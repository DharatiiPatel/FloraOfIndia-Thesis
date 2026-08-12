#!/usr/bin/env Rscript

.libPaths(c("/scratch/dp23301/Thesis/R_library", "~/R/library", .libPaths()))
options(stringsAsFactors = FALSE)

for (pkg in c("ggplot2", "patchwork", "dplyr", "tidyr", "scales")) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    stop("Missing package: ", pkg,
         " — run: module load R/4.5.1-gfbf-2025a && Rscript -e ",
         "\"install.packages('", pkg, "', lib='/scratch/dp23301/Thesis/R_library')\"")
  }
}
library(ggplot2)
library(patchwork)
library(dplyr)
library(tidyr)
library(scales)

base_dir   <- "/scratch/dp23301/Thesis"

# Publication styling for the bar charts (fig1, fig4, fig5) lives here so that
# scripts/rebuild_bar_figures.R and this script cannot drift apart.
source(file.path(base_dir, "scripts/figure_style.R"))

# Clean pipeline outputs (see docs/VERIFIED_Numbers_for_Thesis.md). There is
# only one pipeline now; these paths are not an "updated" alternative to
# anything else in Processed Data/.
exp_dir       <- file.path(base_dir, "Processed Data/experiments")
species_only  <- file.path(exp_dir, "clean_species_only.csv")
treatments_f  <- file.path(exp_dir, "species_descriptions_treatments.csv")
gbif_cache_dir <- file.path(exp_dir, "gbif_cache_clean")
step05_dir    <- file.path(exp_dir, "step05b_outputs_clean")
env_final_f   <- file.path(step05_dir, "species_color_environment_final_clean.csv")
step06_dir   <- file.path(base_dir, "Processed Data/step06_outputs_clean")
step06_tables <- file.path(step06_dir, "tables")
step06_models <- file.path(step06_dir, "models")
fig_dir      <- file.path(base_dir, "Processed Data/figures")
step06_fig   <- file.path(step06_dir, "figures")

s06_combined <- file.path(step06_tables, "combined/all_fixed_effects_combined.csv")
s06_sv       <- file.path(step06_tables, "combined/single_variable_models.csv")
s06_sv_root  <- file.path(step06_dir, "single_variable_models.csv")

dir.create(fig_dir,    recursive = TRUE, showWarnings = FALSE)
dir.create(step06_fig, recursive = TRUE, showWarnings = FALSE)
dir.create(dirname(s06_sv), recursive = TRUE, showWarnings = FALSE)

# Merge root + combined single-var CSVs (step 06b path split). Read-only on root;
# writes only to tables/combined/.
merge_single_var_results <- function(combined_path, root_path) {
  parts <- list()
  if (file.exists(combined_path)) parts <- c(parts, list(read.csv(combined_path)))
  if (file.exists(root_path))     parts <- c(parts, list(read.csv(root_path)))
  if (length(parts) == 0) return(invisible(FALSE))
  merged <- bind_rows(parts)
  key    <- paste(merged$color, merged$env_var, merged$variable, sep = "|")
  merged <- merged[!duplicated(key, fromLast = TRUE), ]
  write.csv(merged, combined_path, row.names = FALSE)
  n_models <- length(unique(paste(merged$color, merged$env_var)))
  message("Merged single-var results: ", n_models, " unique models → ", combined_path)
  invisible(TRUE)
}

COL_POS_BAR  <- "#B35D45"
COL_NEG_BAR  <- "#78B0C5"
COL_SIG      <- "#A3262A"
COL_NONSIG   <- "#999999"

COLOR_PANEL <- c(WHITE = "#D9D9D9", YELLOW = "#D9B556", REDTYPE = "#A3262D")
BAR_COLORS  <- c(WHITE = "#CCCCCC", YELLOW = "#E8B84B", PINK = "#E8A0BF",
                 "PURPLE/BLUE" = "#7B68EE", RED = "#C0392B")

theme_paper <- theme_minimal(base_size = 12, base_family = "sans") +
  theme(
    plot.title      = element_text(face = "bold", size = 13, hjust = 0.5),
    plot.subtitle   = element_text(size = 11, hjust = 0.5, colour = "grey30"),
    strip.text      = element_text(face = "bold", size = 12),
    panel.grid.minor = element_blank(),
    panel.grid.major.y = element_line(colour = "grey92"),
    legend.position = "bottom"
  )

