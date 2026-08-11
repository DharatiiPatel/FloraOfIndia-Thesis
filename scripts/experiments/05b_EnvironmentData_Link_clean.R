#!/usr/bin/env Rscript
# CLEAN-pipeline environment linking + PCA. Faithful copy of 05b_EnvironmentData_Link.R
# redirected to experiments/. Reuses the EXISTING raster cache (step05_env_data) -
# read-only, geodata skips re-download if files are already there. No original
# outputs are touched.

.libPaths(c("~/R/library", .libPaths()))
options(stringsAsFactors = FALSE)
options(bitmapType = "cairo")

library(terra)
library(geodata)
library(dplyr)

base_dir    <- "/scratch/dp23301/Thesis"
input_file  <- file.path(base_dir, "Processed Data/experiments/gbif_outputs_clean/gbif_occurrences_all.csv")
env_dir     <- file.path(base_dir, "Processed Data/step05_env_data")   # REUSE existing raster cache (read-only)
output_dir  <- file.path(base_dir, "Processed Data/experiments/step05b_outputs_clean")

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

out_env_species  <- file.path(output_dir, "species_environment_trimmed.csv")
out_pca_scores   <- file.path(output_dir, "species_pca_scores.csv")
out_pca_loadings <- file.path(output_dir, "pca_loadings.csv")
out_final        <- file.path(output_dir, "species_color_environment_final_clean.csv")

message("Loading WorldClim bioclimatic variables (from cache)...")
worldclim_bio <- worldclim_global(var = "bio", res = 10, path = env_dir)

message("Loading WorldClim elevation (from cache)...")
worldclim_elev <- elevation_global(res = 10, path = env_dir)

message("Loading SoilGrids variables (from cache)...")
soil_vars <- c("bdod", "cec", "nitrogen", "phh2o", "soc", "ocd", "ocs",
               "clay", "silt", "sand", "cfvo")
soil_rasters <- list()
for (var in soil_vars) {
  tryCatch({
    soil_rasters[[var]] <- soil_world(var = var, depth = 5, path = env_dir)
  }, error = function(e) {
    message("  WARNING: Could not load ", var, " - ", conditionMessage(e))
  })
}

message("Raster loading complete.")

message("Loading GBIF occurrences: ", input_file)
occ <- read.csv(input_file, encoding = "UTF-8")

message("Total occurrence records: ", nrow(occ))
message("Species: ", length(unique(occ$query_name)))

required_cols <- c("query_name", "decimalLatitude", "decimalLongitude",
                   "color_group", "color_category")
missing_cols <- setdiff(required_cols, names(occ))
if (length(missing_cols) > 0) {
  stop("Missing columns in occurrence file: ", paste(missing_cols, collapse = ", "))
}

occ <- occ[!is.na(occ$decimalLatitude) & !is.na(occ$decimalLongitude), ]
message("Records after removing NA coordinates: ", nrow(occ))

message("Extracting environmental values at occurrence points...")
coords <- vect(occ[, c("decimalLongitude", "decimalLatitude")],
               geom = c("decimalLongitude", "decimalLatitude"),
               crs  = "EPSG:4326")

message("  Extracting WorldClim Bio1-Bio19...")
bio_vals <- extract(worldclim_bio, coords)
bio_vals <- bio_vals[, -1]
names(bio_vals) <- paste0("bio", 1:19)

message("  Extracting elevation...")
elev_vals <- extract(worldclim_elev, coords)
elev_vals <- elev_vals[, -1, drop = FALSE]
names(elev_vals) <- "alt"

message("  Extracting SoilGrids variables...")
soil_vals_list <- list()
for (var in names(soil_rasters)) {
  tryCatch({
    sv <- extract(soil_rasters[[var]], coords)
    sv <- sv[, -1, drop = FALSE]
    names(sv) <- var
    soil_vals_list[[var]] <- sv
  }, error = function(e) {
    message("  WARNING: Could not extract ", var)
  })
}

