#!/bin/bash
#SBATCH --job-name=gbif_expand
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=24:00:00
#SBATCH --output=/scratch/dp23301/Thesis/logs/gbif_expand_%j.out
#SBATCH --error=/scratch/dp23301/Thesis/logs/gbif_expand_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=dp23301@uga.edu

# NEW species only; reuses gbif_cache_clean. Primary outputs untouched.
set -euo pipefail
cd /scratch/dp23301/Thesis
mkdir -p logs
module load R/4.5.1-gfbf-2025a
Rscript scripts/05a_GBIF_Expansion.R
