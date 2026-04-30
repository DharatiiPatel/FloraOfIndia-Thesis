#!/usr/bin/env Rscript

# =============================================================================
# Step 06: MCMCglmm Statistical Analysis
# Flora of India - Flower Colour & Environment Analysis
# =============================================================================
# This script:
#   1. Loads species x environment PCA scores from step 05b
#   2. Fits Bayesian hierarchical threshold models (MCMCglmm)
#      for each flower colour (WHITE, YELLOW, REDTYPE)
#   3. Uses phylogenetic covariance as random effect (if available)
#      OR genus/family as random effects (fallback)
#   4. Checks convergence (Gelman-Rubin diagnostics)
#   5. Runs single-variable models for individual environmental factors
#   6. Saves all results and figures
# =============================================================================

.libPaths(c("~/R/library", .libPaths()))
options(stringsAsFactors = FALSE)
options(bitmapType = "cairo")

# ── Packages ──────────────────────────────────────────────────────────────────
required_packages <- c("MCMCglmm", "ape", "coda")
for (pkg in required_packages) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    install.packages(pkg, lib = "~/R/library", repos = "https://cloud.r-project.org")
  }
  library(pkg, character.only = TRUE)
}

# ── Paths ─────────────────────────────────────────────────────────────────────
base_dir   <- "/scratch/dp23301/Thesis"
input_file <- file.path(base_dir, "Processed Data/step05_outputs/species_color_environment_final.csv")
output_dir <- file.path(base_dir, "Processed Data/step06_outputs")
fig_dir    <- file.path(output_dir, "figures")

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(fig_dir,    recursive = TRUE, showWarnings = FALSE)

# ── MCMC Settings (matching original paper) ───────────────────────────────────
NITT    <- 1050000   # total iterations
BURNIN  <- 50000     # burn-in
THIN    <- 100       # thinning interval
# Effective samples = (1050000 - 50000) / 100 = 10000

# Prior: weak prior for random effect variance
# V=1, nu=0.002 matches original paper
PRIOR <- list(
  R = list(V = 1, fix = 1),
  G = list(G1 = list(V = 1, nu = 0.002))
)

# ── Load data ─────────────────────────────────────────────────────────────────
message("Loading data: ", input_file)
df <- read.csv(input_file, encoding = "UTF-8")

message("Total species: ", nrow(df))
message("Colour breakdown:")
print(table(df$color_group))

# Check required columns
pc_cols <- paste0("PC", 1:10)
missing <- setdiff(c(pc_cols, "is_white", "is_yellow", "is_redtype", "query_name"), names(df))
if (length(missing) > 0) {
  stop("Missing columns: ", paste(missing, collapse = ", "))
}

# Extract genus from query_name for random effects
df$genus  <- sapply(strsplit(df$query_name, " "), function(x) x[1])

# ── Helper: run MCMCglmm for one colour ───────────────────────────────────────
run_mcmc_model <- function(data, response_col, label, random_formula = "~ genus") {

  message("\n", strrep("─", 60))
  message("Running MCMCglmm for: ", label)
  message(strrep("─", 60))

  # Build formula
  fixed_formula  <- as.formula(paste(response_col, "~", paste(pc_cols, collapse = " + ")))
  random_formula <- as.formula(random_formula)

  message("Fixed formula: ", deparse(fixed_formula))
  message("N species: ", nrow(data))
  message("N positive: ", sum(data[[response_col]]))

  set.seed(42)

  model <- tryCatch({
    MCMCglmm(
      fixed   = fixed_formula,
      random  = random_formula,
      data    = data,
      family  = "threshold",
      prior   = PRIOR,
      nitt    = NITT,
      burnin  = BURNIN,
      thin    = THIN,
      verbose = TRUE
    )
  }, error = function(e) {
    message("ERROR in MCMCglmm: ", conditionMessage(e))
    return(NULL)
  })

  return(model)
}

