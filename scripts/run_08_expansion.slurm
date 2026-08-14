#!/bin/bash
#SBATCH --job-name=elev_expand
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=24:00:00
#SBATCH --output=/scratch/dp23301/Thesis/logs/elev_expand_%j.out
#SBATCH --error=/scratch/dp23301/Thesis/logs/elev_expand_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=dp23301@uga.edu

set -euo pipefail
cd /scratch/dp23301/Thesis
mkdir -p logs
module load R/4.5.1-gfbf-2025a
echo "Starting Expansion Step 08: Elevation Gradient Analysis (n=1438)"
# Full MCMC (unset SKIP). Descriptive panels are written in the same run.
unset SKIP_ELEV_MCMC || true
Rscript scripts/08_ElevationGradient_Expansion.R
