#!/usr/bin/env Rscript

.libPaths(c("/scratch/dp23301/Thesis/R_library", "~/R/library", .libPaths()))
options(stringsAsFactors = FALSE)

for (pkg in c("MCMCglmm", "ggplot2", "patchwork", "dplyr", "tidyr", "scales")) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    stop("Missing package: ", pkg)
  }
  if (pkg == "MCMCglmm") library(MCMCglmm, quietly = TRUE)
}
library(ggplot2)
library(patchwork)
library(dplyr)
library(tidyr)
library(scales)

base_dir    <- "/scratch/dp23301/Thesis"
input_pca   <- file.path(base_dir, "Processed Data/step05_outputs/species_color_environment_final.csv")
input_env   <- file.path(base_dir, "Processed Data/step05_outputs/species_environment_trimmed.csv")
output_dir  <- file.path(base_dir, "Processed Data/step08_outputs")
fig_dir     <- file.path(output_dir, "figures")

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(fig_dir,     recursive = TRUE, showWarnings = FALSE)

#Elevation band definitions (India-relevant, metres)
# Documented in ElevationGradient_NovelResearch.md
ELEV_BREAKS <- c(-Inf, 500, 1500, 3000, 4500, Inf)
ELEV_LABELS <- c(
  "Lowland\n(0–500 m)",
  "Submontane\n(500–1500 m)",
  "Montane\n(1500–3000 m)",
  "Subalpine\n(3000–4500 m)",
  "Alpine\n(>4500 m)"
)

assign_elev_band <- function(alt_m) {
  cut(alt_m, breaks = ELEV_BREAKS, labels = ELEV_LABELS, right = TRUE)
}

NITT   <- 1050000
BURNIN <- 50000
THIN   <- 100
PRIOR  <- list(R = list(V = 1, fix = 1), G = list(G1 = list(V = 1, nu = 0.002)))

COLOR_PANEL <- c(WHITE = "#D9D9D9", YELLOW = "#D9B556", REDTYPE = "#A3262D")
COL_SIG     <- "#A3262A"
COL_NONSIG  <- "#999999"

theme_paper <- theme_minimal(base_size = 12) +
  theme(
    plot.title    = element_text(face = "bold", hjust = 0.5),
    plot.subtitle = element_text(hjust = 0.5, colour = "grey35"),
    strip.text    = element_text(face = "bold"),
    panel.grid.minor = element_blank()
  )

#Build analysis dataset with elevation
message("Loading data...")

df <- read.csv(input_pca, encoding = "UTF-8")
env <- read.csv(input_env, encoding = "UTF-8") %>%
  select(query_name, alt)

df <- df %>%
  left_join(env, by = "query_name") %>%
  filter(!is.na(alt), alt >= 0) %>%
  mutate(
    genus      = sapply(strsplit(query_name, " "), function(x) x[1]),
    elev_band  = assign_elev_band(alt), #assigns the elevation band to the species based on the altitude.
    alt_scaled = scale(alt)[, 1] #scales the altitude to have mean 0 and standard deviation 1.
  )

message("Species with elevation: ", nrow(df))
message("Elevation range (m): ", round(min(df$alt)), " – ", round(max(df$alt)))

write.csv(df, file.path(output_dir, "species_with_elevation.csv"), row.names = FALSE)

# RQ1 — Colour proportions by elevation band

message("\nRQ1: Colour proportions by elevation band...")

band_summary <- df %>%
  group_by(elev_band) %>%
  summarise(
    n_species  = n(),
    n_white    = sum(is_white),
    n_yellow   = sum(is_yellow),
    n_redtype  = sum(is_redtype),
    pct_white  = 100 * mean(is_white), #calculates the percentage of white flowers in the elevation band.
    pct_yellow = 100 * mean(is_yellow), #calculates the percentage of yellow flowers in the elevation band.
    pct_redtype = 100 * mean(is_redtype), #calculates the percentage of red-type flowers in the elevation band.
    median_alt = median(alt), #calculates the median altitude of the species in the elevation band.
    .groups = "drop" #drops the grouping after summarizing.
  )

write.csv(band_summary, file.path(output_dir, "elevation_band_summary.csv"), row.names = FALSE)
print(band_summary)

# Chi-square: colour category vs elevation band
colour_long <- df %>%
  mutate(colour_label = case_when(
    is_white  == 1 ~ "WHITE",
    is_yellow == 1 ~ "YELLOW",
    is_redtype == 1 ~ "REDTYPE",
    TRUE ~ NA_character_
  )) %>%
  filter(!is.na(colour_label))

