#!/usr/bin/env Rscript

.libPaths(c("~/R/library", .libPaths()))
options(stringsAsFactors = FALSE)
options(bitmapType = "cairo")

library(terra) #for raster (gridded spatial data) data manipulation
library(geodata) #for downloading environmental data
library(dplyr) #for data manipulation

base_dir    <- "/scratch/dp23301/Thesis"
input_file  <- file.path(base_dir, "Processed Data/step05_outputs/gbif_occurrences_all.csv")
env_dir     <- file.path(base_dir, "Processed Data/step05_env_data")
output_dir  <- file.path(base_dir, "Processed Data/step05_outputs")

dir.create(env_dir,    recursive = TRUE, showWarnings = FALSE)
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

out_env_species  <- file.path(output_dir, "species_environment_trimmed.csv")
out_pca_scores   <- file.path(output_dir, "species_pca_scores.csv")
out_pca_loadings <- file.path(output_dir, "pca_loadings.csv")
out_final        <- file.path(output_dir, "species_color_environment_final.csv")

message("Downloading WorldClim bioclimatic variables (Bio1-Bio19)...")

worldclim_bio <- worldclim_global(
  var  = "bio",
  res  = 10, #10 arcminutes resolution
  path = env_dir
)

message("Downloading WorldClim elevation...")
worldclim_elev <- elevation_global(
  res  = 10,
  path = env_dir
)

message("WorldClim download complete.")


message("Downloading SoilGrids variables...")

soil_vars <- c("bdod", "cec", "nitrogen", "phh2o", "soc", "ocd", "ocs",
               "clay", "silt", "sand", "cfvo")

soil_rasters <- list() #list to store the soil rasters
for (var in soil_vars) {
  message("  Downloading SoilGrids: ", var)
  tryCatch({
    soil_rasters[[var]] <- soil_world(
      var   = var,
      depth = 5,   # 0-5cm depth (closest to surface)
      path  = env_dir
    )
  }, error = function(e) {
    message("  WARNING: Could not download ", var, " - ", conditionMessage(e))
  })
}

message("SoilGrids download complete.")


message("Loading GBIF occurrences: ", input_file)
occ <- read.csv(input_file, encoding = "UTF-8")

message("Total occurrence records: ", nrow(occ)) 
message("Species: ", length(unique(occ$query_name))) 


required_cols <- c("query_name", "decimalLatitude", "decimalLongitude",
                   "color_group", "color_category") 
missing_cols <- setdiff(required_cols, names(occ)) #returns the columns that are in the required_cols vector but not in the names(occ) vector.
if (length(missing_cols) > 0) { #checks if the length of the missing_cols vector is greater than 0 and stops the script if true.
  stop("Missing columns in occurrence file: ", paste(missing_cols, collapse = ", "))
} 

#Remove rows with missing coordinates
occ <- occ[!is.na(occ$decimalLatitude) & !is.na(occ$decimalLongitude), ]
message("Records after removing NA coordinates: ", nrow(occ))

#Extract environmental values 
message("Extracting environmental values at occurrence points...")

# Create SpatVector from coordinates
coords <- vect(occ[, c("decimalLongitude", "decimalLatitude")], #the coordinates column is the decimalLongitude and decimalLatitude columns.
               geom = c("decimalLongitude", "decimalLatitude"), #the geometry column is the decimalLongitude and decimalLatitude columns.
               crs  = "EPSG:4326") #EPSG:4326 is the EPSG code for the World Geodetic System 1984 (WGS84) coordinate reference system.

# Extract WorldClim bio variables
message("  Extracting WorldClim Bio1-Bio19...")
bio_vals <- extract(worldclim_bio, coords)
#terra's extract() function is the core spatial operation. For each of the 1.3M+ GPS points in coords, it looks up what value each of the 19 raster layers has at that location.
#returns a data frame with one row per point and one column per raster layer (plus an ID column). This one function replaces what used to require complex GIS operations.
bio_vals <- bio_vals[, -1]  # remove ID column
names(bio_vals) <- paste0("bio", 1:19)

# Extract elevation
message("  Extracting elevation...")
elev_vals <- extract(worldclim_elev, coords)
elev_vals <- elev_vals[, -1, drop = FALSE]
names(elev_vals) <- "alt"

# Extract soil variables
message("  Extracting SoilGrids variables...")
soil_vals_list <- list() 
for (var in names(soil_rasters)) { #loops through the names of the soil_rasters list.
  tryCatch({
    sv <- extract(soil_rasters[[var]], coords) #extracts the environmental values for the soil_rasters[[var]] raster at the coordinates.
    sv <- sv[, -1, drop = FALSE] #removes the ID column from the sv dataframe.
    names(sv) <- var
    soil_vals_list[[var]] <- sv #stores the sv dataframe in the soil_vals_list list.
  }, error = function(e) {
    message("  WARNING: Could not extract ", var)
  })
}

