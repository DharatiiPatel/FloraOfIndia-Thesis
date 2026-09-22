#!/usr/bin/env Rscript
# One MCMCglmm task (variant x colour x chain) from the manifest + SLURM_ARRAY_TASK_ID.
# MCMC settings match scripts/06_MCMCglmm.R.

.libPaths(c("~/R/library", .libPaths()))
options(stringsAsFactors = FALSE)

suppressMessages({
  library(MCMCglmm)
})

BASE <- "/scratch/dp23301/Thesis"
VARDIR <- file.path(BASE, "Processed Data/experiments/wp4_label_variants")
MANIFEST <- file.path(VARDIR, "mcmc_manifest.csv")
OUTDIR <- file.path(VARDIR, "mcmc_chains")
dir.create(OUTDIR, recursive = TRUE, showWarnings = FALSE)

NITT   <- 1050000
BURNIN <- 50000
THIN   <- 100
PRIOR  <- list(R = list(V = 1, fix = 1),
               G = list(G1 = list(V = 1, nu = 0.002)))
PC_COLS <- paste0("PC", 1:10)

tid <- Sys.getenv("SLURM_ARRAY_TASK_ID", unset = NA)
if (is.na(tid)) {
  args <- commandArgs(trailingOnly = TRUE)
  if (length(args) >= 1) tid <- args[1] else stop("No SLURM_ARRAY_TASK_ID / arg")
}
tid <- as.integer(tid)

man <- read.csv(MANIFEST)
row <- man[man$task_id == tid, ]
if (nrow(row) != 1) stop("task_id ", tid, " not found in manifest")

variant  <- row$variant
dataset  <- row$dataset_path
response <- row$response_col
color    <- row$color_label
chain    <- row$chain
seed     <- row$seed

message(sprintf("TASK %d | variant=%s colour=%s chain=%d seed=%d",
                tid, variant, color, chain, seed))

df <- read.csv(dataset, encoding = "UTF-8")
df$genus <- sapply(strsplit(df$query_name, " "), function(x) x[1])

fixed_formula <- as.formula(paste(response, "~", paste(PC_COLS, collapse = " + ")))
message("N species: ", nrow(df), " | N positive: ", sum(df[[response]]))

set.seed(seed)
model <- MCMCglmm(
  fixed  = fixed_formula,
  random = ~ genus,
  data   = df,
  family = "threshold",
  prior  = PRIOR,
  nitt   = NITT, burnin = BURNIN, thin = THIN,
  verbose = FALSE
)

# save only the fixed-effect posterior chain (Sol) -> small, enough for
# Gelman-Rubin + posterior summaries in the combine step
out <- file.path(OUTDIR, sprintf("%s_%s_chain%d.rds", variant, color, chain))
saveRDS(model$Sol, out)
message("Saved: ", out)