var_label <- function(v) {
  if (v == "alt") return("Others")
  if (v %in% c("bdod", "cec", "nitrogen", "phh2o", "soc", "ocd", "ocs",
               "clay", "silt", "sand", "cfvo")) return("Soil environment")
  if (grepl("^bio", v, ignore.case = TRUE)) {
    num <- suppressWarnings(as.integer(sub("bio", "", v, ignore.case = TRUE)))
    if (num %in% c(2, 3, 4, 5))  return("Temperature variability")
    if (num == 15)                 return("Precipitation variability")
    if (num %in% 1:11)             return("Temperature level")
    if (num %in% 12:19)            return("Precipitation level")
  }
  "Others"
}

var_colors <- c(
  "Temperature level" = "#A3262A",
  "Temperature variability" = "#B8860B",
  "Precipitation level" = "#1F4E79",
  "Precipitation variability" = "#5B9BD5",
  "Soil environment" = "#E07A5F",
  "Others" = "#666666"
)

message("Loading data...")

df_species <- read.csv(species_only)
effects    <- read.csv(s06_combined)
names(effects) <- c("mean", "lower", "upper", "eff_samp", "pMCMC", "variable", "color")
loadings   <- read.csv(file.path(step05_dir, "pca_loadings.csv"))

gr_dir <- file.path(step06_tables, "convergence")
if (!dir.exists(gr_dir)) gr_dir <- step06_dir
gr_all <- bind_rows(
  read.csv(file.path(gr_dir, "gelman_rubin_WHITE.csv"))   %>% mutate(color = "WHITE"),
  read.csv(file.path(gr_dir, "gelman_rubin_YELLOW.csv"))  %>% mutate(color = "YELLOW"),
  read.csv(file.path(gr_dir, "gelman_rubin_REDTYPE.csv")) %>% mutate(color = "REDTYPE")
)

merge_single_var_results(s06_sv, s06_sv_root)

sv_file <- s06_sv
has_sv  <- file.exists(sv_file)
if (has_sv) {
  sv_effects <- read.csv(sv_file)
  if ("post.mean" %in% names(sv_effects)) {
    sv_effects <- sv_effects %>%
      rename(mean = `post.mean`, lower = `l-95% CI`, upper = `u-95% CI`)
  }
}

save_fig <- function(path, plot, w, h, dpi = 150) {
  ggsave(path, plot, width = w, height = h, dpi = dpi, bg = "white")
  message("  Saved: ", basename(path))
}

make_forest_plot <- function(eff_df, pc_levels, title, subtitle = NULL) {
  sub <- eff_df %>%
    filter(variable %in% pc_levels, variable != "(Intercept)") %>%
    mutate(
      variable   = factor(variable, levels = rev(pc_levels)),
      significant = lower > 0 | upper < 0,
      color      = factor(color, levels = c("WHITE", "YELLOW", "REDTYPE"))
    )

  ggplot(sub, aes(x = mean, y = variable, colour = significant)) +
    geom_vline(xintercept = 0, linetype = "dashed", colour = "grey50", linewidth = 0.6) +
    geom_errorbar(aes(xmin = lower, xmax = upper), width = 0.15, linewidth = 0.7) +
    geom_point(size = 2.8, shape = 21, aes(fill = significant)) +
    scale_colour_manual(values = c("TRUE" = COL_SIG, "FALSE" = COL_NONSIG), guide = "none") +
    scale_fill_manual(values = c("TRUE" = COL_SIG, "FALSE" = "white"), guide = "none") +
    facet_grid(~ color, labeller = labeller(color = c(
      WHITE = "WHITE", YELLOW = "YELLOW", REDTYPE = "REDTYPE"
    ))) +
    labs(title = title, subtitle = subtitle,
         x = "Posterior Mean (95% CI)", y = NULL) +
    theme_paper +
    theme(
      strip.background = element_rect(fill = "grey85", colour = NA),
      panel.spacing = unit(1.2, "lines")
    )
}


message("Figure 1: Colour counts...")

color_counts <- df_species %>%
  filter(!color_category %in% c("UNKNOWN", "OTHER", "GREENISH")) %>%
  count(color_category, name = "n")

p1 <- plot_colour_counts(color_counts)

save_fig(file.path(fig_dir, "fig1_colour_counts.png"), p1, 8.0, 4.4, dpi = 300)


message("Figure 3: PCA loadings...")

