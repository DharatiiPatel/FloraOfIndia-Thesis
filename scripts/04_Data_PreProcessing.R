#!/usr/bin/env Rscript

# ---------------------------
# Step 04: Data preprocessing
# Flora of India flower color dataset
# ---------------------------

options(stringsAsFactors = FALSE)
# Render PNGs without an X11 display (needed on headless clusters)
options(bitmapType = "cairo")

# Paths
base_dir <- "/scratch/dp23301/Thesis"
in_file  <- file.path(base_dir, "Processed Data", "flora_of_india_flower_color_categories.csv")

out_dir  <- file.path(base_dir, "Processed Data", "step04_outputs")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

out_clean_all    <- file.path(out_dir, "flora_india_color_clean_all.csv")
out_clean_species <- file.path(out_dir, "flora_india_color_clean_species_only.csv")
out_summary_cat  <- file.path(out_dir, "summary_color_category.csv")
out_summary_raw  <- file.path(out_dir, "summary_color_free_text_top50.csv")

fig_cat_bar      <- file.path(out_dir, "fig_color_category_counts.png")
fig_known_bar    <- file.path(out_dir, "fig_known_color_category_counts.png")

# Packages (use base R only to avoid install issues on cluster)
# If you prefer ggplot2 later, we can add it.

message("Reading input: ", in_file)
df <- read.csv(in_file, encoding = "UTF-8")

# Expected columns:
# species_id, volume, flower_color_free_text, color_category
needed <- c("species_id", "volume", "flower_color_free_text", "color_category")
missing <- setdiff(needed, names(df))
if (length(missing) > 0) {
  stop("Missing required columns: ", paste(missing, collapse = ", "))
}

# ---------------------------
# 1) Basic cleaning
# ---------------------------
df$species_id <- trimws(df$species_id)
df$flower_color_free_text <- trimws(df$flower_color_free_text)
df$color_category <- trimws(df$color_category)

# Normalize category labels (safety)
df$color_category <- toupper(df$color_category)
df$color_category[df$color_category == ""] <- "UNKNOWN"
df$color_category[is.na(df$color_category)] <- "UNKNOWN"

# ---------------------------
# 2) Extract genus + species epithet (to filter to species-level)
#    Many entries are genus-level keys like "Mangifera L."
#    Species-level typically has at least: Genus species
# ---------------------------

# Remove leading numbering like "15. "
species_name <- gsub("^[0-9]+\\.?\\s*", "", df$species_id)

# Keep first two tokens as "Genus species" when possible
tokens <- strsplit(species_name, "\\s+")
genus <- sapply(tokens, function(x) if (length(x) >= 1) x[1] else NA)
epithet <- sapply(tokens, function(x) if (length(x) >= 2) x[2] else NA)

# Species-level rule: epithet exists AND is lowercase-ish (often true for species epithet)
is_species_level <- !is.na(epithet) & grepl("^[a-z]", epithet)

df$genus <- genus
df$epithet <- epithet
df$is_species_level <- is_species_level

# ---------------------------
# 3) Save cleaned full dataset
# ---------------------------
write.csv(df, out_clean_all, row.names = FALSE)
message("Saved cleaned dataset (all records): ", out_clean_all)

# ---------------------------
# 4) Create a species-only dataset (recommended for analysis)
# ---------------------------
df_species <- df[df$is_species_level, ]

# Optional: remove UNKNOWN for some analyses (keep a copy with UNKNOWN too)
write.csv(df_species, out_clean_species, row.names = FALSE)
message("Saved cleaned dataset (species-only): ", out_clean_species)

# ---------------------------
# 5) Summaries
# ---------------------------

# Category counts (all)
cat_counts <- sort(table(df$color_category), decreasing = TRUE)
summary_cat <- data.frame(
  color_category = names(cat_counts),
  n = as.integer(cat_counts)
)
write.csv(summary_cat, out_summary_cat, row.names = FALSE)
message("Saved summary: ", out_summary_cat)

# Top 50 raw free-text outputs
raw_counts <- sort(table(df$flower_color_free_text), decreasing = TRUE)
top_n <- min(50, length(raw_counts))
summary_raw <- data.frame(
  flower_color_free_text = names(raw_counts)[1:top_n],
  n = as.integer(raw_counts[1:top_n])
)
write.csv(summary_raw, out_summary_raw, row.names = FALSE)
message("Saved summary: ", out_summary_raw)

# ---------------------------
# 6) Plots (base R)
# ---------------------------

png(fig_cat_bar, width = 1200, height = 700)
par(mar = c(10, 5, 3, 1))
barplot(cat_counts,
        las = 2,
        main = "Flower color category counts (all records)",
        ylab = "Count")
dev.off()
message("Saved figure: ", fig_cat_bar)

known_df <- df[df$color_category != "UNKNOWN", ]
known_counts <- sort(table(known_df$color_category), decreasing = TRUE)

png(fig_known_bar, width = 1200, height = 700)
par(mar = c(10, 5, 3, 1))
barplot(known_counts,
        las = 2,
        main = "Flower color category counts (known only)",
        ylab = "Count")
dev.off()
message("Saved figure: ", fig_known_bar)

# ---------------------------
# 7) Print key numbers for your notes / report
# ---------------------------
total_records <- nrow(df)
unique_species_id <- length(unique(df$species_id))
total_species_only <- nrow(df_species)
unique_species_only <- length(unique(df_species$species_id))

message("\n--- Key counts ---")
message("Total records (all): ", total_records)
message("Unique species_id (all): ", unique_species_id)
message("Species-level records: ", total_species_only)
message("Unique species_id (species-level): ", unique_species_only)
message("Unknown category (all): ", sum(df$color_category == 'UNKNOWN'))
message("Known category (all): ", sum(df$color_category != 'UNKNOWN'))
message("------------------\n")

message("Step 04 complete.")
