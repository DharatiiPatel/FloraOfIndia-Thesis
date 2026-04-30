#!/usr/bin/env Rscript
 
# =============================================================================
# Step 05a: GBIF Occurrence Data Fetching + Caching
# Flora of India - Flower Colour & Environment Analysis
# =============================================================================
# This script:
#   1. Reads the cleaned species-level colour dataset from step 04
#   2. Filters to species with KNOWN flower colour only
#   3. Fetches up to 10,000 GBIF occurrence records per species
#   4. Saves a per-species cache so the script can resume if interrupted
#   5. Produces a final combined occurrence CSV for step 05b
#
# Runtime estimate: 2-6 hours depending on number of species and GBIF load
# Run as a SLURM job overnight (see bottom of script for SLURM template)
# =============================================================================
.libPaths(c("~/R/library", .libPaths())) 
options(stringsAsFactors = FALSE)
 
# ── Packages ──────────────────────────────────────────────────────────────────
required_packages <- c("rgbif", "dplyr")
for (pkg in required_packages) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    install.packages(pkg, repos = "https://cloud.r-project.org")
  }
  library(pkg, character.only = TRUE)
}
 
# ── Paths ─────────────────────────────────────────────────────────────────────
base_dir    <- "/scratch/dp23301/Thesis"
input_file  <- file.path(base_dir, "Processed Data/step04_outputs/flora_india_color_clean_species_only.csv")
cache_dir   <- file.path(base_dir, "Processed Data/step05_gbif_cache")
output_dir  <- file.path(base_dir, "Processed Data/step05_outputs")
 
dir.create(cache_dir,  recursive = TRUE, showWarnings = FALSE)
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
 
final_output <- file.path(output_dir, "gbif_occurrences_all.csv")
failed_log   <- file.path(output_dir, "gbif_failed_species.txt")
 
# ── Settings ──────────────────────────────────────────────────────────────────
MAX_RECORDS      <- 10000   # max occurrences per species (same as original paper)
MIN_RECORDS      <- 6       # minimum records to keep species in analysis
RETRY_FAILED     <- TRUE    # retry previously failed species
SLEEP_BETWEEN    <- 0.5     # seconds to wait between API calls (be nice to GBIF)
 
# ── Load and filter data ──────────────────────────────────────────────────────
message("Reading input: ", input_file)
df <- read.csv(input_file, encoding = "UTF-8")
 
# Keep only species with KNOWN flower colour (drop UNKNOWN, OTHER, GREENISH)
known_colors <- c("WHITE", "YELLOW", "RED", "PINK", "PURPLE/BLUE")
df_known <- df[df$color_category %in% known_colors, ]
 
# Create RedType grouping (matching original paper: RED + PINK + PURPLE/BLUE)
df_known$color_group <- df_known$color_category
df_known$color_group[df_known$color_category %in% c("RED", "PINK", "PURPLE/BLUE")] <- "REDTYPE"
 
# Build clean binomial name for GBIF lookup
df_known$binomial <- paste(df_known$genus, df_known$epithet)
df_known$binomial <- trimws(df_known$binomial)
 
# Remove duplicates (same binomial appearing in multiple volumes)
df_unique <- df_known[!duplicated(df_known$binomial), ]
 
message("Species with known colour: ", nrow(df_unique))
message("Colour group breakdown:")
print(table(df_unique$color_group))
message("Starting GBIF fetch...\n")
 
# ── Helper: fetch occurrences for one species ─────────────────────────────────
fetch_occurrences <- function(species_name) {
  tryCatch({
    # Step 1: Get the GBIF taxon key
    name_result <- name_backbone(name = species_name, rank = "species", verbose = FALSE)
 
    if (is.null(name_result) || is.na(name_result$usageKey)) {
      return(list(status = "no_match", data = NULL))
    }
 
    taxon_key <- name_result$usageKey
 
    # Step 2: Fetch occurrence records
    occ <- occ_search(
      taxonKey    = taxon_key,
      hasCoordinate = TRUE,
      limit       = MAX_RECORDS,
      fields      = c("species", "decimalLatitude", "decimalLongitude",
                      "year", "countryCode", "gbifID",
                      "hasGeospatialIssues")
    )
 
    if (is.null(occ$data) || nrow(occ$data) == 0) {
      return(list(status = "no_records", data = NULL))
    }
 
    # Step 3: Filter out records with geospatial issues
    occ_clean <- occ$data[!is.na(occ$data$decimalLatitude) &
                          !is.na(occ$data$decimalLongitude), ]
 
    # Remove flagged geospatial issues if column exists
    if ("hasGeospatialIssues" %in% names(occ_clean)) {
      occ_clean <- occ_clean[is.na(occ_clean$hasGeospatialIssues) |
                             occ_clean$hasGeospatialIssues == FALSE, ]
    }
 
    if (nrow(occ_clean) == 0) {
      return(list(status = "no_clean_records", data = NULL))
    }
 
    return(list(status = "success", data = occ_clean))
 
  }, error = function(e) {
    return(list(status = paste("error:", conditionMessage(e)), data = NULL))
  })
}
 