loading_long <- bind_rows(lapply(paste0("PC", 1:5), function(pc) {
  ord <- order(abs(loadings[[pc]]), decreasing = TRUE)[1:10]
  loadings[ord, ] %>%
    select(variable, loading = all_of(pc)) %>%
    mutate(pc = pc, var_type = vapply(variable, var_label, character(1)))
})) %>%
  mutate(
    pc = factor(pc, levels = paste0("PC", 1:5)),
    variable = factor(variable, levels = unique(variable))
  )

# Order variables within each PC by loading value
loading_long <- loading_long %>%
  group_by(pc) %>%
  arrange(loading) %>%
  mutate(
    variable = factor(variable, levels = unique(variable)),
    var_type = factor(var_type, levels = names(var_colors))
  ) %>%
  ungroup()

p3 <- ggplot(loading_long, aes(x = loading, y = variable, fill = loading > 0)) +
  geom_col(width = 0.7) +
  geom_vline(xintercept = 0, linewidth = 0.5, colour = "grey40") +
  facet_wrap(~ pc, nrow = 1, scales = "free_x") +
  scale_fill_manual(values = c("TRUE" = COL_POS_BAR, "FALSE" = COL_NEG_BAR), guide = "none") +
  scale_y_discrete(labels = function(x) x) +
  labs(title = "PCA Factor Loadings of Environmental Variables — Flora of India",
       x = "Loadings", y = NULL) +
  theme_paper +
  theme(axis.text.y = element_text(size = 8))

save_fig(file.path(fig_dir, "fig3_pca_loadings.png"), p3, 14, 7)


eff_pc <- effects %>%
  filter(variable != "(Intercept)") %>%
  mutate(significant = lower > 0 | upper < 0)

p2 <- make_forest_plot(
  eff_pc, paste0("PC", 1:5),
  "(a) Effects of environmental PCs on flower colour — Flora of India"
)
save_fig(file.path(fig_dir, "fig2_mcmc_coefficients.png"), p2, 12, 5)


message("Figure 2 supplementary: PC6–PC10...")

p2s <- make_forest_plot(
  eff_pc, paste0("PC", 6:10),
  "Supplementary: Effects of environmental PCs PC6–PC10",
  subtitle = "REDTYPE PC7 is the only significant association in this range"
)
save_fig(file.path(fig_dir, "fig2_supp_PC6_10.png"), p2s, 12, 5)


if (has_sv) {
  message("Figure 2b: Single-variable MCMC results...")
  sv <- sv_effects %>%
    filter(variable != "(Intercept)") %>%
    mutate(
      significant = lower > 0 | upper < 0,
      var_type    = vapply(env_var, var_label, character(1)),
      env_var     = factor(env_var, levels = loadings$variable)
    )

  p2b <- ggplot(sv, aes(x = mean, y = env_var, colour = significant)) +
    geom_vline(xintercept = 0, linetype = "dashed", colour = "grey50") +
    geom_errorbar(aes(xmin = lower, xmax = upper), width = 0.15, linewidth = 0.5) +
    geom_point(size = 2, shape = 21, aes(fill = significant)) +
    scale_colour_manual(values = c("TRUE" = COL_SIG, "FALSE" = COL_NONSIG), guide = "none") +
    scale_fill_manual(values = c("TRUE" = COL_SIG, "FALSE" = "white"), guide = "none") +
    facet_grid(color ~ ., scales = "free_y", space = "free_y") +
    labs(title = "(b) Effects of environmental variables on flower colour",
         x = "Posterior Mean (95% CI)", y = NULL) +
    theme_paper +
    theme(axis.text.y = element_text(size = 7))

  save_fig(file.path(fig_dir, "fig2b_mcmc_env_variables.png"), p2b, 10, 14)
} else {
  message("  fig2b skipped — single_variable_models.csv not found yet.")
}


message("Figure 4: Convergence diagnostics...")

p4 <- plot_convergence(gr_all)

save_fig(file.path(fig_dir, "fig4_convergence.png"), p4, 10.5, 4.0, dpi = 300)


message("Figure 5: Pipeline summary...")

n_parsed   <- nrow(read.csv(treatments_f))
n_species  <- nrow(df_species)
n_known    <- sum(!df_species$color_category %in% c("UNKNOWN", "OTHER", "GREENISH"))
n_gbif     <- length(list.files(gbif_cache_dir, pattern = "\\.csv$"))
n_analysis <- nrow(read.csv(env_final_f))

