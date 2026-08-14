#!/usr/bin/env Rscript
# Full ecology figure set from the expansion analysis (n=1438).
# Writes under Processed Data/experiments/expansion/figures/ and publishes
# symlinks into Results/figures/ so the thesis figure set tracks expansion.
# Primary n=1174 paths under Processed Data/figures/ and step06_outputs_clean/
# are left untouched (back up Results before first publish).

.libPaths(c("/scratch/dp23301/Thesis/R_library", "~/R/library", .libPaths()))
options(stringsAsFactors = FALSE)
options(bitmapType = "cairo")

for (pkg in c("ggplot2", "patchwork", "dplyr", "tidyr", "scales")) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    stop("Missing package: ", pkg)
  }
}
library(ggplot2)
library(patchwork)
library(dplyr)
library(tidyr)
library(scales)

base_dir <- "/scratch/dp23301/Thesis"
source(file.path(base_dir, "scripts/figure_style.R"))

exp_root     <- file.path(base_dir, "Processed Data/experiments/expansion")
primary_exp  <- file.path(base_dir, "Processed Data/experiments")
step05_dir   <- file.path(exp_root, "step05b_outputs")
env_final_f  <- file.path(step05_dir, "species_color_environment_final_expanded.csv")
step06_dir   <- file.path(exp_root, "step06_outputs")
step06_tables <- file.path(step06_dir, "tables")
step06_models <- file.path(step06_dir, "models")
step06_fig   <- file.path(step06_dir, "figures")
fig_dir      <- file.path(exp_root, "figures")
step08_dir   <- file.path(exp_root, "step08_outputs")

s06_combined <- file.path(step06_tables, "combined/all_fixed_effects_combined.csv")
s06_sv       <- file.path(step06_tables, "combined/single_variable_models.csv")

dir.create(fig_dir,    recursive = TRUE, showWarnings = FALSE)
dir.create(step06_fig, recursive = TRUE, showWarnings = FALSE)

COL_POS_BAR  <- "#B35D45"
COL_NEG_BAR  <- "#78B0C5"
COL_SIG      <- "#A3262A"
COL_NONSIG   <- "#999999"
COLOR_PANEL  <- c(WHITE = "#D9D9D9", YELLOW = "#D9B556", REDTYPE = "#A3262D")

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

message("Loading expansion data...")

df_analysis <- read.csv(env_final_f, check.names = FALSE)
n_analysis  <- nrow(df_analysis)
n_subtitle  <- sprintf("Expanded analysis set, n = %s", format(n_analysis, big.mark = ","))
message("Analysis N = ", n_analysis)

effects <- read.csv(s06_combined, check.names = FALSE)
# Normalise column names (MCMCglmm CSV may use "l-95% CI" or R-mangled forms)
nm <- names(effects)
rename_map <- c(
  "post.mean" = "mean", "Estimate" = "mean",
  "l-95% CI" = "lower", "l.95..CI" = "lower", "X2.5." = "lower",
  "u-95% CI" = "upper", "u.95..CI" = "upper", "X97.5." = "upper",
  "eff.samp" = "eff_samp", "eff_samp" = "eff_samp"
)
for (old in names(rename_map)) {
  if (old %in% nm) names(effects)[names(effects) == old] <- rename_map[[old]]
}
stopifnot(all(c("mean", "lower", "upper", "variable", "color") %in% names(effects)))

loadings <- read.csv(file.path(step05_dir, "pca_loadings.csv"), check.names = FALSE)

gr_dir <- file.path(step06_tables, "convergence")
gr_all <- bind_rows(
  read.csv(file.path(gr_dir, "gelman_rubin_WHITE.csv"))   %>% mutate(color = "WHITE"),
  read.csv(file.path(gr_dir, "gelman_rubin_YELLOW.csv"))  %>% mutate(color = "YELLOW"),
  read.csv(file.path(gr_dir, "gelman_rubin_REDTYPE.csv")) %>% mutate(color = "REDTYPE")
)

