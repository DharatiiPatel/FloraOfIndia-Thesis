#!/bin/bash
#SBATCH --job-name=rel_ecology
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=24:00:00
#SBATCH --output=/scratch/dp23301/Thesis/logs/reliability_ecology_%j.out
#SBATCH --error=/scratch/dp23301/Thesis/logs/reliability_ecology_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=dp23301@uga.edu

set -euo pipefail
cd /scratch/dp23301/Thesis
mkdir -p logs
module load R/4.5.1-gfbf-2025a
# Match scripts/06_MCMCglmm.R chain length
export RELIABILITY_FULL=1
Rscript scripts/25_Reliability_Ecology.R
# figures need matplotlib; base Python module lacks it, use the repo venv
.venv_figs/bin/python scripts/26_Build_Reliability_Figures.py
