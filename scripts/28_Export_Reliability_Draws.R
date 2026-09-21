#!/usr/bin/env Rscript
# Export thinned posterior draws of the focal effects from the reliability chains so
# the appendix convergence figure (fig18) can be built in Python alongside fig15-17.
#
# Reads  : Processed Data/experiments/reliability/chains_<subset>_<COLOUR>_<kind>.rds
#          (written by scripts/25_Reliability_Ecology.R; a list of per-chain Sol matrices)
#          plus reliability_mcmc_effects.csv to learn which effect is focal per model.
# Writes : Processed Data/experiments/reliability/reliability_chain_draws.csv
#
# Cheap and read-only with respect to the MCMC: safe to re-run without refitting.

args_all <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args_all[grepl("^--file=", args_all)])
root <- if (length(file_arg) != 1) getwd() else dirname(dirname(normalizePath(file_arg)))

options(stringsAsFactors = FALSE)

REL <- file.path(root, "Processed Data/experiments/reliability")
THIN_TO <- 1000   # points per chain in the figure; plenty for a trace panel

effects <- read.csv(file.path(REL, "reliability_mcmc_effects.csv"))

out <- list()
for (i in seq_len(nrow(effects))) {
  r <- effects[i, ]
  kind <- if (identical(r$effect, "alt_scaled")) "elev" else "pc"
  f <- file.path(REL, sprintf("chains_%s_%s_%s.rds", r$subset, r$color, kind))
  if (!file.exists(f)) {
    message("MISSING (skipped): ", basename(f))
    next
  }
  chains <- readRDS(f)
  for (ci in seq_along(chains)) {
    sol <- as.matrix(chains[[ci]])
    if (!r$effect %in% colnames(sol)) {
      message("effect ", r$effect, " absent from ", basename(f))
      next
    }
    x <- sol[, r$effect]
    idx <- unique(round(seq(1, length(x), length.out = min(THIN_TO, length(x)))))
    out[[length(out) + 1]] <- data.frame(
      subset = r$subset, color = r$color, effect = r$effect,
      chain = ci, iter = idx, value = as.numeric(x[idx])
    )
  }
}

draws <- do.call(rbind, out)
dest <- file.path(REL, "reliability_chain_draws.csv")
write.csv(draws, dest, row.names = FALSE)
message("wrote ", nrow(draws), " draws for ",
        length(unique(paste(draws$subset, draws$color, draws$effect))),
        " models -> ", dest)
