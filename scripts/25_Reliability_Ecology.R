#!/usr/bin/env Rscript
# Confidence-stratified ecology: same models on common-known support vs
# high-confidence (three-LLM agreement). Primary colour = Qwen-7B v2.
#
# UNKNOWN/OTHER rows are not in these CSVs (never coded as is_white=0).
#
# Default: shorter MCMC so the chapter can be drafted. Set
#   RELIABILITY_FULL=1
# to match scripts/06_MCMCglmm.R (nitt=1.05e6).
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

suppressPackageStartupMessages({
  library(MCMCglmm)
  library(dplyr)
})

out_dir <- file.path(root, "Processed Data/experiments/reliability")
res_dir <- file.path(root, "Results/tables/reliability")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(res_dir, recursive = TRUE, showWarnings = FALSE)

full <- identical(Sys.getenv("RELIABILITY_FULL", ""), "1")
if (full) {
  NITT <- 1050000; BURNIN <- 50000; THIN <- 100
} else {
  NITT <- 55000; BURNIN <- 5000; THIN <- 50
}
PRIOR <- list(R = list(V = 1, fix = 1), G = list(G1 = list(V = 1, nu = 0.002)))
pc_cols <- paste0("PC", 1:10)

message("Reliability ecology MCMC  nitt=", NITT, " burnin=", BURNIN, " thin=", THIN)
message("RELIABILITY_FULL=", full)

fit_pc <- function(df, response, label) {
  message("  ", label, " ~ PC1+...+PC10  n=", nrow(df),
          " positives=", sum(df[[response]]))
  set.seed(42)
  MCMCglmm(
    fixed  = as.formula(paste(response, "~", paste(pc_cols, collapse = " + "))),
    random = ~ genus,
    data   = df,
    family = "threshold",
    prior  = PRIOR,
    nitt   = NITT,
    burnin = BURNIN,
    thin   = THIN,
    verbose = FALSE
  )
}

fit_elev <- function(df, response, label) {
  d <- df[!is.na(df$alt) & df$alt >= 0, ]
  d$alt_scaled <- as.numeric(scale(d$alt))
  message("  ", label, " ~ alt_scaled  n=", nrow(d),
          " positives=", sum(d[[response]]))
  set.seed(42)
  list(model = MCMCglmm(
    fixed  = as.formula(paste(response, "~ alt_scaled")),
    random = ~ genus,
    data   = d,
    family = "threshold",
    prior  = PRIOR,
    nitt   = NITT,
    burnin = BURNIN,
    thin   = THIN,
    verbose = FALSE
  ), n = nrow(d))
}

extract_row <- function(model, subset_name, n, effect, color, response) {
  sol <- summary(model)$solutions
  if (!effect %in% rownames(sol)) {
    return(NULL)
  }
  data.frame(
    subset = subset_name,
    n = n,
    color = color,
    response = response,
    effect = effect,
    mean = unname(sol[effect, "post.mean"]),
    lower = unname(sol[effect, "l-95% CI"]),
    upper = unname(sol[effect, "u-95% CI"]),
    pMCMC = unname(sol[effect, "pMCMC"]),
    excludes_zero = as.integer(sol[effect, "l-95% CI"] > 0 | sol[effect, "u-95% CI"] < 0),
    direction = ifelse(sol[effect, "post.mean"] > 0, "+", "-"),
    nitt = NITT,
    stringsAsFactors = FALSE
  )
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
    m <- fit_pc(df, sp$col, sp$lab)
    rows[[length(rows) + 1]] <- extract_row(m, subset_name, nrow(df), sp$effect, sp$lab, sp$col)
    saveRDS(m, file.path(out_dir, sprintf("model_%s_%s_pc.rds", subset_name, sp$lab)))
  }
  for (sp in specs) {
    ev <- fit_elev(df, sp$col, sp$lab)
    rows[[length(rows) + 1]] <- extract_row(
      ev$model, subset_name, ev$n, "alt_scaled", sp$lab, sp$col
    )
    saveRDS(ev$model, file.path(out_dir, sprintf("model_%s_%s_elev.rds", subset_name, sp$lab)))
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

write.csv(effects, file.path(out_dir, "reliability_mcmc_effects.csv"), row.names = FALSE)
write.csv(robust, file.path(out_dir, "reliability_robustness_table.csv"), row.names = FALSE)
write.csv(effects, file.path(res_dir, "reliability_mcmc_effects.csv"), row.names = FALSE)
write.csv(robust, file.path(res_dir, "reliability_robustness_table.csv"), row.names = FALSE)
message("Wrote reliability MCMC tables")
print(robust)