chi_tab <- table(colour_long$elev_band, colour_long$colour_label)
chi_test <- chisq.test(chi_tab)
message("\nChi-square test (colour × elevation band):")
message("  X² = ", round(chi_test$statistic, 3), ", df = ", chi_test$parameter,
        ", p = ", format.pval(chi_test$p.value, digits = 3))

writeLines(capture.output(print(chi_test)), file.path(output_dir, "elevation_chisq_test.txt"))


# RQ2 — MCMCglmm: elevation predicts each colour (genus random effect)

message("\nRQ2: MCMCglmm models — colour ~ elevation...")

colors_to_run <- list(
  list(col = "is_white",   label = "WHITE"),
  list(col = "is_yellow",  label = "YELLOW"),
  list(col = "is_redtype", label = "REDTYPE")
)

mcmc_results <- list()
elev_effects <- NULL
elev_csv     <- file.path(output_dir, "elevation_mcmc_results.csv")

if (file.exists(elev_csv)) {
  message("Skipping MCMC — loading ", elev_csv)
  elev_effects <- read.csv(elev_csv)
} else {
for (color_info in colors_to_run) {
  message("\n", strrep("─", 50))
  message("MCMCglmm: ", color_info$label, " ~ alt_scaled + genus")
  message(strrep("─", 50))

  set.seed(42)
  model <- tryCatch({
    MCMCglmm(
      fixed   = as.formula(paste(color_info$col, "~ alt_scaled")),
      random  = ~ genus,
      data    = df,
      family  = "threshold",
      prior   = PRIOR,
      nitt    = NITT,
      burnin  = BURNIN,
      thin    = THIN,
      verbose = TRUE
    )
  }, error = function(e) {
    message("ERROR: ", conditionMessage(e))
    NULL
  })

  if (!is.null(model)) {
    summ <- as.data.frame(summary(model)$solutions)
    summ$variable <- rownames(summ)
    summ$color    <- color_info$label
    rownames(summ) <- NULL
    if ("post.mean" %in% names(summ)) {
      names(summ)[names(summ) == "post.mean"] <- "mean"
      names(summ)[names(summ) == "l-95% CI"]  <- "lower"
      names(summ)[names(summ) == "u-95% CI"]  <- "upper"
    }
    mcmc_results[[color_info$label]] <- summ
    saveRDS(model, file.path(output_dir, paste0("model_elev_", color_info$label, ".rds")))
  }
}

if (length(mcmc_results) > 0) {
  elev_effects <- bind_rows(mcmc_results)
  write.csv(elev_effects, elev_csv, row.names = FALSE)
  message("\nSaved: elevation_mcmc_results.csv")
}
}

# RQ3 — PC2 mean by elevation band (context for replication finding)

message("\nRQ3: PC2 by elevation band...")

pc2_by_band <- df %>%
  group_by(elev_band) %>%
  summarise(
    n          = n(),
    mean_PC2   = mean(PC2, na.rm = TRUE),
    sd_PC2     = sd(PC2, na.rm = TRUE),
    mean_alt   = mean(alt),
    .groups = "drop"
  )

write.csv(pc2_by_band, file.path(output_dir, "pc2_by_elevation_band.csv"), row.names = FALSE)

#Figures
message("\nGenerating elevation figures...")

save_fig <- function(out_path, plot, w, h) {
  ggsave(out_path, plot, width = w, height = h, dpi = 150, bg = "white")
  message("  Saved: ", basename(out_path))
}

# Fig A: Stacked proportion of colours by elevation band
prop_df <- band_summary %>%
  select(elev_band, pct_white, pct_yellow, pct_redtype) %>%
  pivot_longer(-elev_band, names_to = "colour", values_to = "pct") %>%
  mutate(colour = recode(colour,
    pct_white = "WHITE", pct_yellow = "YELLOW", pct_redtype = "REDTYPE"
  ))

p_prop <- ggplot(prop_df, aes(x = elev_band, y = pct, fill = colour)) +
  geom_col(position = "stack", width = 0.75, colour = "white") +
  scale_fill_manual(values = COLOR_PANEL, name = "Colour group") +
  labs(
    title = "Flower Colour Composition across Elevation Bands",
    subtitle = "India - Flora of India analysis dataset (n species per band shown)",
    x = NULL, y = "Percentage of species (%)"
  ) +
  geom_text(
    data = band_summary,
    aes(x = elev_band, y = 102, label = paste0("n=", n_species)),
    inherit.aes = FALSE, size = 3.5, fontface = "bold"
  ) +
  theme_paper +
  theme(axis.text.x = element_text(size = 9))

save_fig(file.path(fig_dir, "fig6_elevation_colour_proportions.png"), p_prop, 10, 6)

