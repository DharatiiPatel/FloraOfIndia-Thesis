#!/usr/bin/env Rscript
# Confidence-stratified ecology: same models on common-known support vs
# high-confidence (three-LLM agreement). Primary colour = Qwen-7B v2.
#
# UNKNOWN/OTHER rows are not in these CSVs (never coded as is_white=0).
#
# Three independent chains per model; inference uses the pooled posterior and
# convergence is reported as Gelman-Rubin MPSRF (reliability_convergence.csv),
# matching scripts/06_MCMCglmm.R and the RQ4 harness.
#
# Default: shorter MCMC so the chapter can be drafted. Set
#   RELIABILITY_FULL=1
# to match scripts/06_MCMCglmm.R (nitt=1.05e6).
# MCMC_SMOKE=1 runs throwaway chains to test the I/O path only.
#
# Genus random intercept only: genus-adjusted, not phylogenetically corrected.

args_all <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args_all[grepl("^--file=", args_all)])
if (length(file_arg) != 1) {
  root <- getwd()
} else {
  root <- dirname(dirname(normalizePath(file_arg)))
}

.libPaths(c(file.path(Sys.getenv("HOME"), "R/library"),
            file.path(root, "R_library"), .libPaths()))
options(stringsAsFactors = FALSE)
options(bitmapType = "cairo")   # headless nodes have no X11

suppressPackageStartupMessages({
  library(MCMCglmm)
  library(coda)
  library(dplyr)
})

