#!/bin/bash
# Regenerate figures after single-variable MCMC completes.
# Usage: sbatch --dependency=afterok:45825091 scripts/slurm/run_07_after_06b.sh
#SBATCH --job-name=figures_post_sv
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=/scratch/dp23301/Thesis/logs/figures_post_sv_%j.out
#SBATCH --error=/scratch/dp23301/Thesis/logs/figures_post_sv_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=dp23301@uga.edu

cd /scratch/dp23301/Thesis
module load R/4.5.1-gfbf-2025a
Rscript scripts/07_Generate_Figures.R
