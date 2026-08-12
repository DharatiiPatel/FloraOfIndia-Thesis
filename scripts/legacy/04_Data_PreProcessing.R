#!/usr/bin/env Rscript

options(stringsAsFactors = FALSE) #prevents R from converting strings to factors automatically.
options(bitmapType = "cairo") #prevents R from using X11 for graphics.

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

message("Reading input: ", in_file)
df <- read.csv(in_file, encoding = "UTF-8")

# Expected columns:
# species_id, volume, flower_color_free_text, color_category
needed <- c("species_id", "volume", "flower_color_free_text", "color_category") #c creates a vector of column names that are needed in the dataframe.
missing <- setdiff(needed, names(df)) #returns elements that are in needed but not in names(df)
if (length(missing) > 0) { #checks if missing vector has any elements
  stop("Missing required columns: ", paste(missing, collapse = ", "))
}
#Basic cleaning
df$species_id <- trimws(df$species_id) 
df$flower_color_free_text <- trimws(df$flower_color_free_text)
df$color_category <- trimws(df$color_category)

df$color_category <- toupper(df$color_category)
df$color_category[df$color_category == ""] <- "UNKNOWN" #assigns "UNKNOWN" to empty strings.
df$color_category[is.na(df$color_category)] <- "UNKNOWN" #returns true for NA values and assigns "UNKNOWN" to them.

#Extract genus and epithet
species_name <- gsub("^[0-9]+\\.?\\s*", "", df$species_id) #removes leading numbering like "15. "

# Keep first two tokens as "Genus species" when possible
tokens <- strsplit(species_name, "\\s+") #splits the species name into tokens separated by whitespace.
genus <- sapply(tokens, function(x) if (length(x) >= 1) x[1] else NA) #returns the first token as genus. sapply applies the function to each element of the tokens vector.
epithet <- sapply(tokens, function(x) if (length(x) >= 2) x[2] else NA) #returns the second token as epithet.

is_species_level <- !is.na(epithet) & grepl("^[a-z]", epithet)

df$genus <- genus #adds three new columns to the dataframe 
df$epithet <- epithet
df$is_species_level <- is_species_level

write.csv(df, out_clean_all, row.names = FALSE) #R adds an extra first col with row numbers which is not useful
message("Saved cleaned dataset (all records): ", out_clean_all)

df_species <- df[df$is_species_level, ] #filters the dataframe to only include rows where is_species_level is true.

write.csv(df_species, out_clean_species, row.names = FALSE)
message("Saved cleaned dataset (species-only): ", out_clean_species)

cat_counts <- sort(table(df$color_category), decreasing = TRUE)
summary_cat <- data.frame(
  color_category = names(cat_counts),
  n = as.integer(cat_counts)
)
write.csv(summary_cat, out_summary_cat, row.names = FALSE)
message("Saved summary: ", out_summary_cat)

raw_counts <- sort(table(df$flower_color_free_text), decreasing = TRUE) 
top_n <- min(50, length(raw_counts)) #returns the minimum of 50 and the length of the raw_counts vector.
summary_raw <- data.frame( #creates a new dataframe with the top 50 most frequent flower color free text values and their counts.
  flower_color_free_text = names(raw_counts)[1:top_n], #names(raw_counts) returns the names of the raw_counts vector. [1:top_n] returns the first top_n elements.
  n = as.integer(raw_counts[1:top_n]) #as.integer converts the raw_counts vector to integers.
)
write.csv(summary_raw, out_summary_raw, row.names = FALSE)
message("Saved summary: ", out_summary_raw)

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
