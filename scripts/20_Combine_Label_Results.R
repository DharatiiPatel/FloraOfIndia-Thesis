#!/usr/bin/env Rscript
# Combine parallel MCMC chains into the label-sensitivity table.
# Per (variant x colour): Gelman-Rubin across 3 chains and pooled posterior summaries.

.libPaths(c("~/R/library", .libPaths()))
options(stringsAsFactors = FALSE)
suppressMessages({ library(coda) })

BASE <- "/scratch/dp23301/Thesis"
VARDIR <- file.path(BASE, "Processed Data/experiments/wp4_label_variants")
MANIFEST <- file.path(VARDIR, "mcmc_manifest.csv")
CHAINDIR <- file.path(VARDIR, "mcmc_chains")
OUTDIR <- file.path(VARDIR, "results")
dir.create(OUTDIR, recursive = TRUE, showWarnings = FALSE)

man <- read.csv(MANIFEST)
combos <- unique(man[, c("variant", "color_label")])

pmcmc <- function(x) {
  2 * min(mean(x > 0), mean(x < 0))
}

all_rows <- list()
converge_rows <- list()

for (i in seq_len(nrow(combos))) {
  variant <- combos$variant[i]
  color   <- combos$color_label[i]

  files <- file.path(CHAINDIR, sprintf("%s_%s_chain%d.rds", variant, color, 1:3))
  if (!all(file.exists(files))) {
    message("SKIP (missing chains): ", variant, " / ", color)
    next
  }
  chains <- lapply(files, readRDS)
  ml <- as.mcmc.list(lapply(chains, as.mcmc))

  gr <- tryCatch(gelman.diag(ml, multivariate = TRUE, autoburnin = FALSE),
                 error = function(e) NULL)
  mpsrf <- if (!is.null(gr)) gr$mpsrf else NA
  converge_rows[[length(converge_rows) + 1]] <-
    data.frame(variant = variant, color = color, mpsrf = mpsrf)

  pooled <- do.call(rbind, chains)
  for (v in colnames(pooled)) {
    x <- pooled[, v]
    lo <- as.numeric(quantile(x, 0.025))
    hi <- as.numeric(quantile(x, 0.975))
    all_rows[[length(all_rows) + 1]] <- data.frame(
      variant = variant, color = color, variable = v,
      post_mean = mean(x), lower95 = lo, upper95 = hi,
      pMCMC = pmcmc(x), significant = (lo > 0 | hi < 0)
    )
  }
}

fixed <- do.call(rbind, all_rows)
conv  <- do.call(rbind, converge_rows)

write.csv(fixed, file.path(OUTDIR, "wp4_fixed_effects_all_variants.csv"), row.names = FALSE)
write.csv(conv,  file.path(OUTDIR, "wp4_convergence.csv"), row.names = FALSE)

sig <- fixed[fixed$significant & fixed$variable != "(Intercept)", ]
message("\n=== SIGNIFICANT colour~environment associations by variant ===")
if (nrow(sig) == 0) {
  message("  (none)")
} else {
  sig$dir <- ifelse(sig$post_mean > 0, "+", "-")
  for (vn in unique(sig$variant)) {
    s <- sig[sig$variant == vn, ]
    message("\n  [", vn, "]")
    for (j in seq_len(nrow(s))) {
      message(sprintf("    %-8s %-5s %s  (mean=%.3f, pMCMC=%.4f)",
                      s$color[j], s$variable[j], s$dir[j],
                      s$post_mean[j], s$pMCMC[j]))
    }
  }
}

message("\n=== Headline check (WHITE~PC2 should be +, YELLOW~PC2 should be -) ===")
for (vn in unique(fixed$variant)) {
  wp2 <- fixed[fixed$variant == vn & fixed$color == "WHITE"  & fixed$variable == "PC2", ]
  yp2 <- fixed[fixed$variant == vn & fixed$color == "YELLOW" & fixed$variable == "PC2", ]
  fmt <- function(r) if (nrow(r)) sprintf("mean=%.3f p=%.4f sig=%s",
                                          r$post_mean, r$pMCMC, r$significant) else "NA"
  message(sprintf("  [%s] WHITE~PC2: %s | YELLOW~PC2: %s", vn, fmt(wp2), fmt(yp2)))
}

message("\nSaved: ", file.path(OUTDIR, "wp4_fixed_effects_all_variants.csv"))
message("Saved: ", file.path(OUTDIR, "wp4_convergence.csv"))
message("WP4 combine complete.")
