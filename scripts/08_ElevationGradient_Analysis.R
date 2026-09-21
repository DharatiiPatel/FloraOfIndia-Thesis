#!/usr/bin/env Rscript
# Elevation-gradient analysis on the primary analysis set (n=1,438).
# Writes under Processed Data/experiments/expansion/step08_outputs/
# (internal path; treat as primary analysis output).
# Does not touch prior n=1,174 paths under step08_outputs_clean/.
#
# Set SKIP_ELEV_MCMC=1 to build descriptive fig6 panels only (no MCMCglmm).

.libPaths(c("/scratch/dp23301/Thesis/R_library", "~/R/library", .libPaths()))
options(stringsAsFactors = FALSE)
options(bitmapType = "cairo")

for (pkg in c("MCMCglmm", "ggplot2", "patchwork", "dplyr", "tidyr", "scales")) {
  if (!requireNamespace(pkg, quietly = TRUE)) stop("Missing package: ", pkg)
  if (pkg == "MCMCglmm") library(MCMCglmm, quietly = TRUE)
}
library(ggplot2)
library(patchwork)
library(dplyr)
library(tidyr)
library(scales)

base_dir <- "/scratch/dp23301/Thesis"
source(file.path(base_dir, "scripts/lib/figure_style.R"))

# ECOLOGY_SET=clean reruns the historical n=1,174 set for the §1b comparison
# table. It must NOT publish into Results/, which holds the primary n=1,438
# figures. Default (unset / "primary") is the published analysis.
eco_set <- Sys.getenv("ECOLOGY_SET", "primary")
publish_results <- !identical(eco_set, "clean")
message("ECOLOGY_SET = ", eco_set, "  (publish to Results: ", publish_results, ")")

if (identical(eco_set, "clean")) {
  clean_root <- file.path(base_dir, "Processed Data/experiments")
  input_pca  <- file.path(clean_root, "step05b_outputs_clean/species_color_environment_final_clean.csv")
  input_env  <- file.path(clean_root, "step05b_outputs_clean/species_environment_trimmed.csv")
  output_dir <- file.path(clean_root, "step08_outputs_clean")
} else {
  exp_root    <- file.path(base_dir, "Processed Data/experiments/expansion")
  input_pca   <- file.path(exp_root, "step05b_outputs/species_color_environment_final_expanded.csv")
  input_env   <- file.path(exp_root, "step05b_outputs/species_environment_trimmed.csv")
  output_dir  <- file.path(exp_root, "step08_outputs")
}
fig_dir     <- file.path(output_dir, "figures")

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(fig_dir,     recursive = TRUE, showWarnings = FALSE)

skip_mcmc <- identical(Sys.getenv("SKIP_ELEV_MCMC", ""), "1")

ELEV_BREAKS <- c(-Inf, 500, 1500, 3000, 4500, Inf)
ELEV_LABELS <- c(
  "Lowland\n(0-500 m)",
  "Submontane\n(500-1500 m)",
  "Montane\n(1500-3000 m)",
  "Subalpine\n(3000-4500 m)",
  "Alpine\n(>4500 m)"
)

assign_elev_band <- function(alt_m) {
  cut(alt_m, breaks = ELEV_BREAKS, labels = ELEV_LABELS, right = TRUE)
}

NITT   <- 1050000
BURNIN <- 50000
THIN   <- 100
PRIOR  <- list(R = list(V = 1, fix = 1), G = list(G1 = list(V = 1, nu = 0.002)))

COL_SIG    <- "#A3262A"
COL_NONSIG <- "#999999"

message("Loading elevation data (", eco_set, " set)...")

df <- read.csv(input_pca, encoding = "UTF-8")
env <- read.csv(input_env, encoding = "UTF-8") %>%
  select(query_name, alt)

df <- df %>%
  left_join(env, by = "query_name") %>%
  filter(!is.na(alt), alt >= 0) %>%
  mutate(
    genus      = sapply(strsplit(query_name, " "), function(x) x[1]),
    elev_band  = assign_elev_band(alt),
    alt_scaled = scale(alt)[, 1]
  )

n_elev <- nrow(df)
n_subtitle <- sprintf("n = %s", format(n_elev, big.mark = ","))
message("Species with elevation: ", n_elev)
message("Elevation range (m): ", round(min(df$alt)), " – ", round(max(df$alt)))