has_sv <- file.exists(s06_sv)
if (has_sv) {
  sv_effects <- read.csv(s06_sv, check.names = FALSE)
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
      variable    = factor(variable, levels = rev(pc_levels)),
      significant = lower > 0 | upper < 0,
      color       = factor(color, levels = c("WHITE", "YELLOW", "REDTYPE"))
    )

  ggplot(sub, aes(x = mean, y = variable, colour = significant)) +
    geom_vline(xintercept = 0, linetype = "dashed", colour = "grey50", linewidth = 0.6) +
    geom_errorbar(aes(xmin = lower, xmax = upper), width = 0.15, linewidth = 0.7) +
    geom_point(size = 2.8, shape = 21, aes(fill = significant)) +
    scale_colour_manual(values = c("TRUE" = COL_SIG, "FALSE" = COL_NONSIG), guide = "none") +
    scale_fill_manual(values = c("TRUE" = COL_SIG, "FALSE" = "white"), guide = "none") +
    facet_grid(~ color) +
    labs(title = title, subtitle = subtitle,
         x = "Posterior Mean (95% CI)", y = NULL) +
    theme_paper +
    theme(
      strip.background = element_rect(fill = "grey85", colour = NA),
      panel.spacing = unit(1.2, "lines")
    )
}

# ── Figure 1: colour counts (analysis-set composition) ───────────────────────
message("Figure 1: Colour counts...")

color_counts <- df_analysis %>%
  filter(!color_category %in% c("UNKNOWN", "OTHER", "GREENISH")) %>%
  count(color_category, name = "n")

p1 <- plot_colour_counts(color_counts) +
  labs(title = "Flower colour distribution — expanded analysis set",
       caption = n_subtitle)
save_fig(file.path(fig_dir, "fig1_colour_counts.png"), p1, 8.0, 4.4, dpi = 300)

# ── Figure 3: PCA loadings ───────────────────────────────────────────────────
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
  labs(title = "PCA Factor Loadings of Environmental Variables — Flora of India",
       subtitle = n_subtitle,
       x = "Loadings", y = NULL) +
  theme_paper +
  theme(axis.text.y = element_text(size = 8))

save_fig(file.path(fig_dir, "fig3_pca_loadings.png"), p3, 14, 7)

# ── Figure 2: MCMC coefficients ──────────────────────────────────────────────
message("Figure 2: MCMC coefficients...")

eff_pc <- effects %>%
  filter(variable != "(Intercept)") %>%
  mutate(significant = lower > 0 | upper < 0)

p2 <- make_forest_plot(
  eff_pc, paste0("PC", 1:5),
  "(a) Effects of environmental PCs on flower colour — Flora of India",
  subtitle = n_subtitle
)
save_fig(file.path(fig_dir, "fig2_mcmc_coefficients.png"), p2, 12, 5)

message("Figure 2 supplementary: PC6–PC10...")
p2s <- make_forest_plot(
  eff_pc, paste0("PC", 6:10),
  "Supplementary: Effects of environmental PCs PC6–PC10",
  subtitle = n_subtitle
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
         subtitle = n_subtitle,
         x = "Posterior Mean (95% CI)", y = NULL) +
    theme_paper +
    theme(axis.text.y = element_text(size = 7))

  save_fig(file.path(fig_dir, "fig2b_mcmc_env_variables.png"), p2b, 10, 14)
} else {
  message("  fig2b skipped — single_variable_models.csv not found for expansion.")
}

# ── Figure 4: convergence ────────────────────────────────────────────────────
message("Figure 4: Convergence diagnostics...")
p4 <- plot_convergence(gr_all) + labs(caption = n_subtitle)
save_fig(file.path(fig_dir, "fig4_convergence.png"), p4, 10.5, 4.0, dpi = 300)

# ── Figure 5: pipeline summary ───────────────────────────────────────────────
message("Figure 5: Pipeline summary...")

treatments_f <- file.path(primary_exp, "species_descriptions_treatments.csv")
new_desc_f   <- file.path(exp_root, "new_descriptions_for_extract.csv")
clean_sp_f   <- file.path(primary_exp, "clean_species_only.csv")
new_col_f    <- file.path(exp_root, "color_categories_new.csv")
occ_f        <- file.path(exp_root, "gbif_outputs/gbif_occurrences_combined.csv")

n_parsed_primary <- if (file.exists(treatments_f)) nrow(read.csv(treatments_f)) else NA_integer_
n_parsed_new     <- if (file.exists(new_desc_f)) nrow(read.csv(new_desc_f)) else 0L
n_parsed         <- sum(n_parsed_primary, n_parsed_new, na.rm = TRUE)

# Species-level colour records: primary clean + new expansion extracts
df_clean <- if (file.exists(clean_sp_f)) read.csv(clean_sp_f) else data.frame()
df_new   <- if (file.exists(new_col_f)) read.csv(new_col_f) else data.frame()
n_species <- length(unique(c(
  if (nrow(df_clean)) df_clean$binomial else character(),
  if (nrow(df_new)) df_new$binomial else character()
)))

