#!/usr/bin/env Rscript
# GBIF occurrence fetch. Writes to Processed Data/experiments/.
# Uses a separate cache so the original download is untouched.

.libPaths(c("~/R/library", .libPaths()))
options(stringsAsFactors = FALSE)

required_packages <- c("rgbif", "dplyr")
for (pkg in required_packages) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    install.packages(pkg, repos = "https://cloud.r-project.org")
  }
  library(pkg, character.only = TRUE)
}

base_dir    <- "/scratch/dp23301/Thesis"
input_file  <- file.path(base_dir, "Processed Data/experiments/clean_species_only.csv")
cache_dir   <- file.path(base_dir, "Processed Data/experiments/gbif_cache_clean")
output_dir  <- file.path(base_dir, "Processed Data/experiments/gbif_outputs_clean")

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

known_colors <- c("WHITE", "YELLOW", "RED", "PINK", "PURPLE/BLUE")
df_known <- df[df$color_category %in% known_colors, ]

df_known$color_group <- df_known$color_category
df_known$color_group[df_known$color_category %in% c("RED", "PINK", "PURPLE/BLUE")] <- "REDTYPE"

df_known$binomial <- paste(df_known$genus, df_known$epithet)
df_known$binomial <- trimws(df_known$binomial)

df_unique <- df_known[!duplicated(df_known$binomial), ]

message("Species with known colour: ", nrow(df_unique))
message("Colour group breakdown:")
print(table(df_unique$color_group))
message("Starting GBIF fetch...\n")

fetch_occurrences <- function(species_name) {
  tryCatch({
    name_result <- name_backbone(name = species_name, rank = "species", verbose = FALSE)
    if (is.null(name_result) || is.na(name_result$usageKey)) {
      return(list(status = "no_match", data = NULL))
    }
    taxon_key <- name_result$usageKey
    occ <- occ_search(
      taxonKey    = taxon_key,
      hasCoordinate = TRUE,
      limit       = MAX_RECORDS,
      fields      = c("species", "decimalLatitude", "decimalLongitude",
                      "year", "countryCode", "gbifID", "hasGeospatialIssues")
    )
    if (is.null(occ$data) || nrow(occ$data) == 0) {
      return(list(status = "no_records", data = NULL))
    }
    occ_clean <- occ$data[!is.na(occ$data$decimalLatitude) &
                          !is.na(occ$data$decimalLongitude), ]
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

failed_species <- c()
success_count  <- 0
skip_count     <- 0

for (i in seq_len(nrow(df_unique))) {
  row         <- df_unique[i, ]
  binomial    <- row$binomial
  safe_name   <- gsub("[^A-Za-z0-9_]", "_", binomial)
  cache_file  <- file.path(cache_dir, paste0(safe_name, ".csv"))

  if (file.exists(cache_file)) {
    skip_count <- skip_count + 1
    if (skip_count %% 50 == 0) {
      message("  [cached] skipped ", skip_count, " species so far...")
    }
    next
  }

  if (i %% 20 == 0) {
    message(sprintf("[%d/%d] Fetching: %s", i, nrow(df_unique), binomial))
  }

  result <- fetch_occurrences(binomial)
  Sys.sleep(SLEEP_BETWEEN)

  if (result$status == "success" && !is.null(result$data)) {
    occ_df <- result$data
    occ_df$query_name    <- binomial
    occ_df$color_group   <- row$color_group
    occ_df$color_category <- row$color_category
    occ_df$volume        <- row$volume
    write.csv(occ_df, cache_file, row.names = FALSE)
    success_count <- success_count + 1
  } else {
    failed_species <- c(failed_species,
                        paste0(binomial, " [", result$status, "]"))
    if (!RETRY_FAILED) {
      write.csv(data.frame(), cache_file, row.names = FALSE)
    }
  }
}

message("\n Fetch complete \n")
message("Successfully fetched: ", success_count)
message("Skipped (cached):    ", skip_count)
message("Failed:              ", length(failed_species))

if (length(failed_species) > 0) {
  writeLines(failed_species, failed_log)
  message("Failed species logged to: ", failed_log)
}

message("\nCombining cached files into final output...")
cache_files <- list.files(cache_dir, pattern = "\\.csv$", full.names = TRUE)

all_occ <- lapply(cache_files, function(f) {
  tryCatch({
    d <- read.csv(f)
    if (nrow(d) > 0) {
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
  combined$lat_round <- round(combined$decimalLatitude,  2)
  combined$lon_round <- round(combined$decimalLongitude, 2)
  combined <- combined[!duplicated(
    paste(combined$query_name, combined$lat_round, combined$lon_round)
  ), ]

  species_counts <- table(combined$query_name)
  species_sufficient <- names(species_counts[species_counts >= MIN_RECORDS])
  combined_filtered <- combined[combined$query_name %in% species_sufficient, ]
  write.csv(combined_filtered, final_output, row.names = FALSE)

  message("\n── Final output ")
  message("Total occurrence records:          ", nrow(combined))
  message("Species with >= ", MIN_RECORDS, " records:         ",
          length(species_sufficient))
  message("Final records saved to:            ", final_output)
} else {
  message("No cached files found — check cache directory: ", cache_dir)
}

message("\nStep 05a (clean) complete.")