pipe_df <- tibble(
  stage = c("Parsed text blocks", "Species-level records", "Known flower colour",
            "GBIF matched", "Final analysis set"),
  n     = c(n_parsed, n_species, n_known, n_gbif, n_analysis)
)

p5 <- plot_pipeline(pipe_df)

save_fig(file.path(fig_dir, "fig5_pipeline_summary.png"), p5, 8.6, 4.4, dpi = 300)


message("Supplementary: Trace plots...")

if (requireNamespace("coda", quietly = TRUE)) {
  model_dir <- if (dir.exists(step06_models)) step06_models else step06_dir
  models <- list(
    WHITE   = readRDS(file.path(model_dir, "model_WHITE.rds")),
    YELLOW  = readRDS(file.path(model_dir, "model_YELLOW.rds")),
    REDTYPE = readRDS(file.path(model_dir, "model_REDTYPE.rds"))
  )

  trace_plots <- lapply(names(models), function(nm) {
    m <- models[[nm]]
    n_cols <- min(6, ncol(m$Sol))
    trace_df <- as.data.frame(m$Sol[, seq_len(n_cols), drop = FALSE]) %>%
      mutate(iter = row_number()) %>%
      pivot_longer(-iter, names_to = "parameter", values_to = "value")

    ggplot(trace_df, aes(x = iter, y = value, colour = parameter)) +
      geom_line(linewidth = 0.3, alpha = 0.85) +
      facet_wrap(~ parameter, scales = "free_y", ncol = 3) +
      labs(title = paste("MCMC Trace —", nm), x = "Sample (post burn-in/thin)", y = NULL) +
      theme_paper +
      theme(legend.position = "none", strip.text = element_text(size = 9))
  })

  p_traces <- wrap_plots(trace_plots, ncol = 1)
  save_fig(file.path(fig_dir, "figS_traceplots.png"), p_traces, 12, 16)

  # Step06 individual trace files
  for (i in seq_along(trace_plots)) {
    nm <- names(models)[i]
    save_fig(file.path(step06_fig, paste0("trace_", nm, ".png")), trace_plots[[i]], 10, 7)
  }

  p_pc13 <- make_forest_plot(eff_pc, paste0("PC", 1:3), "MCMCglmm Coefficients — PC1 to PC3")
  save_fig(file.path(step06_fig, "coefficient_plot_PC1_PC3.png"), p_pc13, 10, 4)
}

#summary
message("\n── Significant Results ─────────────────────────────────────────")
sig <- eff_pc %>% filter(significant) %>% select(color, variable, mean, lower, upper, pMCMC)
if (nrow(sig) > 0) print(sig) else message("No significant fixed effects.")

message("\n── Convergence ─────────────────────────────────────────────────")
for (i in seq_len(nrow(distinct(gr_all, color, mpsrf)))) {
  row <- distinct(gr_all, color, mpsrf)[i, ]
  st  <- if (row$mpsrf < 1.1) "CONVERGED" else "NOT CONVERGED"
  message(sprintf("  %s MPSRF: %.6f %s", row$color, row$mpsrf, st))
}

message("\nFigures saved to: ", fig_dir)

#symlinks
message("Publishing Results/ ...")
res      <- file.path(base_dir, "Results")
proc     <- file.path(base_dir, "Processed Data")
step08   <- file.path(proc, "step08_outputs_clean")

for (d in c("figures/main", "figures/supplementary", "figures/elevation",
            "tables/mcmc", "tables/elevation", "tables/descriptive")) {
  dir.create(file.path(res, d), recursive = TRUE, showWarnings = FALSE)
}

link_to <- function(src, dst) {
  if (!file.exists(src)) return(invisible(FALSE))
  if (file.exists(dst)) unlink(dst)
  file.symlink(normalizePath(src), dst)
  invisible(TRUE)
}

main_figs <- c(
  "fig1_colour_counts.png", "fig2_mcmc_coefficients.png", "fig2_supp_PC6_10.png",
  "fig2b_mcmc_env_variables.png", "fig3_pca_loadings.png", "fig4_convergence.png",
  "fig5_pipeline_summary.png"
)
for (f in main_figs) {
  link_to(file.path(fig_dir, f), file.path(res, "figures/main", f))
}
link_to(file.path(fig_dir, "figS_traceplots.png"),
        file.path(res, "figures/supplementary", "figS_traceplots.png"))