write.csv(df, file.path(output_dir, "species_with_elevation.csv"), row.names = FALSE)

message("\nRQ1: Colour proportions by elevation band...")

band_summary <- df %>%
  group_by(elev_band) %>%
  summarise(
    n_species   = n(),
    n_white     = sum(is_white),
    n_yellow    = sum(is_yellow),
    n_redtype   = sum(is_redtype),
    pct_white   = 100 * mean(is_white),
    pct_yellow  = 100 * mean(is_yellow),
    pct_redtype = 100 * mean(is_redtype),
    median_alt  = median(alt),
    .groups = "drop"
  )

write.csv(band_summary, file.path(output_dir, "elevation_band_summary.csv"), row.names = FALSE)
print(band_summary)

colour_long <- df %>%
  mutate(colour_label = case_when(
    is_white  == 1 ~ "WHITE",
    is_yellow == 1 ~ "YELLOW",
    is_redtype == 1 ~ "REDTYPE",
    TRUE ~ NA_character_
  )) %>%
  filter(!is.na(colour_label))

chi_tab  <- table(colour_long$elev_band, colour_long$colour_label)
chi_test <- chisq.test(chi_tab)
message("\nChi-square test (colour × elevation band):")
message("  X² = ", round(chi_test$statistic, 3), ", df = ", chi_test$parameter,
        ", p = ", format.pval(chi_test$p.value, digits = 3))
writeLines(capture.output(print(chi_test)), file.path(output_dir, "elevation_chisq_test.txt"))

message("\nRQ2: MCMCglmm models — colour ~ elevation...")

colors_to_run <- list(
  list(col = "is_white",   label = "WHITE"),
  list(col = "is_yellow",  label = "YELLOW"),
  list(col = "is_redtype", label = "REDTYPE")
)

mcmc_results <- list()
elev_effects <- NULL
elev_csv     <- file.path(output_dir, "elevation_mcmc_results.csv")

if (skip_mcmc && !file.exists(elev_csv)) {
  message("SKIP_ELEV_MCMC=1 and no cached elevation_mcmc_results.csv — skipping MCMC.")
} else if (file.exists(elev_csv)) {
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

message("\nRQ3: PC2 by elevation band...")

pc2_by_band <- df %>%
  group_by(elev_band) %>%
  summarise(
    n        = n(),
    mean_PC2 = mean(PC2, na.rm = TRUE),
    sd_PC2   = sd(PC2, na.rm = TRUE),
    mean_alt = mean(alt),
    .groups = "drop"
  )

write.csv(pc2_by_band, file.path(output_dir, "pc2_by_elevation_band.csv"), row.names = FALSE)

message("\nGenerating elevation figures...")

save_fig <- function(out_path, plot, w, h) {
  ggsave(out_path, plot, width = w, height = h, dpi = 300, bg = "white")
  message("  Saved: ", basename(out_path))
}

prop_df <- band_summary %>%
  select(elev_band, pct_white, pct_yellow, pct_redtype) %>%
  pivot_longer(-elev_band, names_to = "colour", values_to = "pct") %>%
  mutate(colour = recode(colour,
    pct_white = "WHITE", pct_yellow = "YELLOW", pct_redtype = "REDTYPE"
  ))

p_prop <- plot_elev_proportions(prop_df, band_summary)
save_fig(file.path(fig_dir, "fig6_elevation_colour_proportions.png"), p_prop, 8.6, 4.8)

count_df <- band_summary %>%
  select(elev_band, n_white, n_yellow, n_redtype) %>%
  pivot_longer(-elev_band, names_to = "colour", values_to = "n") %>%
  mutate(colour = recode(colour,
    n_white = "WHITE", n_yellow = "YELLOW", n_redtype = "REDTYPE"
  ))

p_count <- plot_elev_counts(count_df, band_summary)
save_fig(file.path(fig_dir, "fig6_elevation_species_counts.png"), p_count, 9.2, 4.8)

p_density <- ggplot(df, aes(x = alt, fill = color_group)) +
  geom_density(alpha = 0.45, colour = NA) +
  scale_fill_manual(values = PUB_CLASS_COLORS, name = NULL) +
  scale_x_continuous(labels = comma) +
  labs(
    title = "Elevation by flower colour",
    subtitle = n_subtitle,
    x = "Elevation (m)", y = "Density"
  ) +
  theme_pub()

save_fig(file.path(fig_dir, "fig6_elevation_density.png"), p_density, 10, 5)

if (!is.null(elev_effects) && nrow(elev_effects) > 0) {
  # Normalise column names if loaded from CSV with mangled names
  nm <- names(elev_effects)
  if ("post.mean" %in% nm) names(elev_effects)[nm == "post.mean"] <- "mean"
  if ("l.95..CI" %in% names(elev_effects)) names(elev_effects)[names(elev_effects) == "l.95..CI"] <- "lower"
  if ("u.95..CI" %in% names(elev_effects)) names(elev_effects)[names(elev_effects) == "u.95..CI"] <- "upper"
  if ("l-95% CI" %in% names(elev_effects)) names(elev_effects)[names(elev_effects) == "l-95% CI"] <- "lower"
  if ("u-95% CI" %in% names(elev_effects)) names(elev_effects)[names(elev_effects) == "u-95% CI"] <- "upper"

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
      title = "Elevation effect on flower colour",
      subtitle = n_subtitle,
      x = "Coefficient (scaled elevation)", y = NULL
    ) +
    theme_pub_forest()

  save_fig(file.path(fig_dir, "fig6_elevation_mcmc_coefficients.png"), p_mcmc, 8, 4)
} else {
  message("  fig6_elevation_mcmc_coefficients skipped (no elevation MCMC results yet).")
}