# ── Main fetch loop with checkpointing ───────────────────────────────────────
failed_species <- c()
success_count  <- 0
skip_count     <- 0
 
for (i in seq_len(nrow(df_unique))) {
 
  row         <- df_unique[i, ]
  binomial    <- row$binomial
  safe_name   <- gsub("[^A-Za-z0-9_]", "_", binomial)
  cache_file  <- file.path(cache_dir, paste0(safe_name, ".csv"))
 
  # Skip if already cached
  if (file.exists(cache_file)) {
    skip_count <- skip_count + 1
    if (skip_count %% 50 == 0) {
      message("  [cached] skipped ", skip_count, " species so far...")
    }
    next
  }
 
  # Progress reporting
  if (i %% 20 == 0) {
    message(sprintf("[%d/%d] Fetching: %s", i, nrow(df_unique), binomial))
  }
 
  # Fetch
  result <- fetch_occurrences(binomial)
  Sys.sleep(SLEEP_BETWEEN)
 
  if (result$status == "success" && !is.null(result$data)) {
    # Add metadata columns
    occ_df <- result$data
    occ_df$query_name    <- binomial
    occ_df$color_group   <- row$color_group
    occ_df$color_category <- row$color_category
    occ_df$volume        <- row$volume
 
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
 
message("\n── Fetch complete ──────────────────────────────────────────────")
message("Successfully fetched: ", success_count)
message("Skipped (cached):    ", skip_count)
message("Failed:              ", length(failed_species))
 
# Save failed species log
if (length(failed_species) > 0) {
  writeLines(failed_species, failed_log)
  message("Failed species logged to: ", failed_log)
}
 
# ── Combine all cached CSVs into one file ─────────────────────────────────────
message("\nCombining cached files into final output...")
 
cache_files <- list.files(cache_dir, pattern = "\\.csv$", full.names = TRUE)
 
all_occ <- lapply(cache_files, function(f) {
  tryCatch({
    d <- read.csv(f)
    if (nrow(d) > 0) {
      # Keep only essential columns to avoid mismatch
      cols_needed <- c("query_name", "color_group", "color_category", 
                       "volume", "decimalLatitude", "decimalLongitude")
      cols_present <- intersect(cols_needed, names(d))
      d[, cols_present, drop = FALSE]
    } else NULL
  }, error = function(e) NULL)
})
 
all_occ <- Filter(Negate(is.null), all_occ)
 
if (length(all_occ) > 0) {
  combined <- do.call(dplyr::bind_rows, all_occ)
 
  # Remove duplicate grid cells per species (same lat/lon)
  combined$lat_round <- round(combined$decimalLatitude,  2)
  combined$lon_round <- round(combined$decimalLongitude, 2)
  combined <- combined[!duplicated(
    paste(combined$query_name, combined$lat_round, combined$lon_round)
  ), ]
 
  # Count records per species
  species_counts <- table(combined$query_name)
  species_sufficient <- names(species_counts[species_counts >= MIN_RECORDS])
 
  combined_filtered <- combined[combined$query_name %in% species_sufficient, ]
 
  write.csv(combined_filtered, final_output, row.names = FALSE)
 
  message("\n── Final output ────────────────────────────────────────────────")
  message("Total occurrence records:          ", nrow(combined))
  message("After deduplication:               ", nrow(combined))
  message("Species with >= ", MIN_RECORDS, " records:         ",
          length(species_sufficient))
  message("Final records saved to:            ", final_output)
 
} else {
  message("No cached files found — check cache directory: ", cache_dir)
}
 
message("\nStep 05a complete.")
