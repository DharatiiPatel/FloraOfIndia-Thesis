#!/bin/bash
#SBATCH --job-name=fig_expand
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=/scratch/dp23301/Thesis/logs/fig_expand_%j.out
#SBATCH --error=/scratch/dp23301/Thesis/logs/fig_expand_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=dp23301@uga.edu

set -euo pipefail
cd /scratch/dp23301/Thesis
mkdir -p logs
module load R/4.5.1-gfbf-2025a
echo "Starting Expansion Step 07: full ecology figure set (n=1438)"
Rscript scripts/07_Generate_Figures_Expansion.R
