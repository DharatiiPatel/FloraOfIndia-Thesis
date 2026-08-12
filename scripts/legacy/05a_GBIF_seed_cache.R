#!/usr/bin/env Rscript
 
.libPaths(c("~/R/library", .libPaths())) 
options(stringsAsFactors = FALSE)
 
required_packages <- c("rgbif", "dplyr") #dplyr for data manipulation
for (pkg in required_packages) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    install.packages(pkg, repos = "https://cloud.r-project.org")
  }
  library(pkg, character.only = TRUE)
}
 
base_dir    <- "/scratch/dp23301/Thesis"
input_file  <- file.path(base_dir, "Processed Data/step04_outputs/flora_india_color_clean_species_only.csv")
cache_dir   <- file.path(base_dir, "Processed Data/step05_gbif_cache")
output_dir  <- file.path(base_dir, "Processed Data/step05_outputs")
 
dir.create(cache_dir,  recursive = TRUE, showWarnings = FALSE)
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
 
final_output <- file.path(output_dir, "gbif_occurrences_all.csv")
failed_log   <- file.path(output_dir, "gbif_failed_species.txt")
 
MAX_RECORDS      <- 10000  
MIN_RECORDS      <- 6       
RETRY_FAILED     <- TRUE  
SLEEP_BETWEEN    <- 0.5    
 
message("Reading input: ", input_file)
df <- read.csv(input_file, encoding = "UTF-8")
 
# Keep only species with KNOWN flower colour (drop UNKNOWN, OTHER, GREENISH)
known_colors <- c("WHITE", "YELLOW", "RED", "PINK", "PURPLE/BLUE")
df_known <- df[df$color_category %in% known_colors, ] #checks if the color_category column is in the known_colors vector and returns a new dataframe with only the rows where the condition is true.
 
# Create RedType grouping 
df_known$color_group <- df_known$color_category
df_known$color_group[df_known$color_category %in% c("RED", "PINK", "PURPLE/BLUE")] <- "REDTYPE"
 
# Build clean binomial name for GBIF lookup
df_known$binomial <- paste(df_known$genus, df_known$epithet)
df_known$binomial <- trimws(df_known$binomial)
 
# Remove duplicates
df_unique <- df_known[!duplicated(df_known$binomial), ]
 
message("Species with known colour: ", nrow(df_unique))
message("Colour group breakdown:")
print(table(df_unique$color_group))
message("Starting GBIF fetch...\n")
 
fetch_occurrences <- function(species_name) {
  tryCatch({
    #Get the GBIF taxon key a function from rgbif. It returns GBIFs internal numeric id for the species called the usage key
    name_result <- name_backbone(name = species_name, rank = "species", verbose = FALSE)
 
    if (is.null(name_result) || is.na(name_result$usageKey)) { #checks if the name_result is null or NA and returns a list with the status "no_match" and data NULL if true.
      return(list(status = "no_match", data = NULL)) #returns a list with the status "no_match" and data NULL if true.
    }
 
    taxon_key <- name_result$usageKey
 
    #Fetch occurrence records
    occ <- occ_search( #a function from rgbif that searches for occurrences of a species.
      taxonKey    = taxon_key,
      hasCoordinate = TRUE, #only returns if the species has coordinates
      limit       = MAX_RECORDS, #limits the number of records returned to 10000
      fields      = c("species", "decimalLatitude", "decimalLongitude",
                      "year", "countryCode", "gbifID",
                      "hasGeospatialIssues") #specifies the fields to return
    )
 
    if (is.null(occ$data) || nrow(occ$data) == 0) { #checks if the occ$data is null or has no rows and returns a list with the status "no_records" and data NULL if true.
      return(list(status = "no_records", data = NULL)) #returns a list with the status "no_records" and data NULL if true.
    }
 
    #Filter out records with geospatial issues
    occ_clean <- occ$data[!is.na(occ$data$decimalLatitude) &
                          !is.na(occ$data$decimalLongitude), ]
 
    # Remove flagged geospatial issues if column exists
    if ("hasGeospatialIssues" %in% names(occ_clean)) { #checks if the hasGeospatialIssues column exists in the occ_clean dataframe and returns a new dataframe with only the rows where the condition is true.
      occ_clean <- occ_clean[is.na(occ_clean$hasGeospatialIssues) | #checks if the hasGeospatialIssues column is NA or FALSE and returns a new dataframe with only the rows where the condition is true.
                             occ_clean$hasGeospatialIssues == FALSE, ] #checks if the hasGeospatialIssues column is FALSE and returns a new dataframe with only the rows where the condition is true.
    }
 
    if (nrow(occ_clean) == 0) {
      return(list(status = "no_clean_records", data = NULL))
    }
 
    return(list(status = "success", data = occ_clean))
 
  }, error = function(e) {
    return(list(status = paste("error:", conditionMessage(e)), data = NULL))
  })
}
 