known_cats <- c("WHITE", "YELLOW", "RED", "PINK", "PURPLE/BLUE")
n_known <- length(unique(c(
  if (nrow(df_clean)) df_clean$binomial[df_clean$color_category %in% known_cats] else character(),
  if (nrow(df_new)) df_new$binomial[df_new$color_category %in% known_cats] else character()
)))

# Unique GBIF-matched binomials (query_name) without loading 1.8M rows into R
n_gbif <- as.integer(system(paste(
  "tail -n +2", shQuote(occ_f), "| cut -d, -f1 | sed 's/\"//g' | sort -u | wc -l"
), intern = TRUE))

pipe_df <- tibble(
  stage = c("Parsed text blocks", "Species-level records", "Known flower colour",
            "GBIF matched", "Final analysis set"),
  n     = c(n_parsed, n_species, n_known, n_gbif, n_analysis)
)

p5 <- plot_pipeline(pipe_df) +
  labs(title = "Species retention through the expansion pipeline",
       caption = n_subtitle)
save_fig(file.path(fig_dir, "fig5_pipeline_summary.png"), p5, 8.6, 4.4, dpi = 300)

# Compact coefficient plot (legacy expansion artefact name)
p_exp <- make_forest_plot(
  eff_pc, paste0("PC", 1:10),
  "Expanded MCMCglmm fixed effects (PC1–PC10)",
  subtitle = n_subtitle
)
save_fig(file.path(fig_dir, "coefficient_plot_expanded.png"), p_exp, 10, 8)

writeLines(c(
  paste("expanded_n_species", n_analysis),
  paste("WHITE", sum(df_analysis$is_white)),
  paste("YELLOW", sum(df_analysis$is_yellow)),
  paste("REDTYPE", sum(df_analysis$is_redtype)),
  paste("generated", as.character(Sys.time()))
), file.path(fig_dir, "expanded_n_summary.txt"))

# ── Supplementary traces ─────────────────────────────────────────────────────
message("Supplementary: Trace plots...")

if (requireNamespace("coda", quietly = TRUE) && dir.exists(step06_models)) {
  models <- list(
    WHITE   = readRDS(file.path(step06_models, "model_WHITE.rds")),
    YELLOW  = readRDS(file.path(step06_models, "model_YELLOW.rds")),
    REDTYPE = readRDS(file.path(step06_models, "model_REDTYPE.rds"))
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
      labs(title = paste("MCMC Trace —", nm),
           subtitle = n_subtitle,
           x = "Sample (post burn-in/thin)", y = NULL) +
      theme_paper +
      theme(legend.position = "none", strip.text = element_text(size = 9))
  })

  p_traces <- wrap_plots(trace_plots, ncol = 1)
  save_fig(file.path(fig_dir, "figS_traceplots.png"), p_traces, 12, 16)

  for (i in seq_along(trace_plots)) {
    nm <- names(models)[i]
    save_fig(file.path(step06_fig, paste0("trace_", nm, ".png")), trace_plots[[i]], 10, 7)
  }

  p_pc13 <- make_forest_plot(eff_pc, paste0("PC", 1:3),
                             "MCMCglmm Coefficients — PC1 to PC3",
                             subtitle = n_subtitle)
  save_fig(file.path(step06_fig, "coefficient_plot_PC1_PC3.png"), p_pc13, 10, 4)
  save_fig(file.path(fig_dir, "coefficient_plot_PC1_PC3.png"), p_pc13, 10, 4)
} else {
  message("  Trace plots skipped (coda / models missing).")
}

message("\n── Significant Results ─────────────────────────────────────────")
sig <- eff_pc %>% filter(significant) %>% select(color, variable, mean, lower, upper, pMCMC)
if (nrow(sig) > 0) print(sig) else message("No significant fixed effects.")

message("\n── Convergence ─────────────────────────────────────────────────")
conv_rows <- distinct(gr_all, color, mpsrf)
for (i in seq_len(nrow(conv_rows))) {
  row <- conv_rows[i, ]
  st  <- if (row$mpsrf < 1.1) "CONVERGED" else "NOT CONVERGED"
  message(sprintf("  %s MPSRF: %.6f %s", row$color, row$mpsrf, st))
}

# ── Publish to Results/ ──────────────────────────────────────────────────────
message("Publishing Results/ from expansion outputs...")
res  <- file.path(base_dir, "Results")
proc <- file.path(base_dir, "Processed Data")