link_to(file.path(step06_fig, "coefficient_plot_PC1_PC3.png"),
        file.path(res, "figures/supplementary", "coefficient_plot_PC1_PC3.png"))

elev_fig <- file.path(step08, "figures")
if (dir.exists(elev_fig)) {
  for (f in list.files(elev_fig, pattern = "\\.png$")) {
    link_to(file.path(elev_fig, f), file.path(res, "figures/elevation", f))
  }
}

mcmc_tables <- c(
  "combined/all_fixed_effects_combined.csv", "combined/single_variable_models.csv",
  "fixed_effects/fixed_effects_WHITE.csv", "fixed_effects/fixed_effects_YELLOW.csv",
  "fixed_effects/fixed_effects_REDTYPE.csv",
  "convergence/gelman_rubin_WHITE.csv", "convergence/gelman_rubin_YELLOW.csv",
  "convergence/gelman_rubin_REDTYPE.csv",
  "random_effects/random_effects_WHITE.csv", "random_effects/random_effects_YELLOW.csv",
  "random_effects/random_effects_REDTYPE.csv"
)
for (t in mcmc_tables) {
  link_to(file.path(step06_tables, t), file.path(res, "tables/mcmc", basename(t)))
}

if (file.exists(s06_combined)) {
  eff <- read.csv(s06_combined)
  names(eff) <- c("mean", "lower", "upper", "eff_samp", "pMCMC", "variable", "color")
  sig <- eff[eff$variable != "(Intercept)" & (eff$lower > 0 | eff$upper < 0), ]
  write.csv(sig, file.path(res, "tables/mcmc/significant_results.csv"), row.names = FALSE)
}

gr_files <- list.files(file.path(step06_tables, "convergence"),
                       full.names = TRUE, pattern = "gelman")
if (length(gr_files) > 0) {
  gr <- do.call(rbind, lapply(gr_files, function(f) {
    x <- read.csv(f)
    x$color <- sub("gelman_rubin_(.*)\\.csv", "\\1", basename(f))
    x
  }))
  conv <- aggregate(point_est ~ color, gr, function(x) max(x, na.rm = TRUE))
  names(conv)[2] <- "max_psrf"
  conv$mpsrf <- sapply(conv$color, function(c) unique(gr$mpsrf[gr$color == c]))
  conv$converged <- conv$mpsrf < 1.1
  write.csv(conv, file.path(res, "tables/mcmc/convergence_summary.csv"), row.names = FALSE)
}

# No standalone summary_color_category.csv exists in the clean pipeline
# (03_04_Categorize_and_Prepare.py only prints the counts) - derive it here
# from df_species instead of depending on a file that was never regenerated.
# This path used to be a symlink into the old step04_outputs/ - if left in
# place, write.csv() would follow it and silently overwrite that legacy file.
color_summary_dst <- file.path(res, "tables/descriptive/color_category_summary.csv")
if (file.exists(color_summary_dst) && !identical(Sys.readlink(color_summary_dst), "")) {
  unlink(color_summary_dst)
}
color_summary <- df_species %>% count(color_category, name = "n")
write.csv(color_summary, color_summary_dst, row.names = FALSE)

link_to(file.path(step05_dir, "pca_loadings.csv"),
        file.path(res, "tables/descriptive/pca_loadings.csv"))

for (t in c("elevation_band_summary.csv", "elevation_mcmc_results.csv",
            "pc2_by_elevation_band.csv", "elevation_analysis_summary.txt")) {
  link_to(file.path(step08, t), file.path(res, "tables/elevation", t))
}

writeLines(c(
  "# Thesis Results", "",
  "Symlinks to `Processed Data/` outputs. Synced by `scripts/07_Generate_Figures.R`.", "",
  "## figures/", "- **main/** — fig1–fig5, MCMC coefficients",
  "- **supplementary/** — Combined trace plot (figS), coefficient diagnostic",
  "- **elevation/** — Step 08 fig6_*", "",
  "## tables/", "- **mcmc/** — MCMCglmm outputs",
  "- **elevation/** — Elevation analysis tables",
  "- **descriptive/** — Colour counts, PCA loadings", "",
  paste("Last synced:", Sys.time())
), file.path(res, "README.md"))

message("Results published to: ", res)
message("Step 07 complete.")