failed_species <- c()
success_count  <- 0
skip_count     <- 0
 
for (i in seq_len(nrow(df_unique))) { #loops through the rows of the df_unique dataframe.
 
  row         <- df_unique[i, ] #the row of the df_unique dataframe.
  binomial    <- row$binomial #the binomial column of the row.
  safe_name   <- gsub("[^A-Za-z0-9_]", "_", binomial) #replaces any characters that are not letters, numbers or underscores with an underscore.
  cache_file  <- file.path(cache_dir, paste0(safe_name, ".csv"))
 
  # Skip if already cached
  if (file.exists(cache_file)) {
    skip_count <- skip_count + 1
    if (skip_count %% 50 == 0) {
      message("  [cached] skipped ", skip_count, " species so far...")
    }
    next
  }
 
  #Progress reporting
  if (i %% 20 == 0) {
    message(sprintf("[%d/%d] Fetching: %s", i, nrow(df_unique), binomial))
  }
 
  #fetch
  result <- fetch_occurrences(binomial)
  Sys.sleep(SLEEP_BETWEEN)
 
  if (result$status == "success" && !is.null(result$data)) { 
    # Add metadata columns
    occ_df <- result$data #the data column of the result list.
    occ_df$query_name    <- binomial #the binomial column of the row.
    occ_df$color_group   <- row$color_group #the color_group column of the row.
    occ_df$color_category <- row$color_category #the color_category column of the row.
    occ_df$volume        <- row$volume #the volume column of the row.
 
    # Save to cache
    write.csv(occ_df, cache_file, row.names = FALSE) 
    success_count <- success_count + 1
 
  } else {
    # Log failure
    failed_species <- c(failed_species, 
                        paste0(binomial, " [", result$status, "]")) 
    # Write empty marker so we don't retry endlessly
    if (!RETRY_FAILED) {
      write.csv(data.frame(), cache_file, row.names = FALSE)
    }
  }
}
 
message("\n Fetch complete \n")
message("Successfully fetched: ", success_count)
message("Skipped (cached):    ", skip_count)
message("Failed:              ", length(failed_species))
 
#save failed species log
if (length(failed_species) > 0) {
  writeLines(failed_species, failed_log)
  message("Failed species logged to: ", failed_log)
}
 
#Combine all cached CSVs into one file
message("\nCombining cached files into final output...")
 
cache_files <- list.files(cache_dir, pattern = "\\.csv$", full.names = TRUE) #lists all the files in the cache_dir directory that end with .csv.
 
all_occ <- lapply(cache_files, function(f) { #loops through the cache_files vector and applies the function to each element.
  tryCatch({
    d <- read.csv(f)
    if (nrow(d) > 0) {
      # Keep only essential columns to avoid mismatch
      cols_needed <- c("query_name", "color_group", "color_category", 
                       "volume", "decimalLatitude", "decimalLongitude")
      cols_present <- intersect(cols_needed, names(d)) #returns the columns that are in the cols_needed vector and in the names(d) vector.
      d[, cols_present, drop = FALSE] 
    } else NULL
  }, error = function(e) NULL)
})
 
all_occ <- Filter(Negate(is.null), all_occ) #removes all null values from the list 
 
if (length(all_occ) > 0) {
  combined <- do.call(dplyr::bind_rows, all_occ) #binds the rows of the all_occ list into a single dataframe.
 
  # Remove duplicate grid cells per species (same lat/lon)
  combined$lat_round <- round(combined$decimalLatitude,  2)
  combined$lon_round <- round(combined$decimalLongitude, 2) 
  combined <- combined[!duplicated( #removes duplicate rows from the dataframe based on the query_name, lat_round and lon_round columns.
    paste(combined$query_name, combined$lat_round, combined$lon_round) 
  ), ]
 
  #count records per species
  species_counts <- table(combined$query_name) #returns a table of the counts of the query_name column.
  species_sufficient <- names(species_counts[species_counts >= MIN_RECORDS]) #returns the names of the species_counts vector where the species_counts are greater than or equal to MIN_RECORDS.
 
  combined_filtered <- combined[combined$query_name %in% species_sufficient, ]
 
  write.csv(combined_filtered, final_output, row.names = FALSE)
 
  message("\n── Final output ")
  message("Total occurrence records:          ", nrow(combined))
  message("After deduplication:               ", nrow(combined))
  message("Species with >= ", MIN_RECORDS, " records:         ",
          length(species_sufficient))
  message("Final records saved to:            ", final_output)
 
} else {
  message("No cached files found — check cache directory: ", cache_dir)
}
 
message("\nStep 05a complete.")