for (d in c("figures/main", "figures/supplementary", "figures/elevation",
            "tables/mcmc", "tables/elevation", "tables/descriptive")) {
  dir.create(file.path(res, d), recursive = TRUE, showWarnings = FALSE)
}

link_to <- function(src, dst) {
  if (!file.exists(src)) return(invisible(FALSE))
  if (file.exists(dst)) unlink(dst)
  # Broken symlink: exists() is FALSE but readlink is non-NA
  rl <- Sys.readlink(dst)
  if (!is.na(rl) && nzchar(rl)) unlink(dst)
  file.symlink(normalizePath(src), dst)
  invisible(TRUE)
}

main_figs <- c(
  "fig1_colour_counts.png", "fig2_mcmc_coefficients.png", "fig2_supp_PC6_10.png",
  "fig3_pca_loadings.png", "fig4_convergence.png", "fig5_pipeline_summary.png"
)
for (f in main_figs) {
  link_to(file.path(fig_dir, f), file.path(res, "figures/main", f))
}
# fig2b only if regenerated for expansion; otherwise drop stale n1174 symlink
fig2b_src <- file.path(fig_dir, "fig2b_mcmc_env_variables.png")
fig2b_dst <- file.path(res, "figures/main", "fig2b_mcmc_env_variables.png")
if (file.exists(fig2b_src)) {
  link_to(fig2b_src, fig2b_dst)
} else if (file.exists(fig2b_dst) || file.lexists(fig2b_dst)) {
  unlink(fig2b_dst)
  message("  Removed stale Results fig2b (no expansion single-variable models).")
}

link_to(file.path(fig_dir, "figS_traceplots.png"),
        file.path(res, "figures/supplementary", "figS_traceplots.png"))
link_to(file.path(fig_dir, "coefficient_plot_PC1_PC3.png"),
        file.path(res, "figures/supplementary", "coefficient_plot_PC1_PC3.png"))

elev_fig <- file.path(step08_dir, "figures")
if (dir.exists(elev_fig)) {
  for (f in list.files(elev_fig, pattern = "\\.png$")) {
    link_to(file.path(elev_fig, f), file.path(res, "figures/elevation", f))
  }
}

mcmc_tables <- c(
  "combined/all_fixed_effects_combined.csv",
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

sig_out <- effects %>%
  filter(variable != "(Intercept)", lower > 0 | upper < 0)
write.csv(sig_out, file.path(res, "tables/mcmc/significant_results.csv"), row.names = FALSE)

gr_files <- list.files(gr_dir, full.names = TRUE, pattern = "gelman")
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

color_summary_dst <- file.path(res, "tables/descriptive/color_category_summary.csv")
if (file.exists(color_summary_dst) && !identical(Sys.readlink(color_summary_dst), "")) {
  unlink(color_summary_dst)
}
write.csv(color_counts, color_summary_dst, row.names = FALSE)

link_to(file.path(step05_dir, "pca_loadings.csv"),
        file.path(res, "tables/descriptive/pca_loadings.csv"))

if (dir.exists(step08_dir)) {
  for (t in c("elevation_band_summary.csv", "elevation_mcmc_results.csv",
              "pc2_by_elevation_band.csv", "elevation_analysis_summary.txt")) {
    link_to(file.path(step08_dir, t), file.path(res, "tables/elevation", t))
  }
}

writeLines(c(
  "# Thesis Results", "",
  "Published figure/table set tracks the **expansion** ecology analysis (n=1,438).",
  "Synced by `scripts/07_Generate_Figures_Expansion.R`.", "",
  "Primary n=1,174 artefacts remain under `Processed Data/figures/` /",
  "`step06_outputs_clean/` / `step08_outputs_clean/`. Backup of the previous",
  "Results ecology set: `Results/figures/main_n1174_backup/`.", "",
  "## figures/",
  "- **main/** — fig1–fig5 from expansion; fig7–fig14 method/prediction unchanged",
  "- **supplementary/** — traces + PC1–PC3 coefficient diagnostic",
  "- **elevation/** — Step 08 expansion fig6_* (when step08 expansion has run)", "",
  "## tables/",
  "- **mcmc/** — expansion MCMCglmm outputs",
  "- **elevation/** — expansion elevation tables (when available)",
  "- **descriptive/** — colour counts, PCA loadings", "",
  paste("Last synced:", Sys.time()),
  paste("Analysis N:", n_analysis)
), file.path(res, "README.md"))

message("Results published to: ", res)
message("Expansion Step 07 complete (N=", n_analysis, ").")