# Fig B: Species count by band (stacked absolute)
count_df <- band_summary %>%
  select(elev_band, n_white, n_yellow, n_redtype) %>%
  pivot_longer(-elev_band, names_to = "colour", values_to = "n") %>%
  mutate(colour = recode(colour,
    n_white = "WHITE", n_yellow = "YELLOW", n_redtype = "REDTYPE"
  ))

p_count <- ggplot(count_df, aes(x = elev_band, y = n, fill = colour)) +
  geom_col(position = "stack", width = 0.75, colour = "white") +
  scale_fill_manual(values = COLOR_PANEL, name = "Colour group") +
  scale_y_continuous(labels = comma) +
  labs(
    title = "Species Counts by Elevation Band and Flower Colour",
    x = NULL, y = "Number of species"
  ) +
  theme_paper +
  theme(axis.text.x = element_text(size = 9))

save_fig(file.path(fig_dir, "fig6_elevation_species_counts.png"), p_count, 10, 6)

# Fig C: Altitude distribution by colour (density)
p_density <- ggplot(df, aes(x = alt, fill = color_group)) +
  geom_density(alpha = 0.45, colour = NA) +
  scale_fill_manual(values = COLOR_PANEL, name = "Colour group") +
  scale_x_continuous(labels = comma) +
  labs(
    title = "Elevation Distribution of Species by Flower Colour",
    subtitle = "WorldClim altitude (m) at GBIF occurrence locations — species-level trimmed mean",
    x = "Elevation (m)", y = "Density"
  ) +
  theme_paper

save_fig(file.path(fig_dir, "fig6_elevation_density.png"), p_density, 10, 5)

# Fig D: MCMC forest plot for elevation effect (if models ran)
if (!is.null(elev_effects) && nrow(elev_effects) > 0) {
  eff_plot <- elev_effects %>%
    filter(variable != "(Intercept)") %>%
    mutate(
      significant = lower > 0 | upper < 0,
      color = factor(color, levels = c("WHITE", "YELLOW", "REDTYPE"))
    )

  p_mcmc <- ggplot(eff_plot, aes(x = mean, y = color, colour = significant)) +
    geom_vline(xintercept = 0, linetype = "dashed", colour = "grey50") +
    geom_errorbar(aes(xmin = lower, xmax = upper), width = 0.15, linewidth = 0.8) +
    geom_point(size = 3.5, shape = 21, aes(fill = significant)) +
    scale_colour_manual(values = c("TRUE" = COL_SIG, "FALSE" = COL_NONSIG), guide = "none") +
    scale_fill_manual(values = c("TRUE" = COL_SIG, "FALSE" = "white"), guide = "none") +
    labs(
      title = "Elevation Effect on Flower Colour (MCMCglmm)",
      subtitle = "Posterior mean ± 95% CI; alt scaled to unit variance; genus random effect",
      x = "Coefficient (alt_scaled)", y = NULL
    ) +
    theme_paper

  save_fig(file.path(fig_dir, "fig6_elevation_mcmc_coefficients.png"), p_mcmc, 8, 4)
}

# Fig E: PC2 by elevation band (environmental context)
p_pc2 <- ggplot(df, aes(x = elev_band, y = PC2, fill = elev_band)) +
  geom_boxplot(outlier.size = 0.8, alpha = 0.7, show.legend = FALSE) +
  geom_hline(yintercept = 0, linetype = "dashed", colour = "grey50") +
  labs(
    title = "Environmental PC2 across Elevation Bands",
    subtitle = "PC2 = fertile-wet-acidic forest soil axis (see main results)",
    x = NULL, y = "PC2 score"
  ) +
  theme_paper +
  theme(axis.text.x = element_text(size = 9))

save_fig(file.path(fig_dir, "fig6_elevation_pc2_boxplot.png"), p_pc2, 10, 5)


# Text summary for thesis
summary_lines <- c(
  "Elevation Gradient Analysis — Summary",
  strrep("=", 50),
  paste("Date:", Sys.time()),
  paste("Species analysed:", nrow(df)),
  paste("Elevation range (m):", round(min(df$alt)), "-", round(max(df$alt))),
  "",
  "Research questions:",
  "  RQ1: Colour proportions vary across elevation bands?",
  "  RQ2: Elevation predicts colour after genus random effect (MCMCglmm)?",
  "  RQ3: PC2 (main env axis) shifts with elevation?",
  "",
  "Chi-square (colour x band):",
  capture.output(print(chi_test)),
  "",
  "Outputs:",
  "  species_with_elevation.csv",
  "  elevation_band_summary.csv",
  "  elevation_mcmc_results.csv",
  "  pc2_by_elevation_band.csv",
  "  figures/fig6_elevation_*.png"
)

writeLines(summary_lines, file.path(output_dir, "elevation_analysis_summary.txt"))

message("\n Step 08 Complete")
message("Results: ", output_dir)
message("Figures: ", fig_dir)