env_vals <- cbind(bio_vals, elev_vals)
if (length(soil_vals_list) > 0) {
  soil_df <- do.call(cbind, soil_vals_list)
  env_vals <- cbind(env_vals, soil_df)
}

occ_env <- cbind(
  occ[, c("query_name", "color_group", "color_category",
          "decimalLatitude", "decimalLongitude")],
  env_vals
)

message("Environmental extraction complete.")
message("Variables extracted: ", ncol(env_vals))

message("Removing duplicate grid cells...")
occ_env$lat_round <- round(occ_env$decimalLatitude,  1)
occ_env$lon_round <- round(occ_env$decimalLongitude, 1)
occ_env <- occ_env[!duplicated(
  paste(occ_env$query_name, occ_env$lat_round, occ_env$lon_round)
), ]
message("Records after deduplication: ", nrow(occ_env))

species_counts <- table(occ_env$query_name)
species_keep   <- names(species_counts[species_counts >= 6])
occ_env        <- occ_env[occ_env$query_name %in% species_keep, ]
message("Species with >= 6 records: ", length(species_keep))

message("Calculating 20% trimmed means per species...")
env_cols <- c(paste0("bio", 1:19), "alt", soil_vars)
env_cols <- intersect(env_cols, names(occ_env))

trim_mean <- function(x) mean(x, trim = 0.2, na.rm = TRUE)

species_env <- occ_env %>%
  group_by(query_name, color_group, color_category) %>%
  summarise(
    n_records = n(),
    across(all_of(env_cols), trim_mean),
    .groups = "drop"
  )

message("Species in final environment dataset: ", nrow(species_env))
write.csv(species_env, out_env_species, row.names = FALSE)
message("Saved: ", out_env_species)

message("Running PCA on environmental variables...")
env_matrix <- species_env[, env_cols]
complete_rows <- complete.cases(env_matrix)
message("Species with complete environmental data: ", sum(complete_rows))

species_complete <- species_env[complete_rows, ]
env_matrix_clean <- env_matrix[complete_rows, ]

pca_result <- prcomp(env_matrix_clean, center = TRUE, scale. = TRUE)

pc_scores <- as.data.frame(pca_result$x[, 1:10])
names(pc_scores) <- paste0("PC", 1:10)

species_pca <- cbind(
  species_complete[, c("query_name", "color_group", "color_category", "n_records")],
  pc_scores
)

write.csv(species_pca, out_pca_scores, row.names = FALSE)
message("Saved PCA scores: ", out_pca_scores)

loadings_df <- as.data.frame(pca_result$rotation[, 1:10])
loadings_df$variable <- rownames(loadings_df)
write.csv(loadings_df, out_pca_loadings, row.names = FALSE)
message("Saved PCA loadings: ", out_pca_loadings)

var_explained <- summary(pca_result)$importance[2, 1:10] * 100
message("\nVariance explained by PC1-PC10:")
for (i in 1:10) {
  message(sprintf("  PC%d: %.1f%%", i, var_explained[i]))
}

message("\nCreating binary colour columns...")
species_pca$is_white   <- as.integer(species_pca$color_group == "WHITE")
species_pca$is_yellow  <- as.integer(species_pca$color_group == "YELLOW")
species_pca$is_redtype <- as.integer(species_pca$color_group == "REDTYPE")

write.csv(species_pca, out_final, row.names = FALSE)
message("Saved final dataset: ", out_final)

message("\n── Step 05b (CLEAN) Summary ────────────────────────────────────")
message("Total species in final dataset:  ", nrow(species_pca))
message("WHITE:   ", sum(species_pca$is_white))
message("YELLOW:  ", sum(species_pca$is_yellow))
message("REDTYPE: ", sum(species_pca$is_redtype))
message("────────────────────────────────────────────────────────────────")
message("Step 05b (clean) complete.")
