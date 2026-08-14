#!/bin/bash
#SBATCH --job-name=mcmc_expand
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=24:00:00
#SBATCH --output=/scratch/dp23301/Thesis/logs/mcmc_expand_%j.out
#SBATCH --error=/scratch/dp23301/Thesis/logs/mcmc_expand_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=dp23301@uga.edu

# Expanded MCMCglmm -> experiments/expansion/step06_outputs/
# Primary step06_outputs_clean untouched.
set -euo pipefail
cd /scratch/dp23301/Thesis
module load R/4.5.1-gfbf-2025a
Rscript scripts/06_MCMCglmm_Expansion.R