# Combine all environmental values
env_vals <- cbind(bio_vals, elev_vals)
if (length(soil_vals_list) > 0) {
  soil_df <- do.call(cbind, soil_vals_list)
  env_vals <- cbind(env_vals, soil_df)
}

#Add back species metadata
occ_env <- cbind(
  occ[, c("query_name", "color_group", "color_category",
          "decimalLatitude", "decimalLongitude")],
  env_vals
)

message("Environmental extraction complete.")
message("Variables extracted: ", ncol(env_vals))

#Remove duplicate grid cells per species
message("Removing duplicate grid cells...")

occ_env$lat_round <- round(occ_env$decimalLatitude,  1)  # ~10km grid
occ_env$lon_round <- round(occ_env$decimalLongitude, 1)

occ_env <- occ_env[!duplicated(
  paste(occ_env$query_name, occ_env$lat_round, occ_env$lon_round)
), ]

message("Records after deduplication: ", nrow(occ_env))

# Keep only species with >= 6 records
species_counts <- table(occ_env$query_name)
species_keep   <- names(species_counts[species_counts >= 6])
occ_env        <- occ_env[occ_env$query_name %in% species_keep, ]

message("Species with >= 6 records: ", length(species_keep))

message("Calculating 20% trimmed means per species...")

env_cols <- c(paste0("bio", 1:19), "alt", soil_vars)
env_cols <- intersect(env_cols, names(occ_env))

# Trimmed mean function
trim_mean <- function(x) mean(x, trim = 0.2, na.rm = TRUE) 

species_env <- occ_env %>% #the weird symbol is the pipe operator. it reads as abd then. take occ_env and then group by query_name, color_group, color_category and then summarise by n_records and across all of the env_cols and then drop the groups.
  group_by(query_name, color_group, color_category) %>%
  summarise(
    n_records = n(), #n() is a function that counts the number of rows in the group.
    across(all_of(env_cols), trim_mean),
    .groups = "drop" #remove grouping after summarizing
  )

message("Species in final environment dataset: ", nrow(species_env))

#Save species x environment table
write.csv(species_env, out_env_species, row.names = FALSE)
message("Saved: ", out_env_species)

#Step 7: PCA on environmental variables
message("Running PCA on environmental variables...")

# Get environmental matrix (remove rows with any NA)
env_matrix <- species_env[, env_cols] #extracts only the env cols
complete_rows <- complete.cases(env_matrix) #checks if there are any NA values in the env_matrix.
message("Species with complete environmental data: ", sum(complete_rows))

species_complete <- species_env[complete_rows, ]
env_matrix_clean <- env_matrix[complete_rows, ]

# Scale and run PCA
pca_result <- prcomp(env_matrix_clean, center = TRUE, scale. = TRUE) 

# Save PC1-PC10 scores
pc_scores <- as.data.frame(pca_result$x[, 1:10]) #$x contains pc scores. keeping first 10pcs
names(pc_scores) <- paste0("PC", 1:10)

species_pca <- cbind(
  species_complete[, c("query_name", "color_group", "color_category", "n_records")],
  pc_scores
)

write.csv(species_pca, out_pca_scores, row.names = FALSE)
message("Saved PCA scores: ", out_pca_scores)

# Save loadings (how much each original variable contributes to each PC.
loadings_df <- as.data.frame(pca_result$rotation[, 1:10])
loadings_df$variable <- rownames(loadings_df)
write.csv(loadings_df, out_pca_loadings, row.names = FALSE)
message("Saved PCA loadings: ", out_pca_loadings)

# Print variance explained
var_explained <- summary(pca_result)$importance[2, 1:10] * 100 #$importance[2, 1:10] contains the variance explained by each PC.
message("\nVariance explained by PC1-PC10:")
for (i in 1:10) {
  message(sprintf("  PC%d: %.1f%%", i, var_explained[i])) #print something like "PC1: 45.7%"
}

#create binary color columns for MCMCglmm
message("\nCreating binary colour columns...")

species_pca$is_white   <- as.integer(species_pca$color_group == "WHITE") #bracket thing creates a true false vector and as.integer converts to 0/1.
species_pca$is_yellow  <- as.integer(species_pca$color_group == "YELLOW")
species_pca$is_redtype <- as.integer(species_pca$color_group == "REDTYPE")

# Save final dataset
write.csv(species_pca, out_final, row.names = FALSE)
message("Saved final dataset: ", out_final)

message("\n── Step 05b Summary ────────────────────────────────────────────")
message("Total species in final dataset:  ", nrow(species_pca))
message("WHITE:   ", sum(species_pca$is_white))
message("YELLOW:  ", sum(species_pca$is_yellow))
message("REDTYPE: ", sum(species_pca$is_redtype))
message("────────────────────────────────────────────────────────────────")
message("Step 05b complete. Ready for MCMCglmm (Step 06).")