# ── Helper: extract and save results ─────────────────────────────────────────
save_model_results <- function(model, label, output_dir) {

  if (is.null(model)) {
    message("Skipping results for ", label, " - model failed")
    return(NULL)
  }

  # Fixed effects summary
  fixed_summary <- summary(model)$solutions
  fixed_df <- as.data.frame(fixed_summary)
  fixed_df$variable <- rownames(fixed_df)
  fixed_df$color    <- label

  out_fixed <- file.path(output_dir, paste0("fixed_effects_", label, ".csv"))
  write.csv(fixed_df, out_fixed, row.names = FALSE)
  message("Saved fixed effects: ", out_fixed)

  # Random effect variance
  rand_summary <- summary(model)$Gcovariances
  rand_df <- as.data.frame(rand_summary)
  rand_df$color <- label

  out_rand <- file.path(output_dir, paste0("random_effects_", label, ".csv"))
  write.csv(rand_df, out_rand, row.names = FALSE)

  # Gelman-Rubin convergence (need multiple chains - run 3 chains)
  message("Checking convergence for ", label, "...")

  # Run 2 more chains for Gelman-Rubin
  set.seed(123)
  model2 <- tryCatch({
    MCMCglmm(
      fixed   = model$Fixed$formula,
      random  = model$Random$formula,
      data    = df,
      family  = "threshold",
      prior   = PRIOR,
      nitt    = NITT,
      burnin  = BURNIN,
      thin    = THIN,
      verbose = FALSE
    )
  }, error = function(e) NULL)

  set.seed(456)
  model3 <- tryCatch({
    MCMCglmm(
      fixed   = model$Fixed$formula,
      random  = model$Random$formula,
      data    = df,
      family  = "threshold",
      prior   = PRIOR,
      nitt    = NITT,
      burnin  = BURNIN,
      thin    = THIN,
      verbose = FALSE
    )
  }, error = function(e) NULL)

  if (!is.null(model2) && !is.null(model3)) {
    chains <- mcmc.list(model$Sol, model2$Sol, model3$Sol)
    gr     <- gelman.diag(chains, multivariate = TRUE)

    gr_df <- data.frame(
      variable = rownames(gr$psrf),
      point_est = gr$psrf[, 1],
      upper_CI  = gr$psrf[, 2],
      mpsrf     = gr$mpsrf,
      color     = label
    )

    out_gr <- file.path(output_dir, paste0("gelman_rubin_", label, ".csv"))
    write.csv(gr_df, out_gr, row.names = FALSE)
    message("MPSRF for ", label, ": ", round(gr$mpsrf, 6))
  }

  # Save trace plots
  png(file.path(fig_dir, paste0("trace_", label, ".png")),
      width = 1200, height = 800)
  plot(model$Sol[, 1:min(6, ncol(model$Sol))])
  dev.off()

  return(fixed_df)
}

# ── Run main models ───────────────────────────────────────────────────────────
colors_to_run <- list(
  list(col = "is_white",   label = "WHITE"),
  list(col = "is_yellow",  label = "YELLOW"),
  list(col = "is_redtype", label = "REDTYPE")
)

all_fixed_effects <- list()

for (color_info in colors_to_run) {

  model <- run_mcmc_model(
    data           = df,
    response_col   = color_info$col,
    label          = color_info$label,
    random_formula = "~ genus"
  )

  results <- save_model_results(model, color_info$label, output_dir)
  if (!is.null(results)) {
    all_fixed_effects[[color_info$label]] <- results
  }

  # Save model object
  model_file <- file.path(output_dir, paste0("model_", color_info$label, ".rds"))
  saveRDS(model, model_file)
  message("Saved model: ", model_file)
}

# ── Combine all fixed effects ─────────────────────────────────────────────────
if (length(all_fixed_effects) > 0) {
  combined_effects <- do.call(rbind, all_fixed_effects)
  write.csv(combined_effects,
            file.path(output_dir, "all_fixed_effects_combined.csv"),
            row.names = FALSE)
  message("\nSaved combined fixed effects table")
}