p_pc2 <- ggplot(df, aes(x = elev_band, y = PC2, fill = elev_band)) +
  geom_boxplot(outlier.size = 0.8, alpha = 0.85, show.legend = FALSE,
               colour = PUB_INK, linewidth = 0.35) +
  geom_hline(yintercept = 0, linetype = "dashed", colour = "grey50") +
  scale_fill_manual(values = PUB_STAGE_RAMP(nlevels(df$elev_band))) +
  labs(
    title = "Environmental PC2 across elevation bands",
    subtitle = n_subtitle,
    x = NULL, y = "PC2 score"
  ) +
  theme_pub() +
  theme(axis.text.x = element_text(size = 9), legend.position = "none")

save_fig(file.path(fig_dir, "fig6_elevation_pc2_boxplot.png"), p_pc2, 10, 5)

summary_lines <- c(
  paste0("Elevation Gradient Analysis — ", eco_set, " set summary"),
  strrep("=", 50),
  paste("Date:", Sys.time()),
  paste("ECOLOGY_SET:", eco_set),
  paste("Input:", input_pca),
  paste("Species analysed:", nrow(df)),
  paste("Elevation range (m):", round(min(df$alt)), "-", round(max(df$alt))),
  paste("SKIP_ELEV_MCMC:", skip_mcmc),
  "",
  "Chi-square (colour x band):",
  capture.output(print(chi_test)),
  "",
  paste("Outputs under:", output_dir)
)
writeLines(summary_lines, file.path(output_dir, "elevation_analysis_summary.txt"))

# Publish elevation figures into Results — primary set only, so a clean-set
# rerun never overwrites the published n=1,438 figures.
if (publish_results) {
  res_elev <- file.path(base_dir, "Results/figures/ecology")
  dir.create(res_elev, recursive = TRUE, showWarnings = FALSE)
  for (f in list.files(fig_dir, pattern = "\\.png$")) {
    dst <- file.path(res_elev, f)
    if (file.exists(dst) || !is.na(Sys.readlink(dst))) try(unlink(dst), silent = TRUE)
    file.copy(file.path(fig_dir, f), dst, overwrite = TRUE)
  }
  for (t in c("elevation_band_summary.csv", "elevation_mcmc_results.csv",
              "pc2_by_elevation_band.csv", "elevation_analysis_summary.txt")) {
    src <- file.path(output_dir, t)
    if (!file.exists(src)) next
    dst <- file.path(base_dir, "Results/tables/elevation", t)
    dir.create(dirname(dst), recursive = TRUE, showWarnings = FALSE)
    if (file.exists(dst) || !is.na(Sys.readlink(dst))) try(unlink(dst), silent = TRUE)
    file.copy(src, dst, overwrite = TRUE)
  }
} else {
  message("Skipping Results/ publication (ECOLOGY_SET=clean).")
}

message("\nPrimary elevation Step 08 complete")
message("Results: ", output_dir)
message("Figures: ", fig_dir)