out_dir <- file.path(root, "Processed Data/experiments/reliability")
res_dir <- file.path(root, "Results/tables/reliability")
fig_dir <- file.path(out_dir, "figures")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(res_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(fig_dir, recursive = TRUE, showWarnings = FALSE)

full <- identical(Sys.getenv("RELIABILITY_FULL", ""), "1")
if (full) {
  NITT <- 1050000; BURNIN <- 50000; THIN <- 100
} else {
  NITT <- 55000; BURNIN <- 5000; THIN <- 50
}
if (identical(Sys.getenv("MCMC_SMOKE", ""), "1")) {
  NITT <- 3000; BURNIN <- 500; THIN <- 5
  message("*** MCMC_SMOKE=1: short chains, results are NOT publishable ***")
}
PRIOR <- list(R = list(V = 1, fix = 1), G = list(G1 = list(V = 1, nu = 0.002)))
pc_cols <- paste0("PC", 1:10)

# Three independent chains from different seeds, as in scripts/06_MCMCglmm.R and
# the RQ4 harness (19/20). Inference pools all three; convergence is assessed
# with Gelman-Rubin across them.
CHAIN_SEEDS <- c(42, 123, 456)

message("Reliability ecology MCMC  nitt=", NITT, " burnin=", BURNIN, " thin=", THIN)
message("RELIABILITY_FULL=", full, "  chains=", length(CHAIN_SEEDS))

fit_chains <- function(data, formula_str, label) {
  lapply(seq_along(CHAIN_SEEDS), function(i) {
    message("    chain ", i, "/", length(CHAIN_SEEDS), " (seed ", CHAIN_SEEDS[i], ")")
    set.seed(CHAIN_SEEDS[i])
    MCMCglmm(
      fixed   = as.formula(formula_str),
      random  = ~ genus,
      data    = data,
      family  = "threshold",
      prior   = PRIOR,
      nitt    = NITT,
      burnin  = BURNIN,
      thin    = THIN,
      verbose = FALSE
    )
  })
}

fit_pc <- function(df, response, label) {
  message("  ", label, " ~ PC1+...+PC10  n=", nrow(df),
          " positives=", sum(df[[response]]))
  fit_chains(df, paste(response, "~", paste(pc_cols, collapse = " + ")), label)
}

fit_elev <- function(df, response, label) {
  d <- df[!is.na(df$alt) & df$alt >= 0, ]
  d$alt_scaled <- as.numeric(scale(d$alt))
  message("  ", label, " ~ alt_scaled  n=", nrow(d),
          " positives=", sum(d[[response]]))
  list(models = fit_chains(d, paste(response, "~ alt_scaled"), label), n = nrow(d))
}

# Pooled posterior across chains, replicating summary.MCMCglmm's own arithmetic
# (verified to 10 d.p. against summary() on a single chain) so that pooled
# numbers stay directly comparable with the rest of the thesis.
extract_row <- function(models, subset_name, n, effect, color, response) {
  sols <- lapply(models, function(m) as.mcmc(as.matrix(m$Sol)))
  if (!effect %in% colnames(sols[[1]])) return(NULL)

  gr <- tryCatch(gelman.diag(as.mcmc.list(sols), multivariate = TRUE,
                             autoburnin = FALSE),
                 error = function(e) NULL)
  mpsrf    <- if (is.null(gr)) NA_real_ else gr$mpsrf
  max_psrf <- if (is.null(gr)) NA_real_ else max(gr$psrf[, 1], na.rm = TRUE)

  x <- unlist(lapply(sols, function(s) s[, effect]), use.names = FALSE)
  hpd <- HPDinterval(as.mcmc(x))
  # ESS summed per chain (concatenated chains are not one contiguous series)
  ess <- sum(vapply(sols, function(s) effectiveSize(s[, effect]), numeric(1)))
  pmcmc <- 2 * max(0.5 / length(x),
                   min(sum(x > 0) / length(x), sum(x < 0) / length(x)))

  data.frame(
    subset = subset_name,
    n = n,
    color = color,
    response = response,
    effect = effect,
    mean = mean(x),
    lower = unname(hpd[1]),
    upper = unname(hpd[2]),
    pMCMC = pmcmc,
    excludes_zero = as.integer(hpd[1] > 0 | hpd[2] < 0),
    direction = ifelse(mean(x) > 0, "+", "-"),
    nitt = NITT,
    n_chains = length(models),
    n_samples_pooled = length(x),
    eff_samp = ess,
    mpsrf = mpsrf,
    max_psrf = max_psrf,
    converged = as.integer(!is.na(mpsrf) & mpsrf < 1.01 &
                             !is.na(max_psrf) & max_psrf < 1.01),
    stringsAsFactors = FALSE
  )
}

# Trace of the focal effect across chains — visual convergence evidence.
# Wrapped: a plotting-device failure must never discard completed MCMC work.
save_trace <- function(models, effect, tag) {
  tryCatch({
    png(file.path(fig_dir, paste0("trace_", tag, ".png")),
        width = 900, height = 420)
    on.exit(dev.off(), add = TRUE)
    mat <- vapply(models, function(m) as.matrix(m$Sol)[, effect],
                  numeric(nrow(models[[1]]$Sol)))
    matplot(mat, type = "l", lty = 1, col = c("#1B6C6F", "#B4642A", "#5A6FA8"),
            xlab = "stored iteration", ylab = effect,
            main = paste0(tag, "  (", ncol(mat), " chains)"))
    abline(h = mean(mat), lty = 2, col = "grey40")
  }, error = function(e) {
    message("    (trace plot skipped: ", conditionMessage(e), ")")
  })
}

run_subset <- function(path, subset_name) {
  df <- read.csv(path, encoding = "UTF-8")
  stopifnot(all(c("is_white", "is_yellow", "is_redtype", "genus") %in% names(df)))
  if (any(is.na(df$is_white))) stop("NA in is_white: UNKNOWN leaked into ecology file")
  rows <- list()
  specs <- list(
    list(col = "is_white",   lab = "WHITE",   effect = "PC2"),
    list(col = "is_yellow",  lab = "YELLOW",  effect = "PC2"),
    list(col = "is_redtype", lab = "REDTYPE", effect = "PC3")
  )
  for (sp in specs) {
    ms <- fit_pc(df, sp$col, sp$lab)
    rows[[length(rows) + 1]] <- extract_row(ms, subset_name, nrow(df), sp$effect, sp$lab, sp$col)
    tag <- sprintf("%s_%s_pc", subset_name, sp$lab)
    save_trace(ms, sp$effect, tag)
    # chain 1 full model (back-compatible filename) + all chains' Sol for diagnostics
    saveRDS(ms[[1]], file.path(out_dir, sprintf("model_%s.rds", tag)))
    saveRDS(lapply(ms, function(m) m$Sol),
            file.path(out_dir, sprintf("chains_%s.rds", tag)))
  }
  for (sp in specs) {
    ev <- fit_elev(df, sp$col, sp$lab)
    rows[[length(rows) + 1]] <- extract_row(
      ev$models, subset_name, ev$n, "alt_scaled", sp$lab, sp$col
    )
    tag <- sprintf("%s_%s_elev", subset_name, sp$lab)
    save_trace(ev$models, "alt_scaled", tag)
    saveRDS(ev$models[[1]], file.path(out_dir, sprintf("model_%s.rds", tag)))
    saveRDS(lapply(ev$models, function(m) m$Sol),
            file.path(out_dir, sprintf("chains_%s.rds", tag)))
  }
  bind_rows(rows)
}

common <- file.path(out_dir, "ecology_common_known.csv")
high   <- file.path(out_dir, "ecology_high_confidence.csv")
if (!file.exists(common) || !file.exists(high)) {
  stop("Run python scripts/24_Build_Reliability_Set.py first")
}

effects <- bind_rows(
  run_subset(common, "common_known"),
  run_subset(high, "high_confidence")
)

# Robust vs label-sensitive: same sign and zero-exclusion on both subsets
wide <- effects %>%
  mutate(key = paste(color, effect, sep = "~")) %>%
  select(key, subset, n, mean, lower, upper, pMCMC, excludes_zero, direction)

keys <- unique(wide$key)
robust_rows <- lapply(keys, function(k) {
  a <- wide %>% filter(key == k, subset == "common_known")
  b <- wide %>% filter(key == k, subset == "high_confidence")
  if (nrow(a) != 1 || nrow(b) != 1) return(NULL)
  same_dir <- a$direction == b$direction
  both_ex  <- a$excludes_zero == 1 & b$excludes_zero == 1
  designation <- if (same_dir && both_ex) {
    "robust"
  } else if (same_dir) {
    "same_direction_interval_changes"
  } else {
    "label-sensitive"
  }
  data.frame(
    effect = k,
    n_common_known = a$n,
    n_high_confidence = b$n,
    mean_common = a$mean, lower_common = a$lower, upper_common = a$upper,
    p_common = a$pMCMC, dir_common = a$direction, excl0_common = a$excludes_zero,
    mean_high = b$mean, lower_high = b$lower, upper_high = b$upper,
    p_high = b$pMCMC, dir_high = b$direction, excl0_high = b$excludes_zero,
    designation = designation,
    stringsAsFactors = FALSE
  )
})
robust <- bind_rows(robust_rows)

convergence <- effects %>%
  transmute(
    subset, color, effect, n,
    n_chains, nitt, n_samples_pooled,
    eff_samp = round(eff_samp, 1),
    mpsrf = round(mpsrf, 6),
    max_psrf = round(max_psrf, 6),
    converged
  )

write.csv(effects, file.path(out_dir, "reliability_mcmc_effects.csv"), row.names = FALSE)
write.csv(robust, file.path(out_dir, "reliability_robustness_table.csv"), row.names = FALSE)
write.csv(convergence, file.path(out_dir, "reliability_convergence.csv"), row.names = FALSE)
write.csv(effects, file.path(res_dir, "reliability_mcmc_effects.csv"), row.names = FALSE)
write.csv(robust, file.path(res_dir, "reliability_robustness_table.csv"), row.names = FALSE)
write.csv(convergence, file.path(res_dir, "reliability_convergence.csv"), row.names = FALSE)
message("Wrote reliability MCMC tables")
print(robust)

message("\nConvergence (Gelman-Rubin across ", length(CHAIN_SEEDS), " chains):")
print(convergence)
message("max MPSRF = ", round(max(convergence$mpsrf, na.rm = TRUE), 6),
        "   min pooled ESS = ", round(min(convergence$eff_samp, na.rm = TRUE), 1))
if (any(convergence$converged == 0)) {
  warning("Some models did not meet MPSRF < 1.01 — inspect reliability_convergence.csv ",
          "before citing these estimates.")
} else {
  message("All models converged (MPSRF < 1.01 and max PSRF < 1.01).")
}