# ── Single variable models ────────────────────────────────────────────────────
message("\n", strrep("─", 60))
message("Running single-variable models...")
message(strrep("─", 60))

# Load PCA loadings to identify top environmental variables
loadings_file <- file.path(base_dir,
  "Processed Data/step05_outputs/pca_loadings.csv")

if (file.exists(loadings_file)) {

  loadings <- read.csv(loadings_file)
  env_vars <- loadings$variable

  single_var_results <- list()

  for (color_info in colors_to_run) {
    for (env_var in env_vars) {

      if (!env_var %in% names(df)) next

      label_sv <- paste0(color_info$label, "_", env_var)
      message("  Single var model: ", label_sv)

      formula_sv <- as.formula(paste(color_info$col, "~", env_var))

      sv_model <- tryCatch({
        MCMCglmm(
          fixed   = formula_sv,
          random  = ~ genus,
          data    = df,
          family  = "threshold",
          prior   = PRIOR,
          nitt    = NITT,
          burnin  = BURNIN,
          thin    = THIN,
          verbose = FALSE
        )
      }, error = function(e) NULL)

      if (!is.null(sv_model)) {
        sv_summary <- as.data.frame(summary(sv_model)$solutions)
        sv_summary$variable  <- rownames(sv_summary)
        sv_summary$env_var   <- env_var
        sv_summary$color     <- color_info$label
        single_var_results[[label_sv]] <- sv_summary
      }
    }
  }

  if (length(single_var_results) > 0) {
    sv_combined <- do.call(rbind, single_var_results)
    write.csv(sv_combined,
              file.path(output_dir, "single_variable_models.csv"),
              row.names = FALSE)
    message("Saved single variable model results")
  }
}

# ── Generate coefficient plot ─────────────────────────────────────────────────
message("\nGenerating coefficient plots...")

if (length(all_fixed_effects) > 0) {

  combined <- do.call(rbind, all_fixed_effects)
  combined <- combined[combined$variable != "(Intercept)", ]

  # Rename columns if needed
  names(combined)[names(combined) == "post.mean"] <- "mean"
  names(combined)[names(combined) == "l-95% CI"]  <- "lower"
  names(combined)[names(combined) == "u-95% CI"]  <- "upper"

  # Mark significant (CI doesn't overlap zero)
  combined$significant <- (combined$lower > 0 | combined$upper < 0)

  png(file.path(fig_dir, "coefficient_plot_PC1_PC3.png"),
      width = 1200, height = 600)

  par(mfrow = c(1, 3), mar = c(5, 4, 3, 1))

  for (col_label in c("WHITE", "YELLOW", "REDTYPE")) {

    sub <- combined[combined$color == col_label &
                    combined$variable %in% c("PC1", "PC2", "PC3"), ]

    if (nrow(sub) == 0) next

    ylim <- range(c(sub$lower, sub$upper), na.rm = TRUE)

    plot(1:nrow(sub), sub$mean,
         ylim   = ylim,
         xaxt   = "n",
         xlab   = "",
         ylab   = "Coefficient",
         main   = col_label,
         pch    = 19,
         col    = ifelse(sub$significant, "black", "grey60"),
         cex    = 1.5)

    axis(1, at = 1:nrow(sub), labels = sub$variable, las = 2)
    abline(h = 0, lty = 2, col = "red")

    arrows(1:nrow(sub), sub$lower,
           1:nrow(sub), sub$upper,
           angle  = 90,
           code   = 3,
           length = 0.05,
           col    = ifelse(sub$significant, "black", "grey60"))
  }

  dev.off()
  message("Saved coefficient plot")
}

message("\n── Step 06 Complete ────────────────────────────────────────────")
message("Results saved to: ", output_dir)
message("Figures saved to: ", fig_dir)
message("────────────────────────────────────────────────────────────────")