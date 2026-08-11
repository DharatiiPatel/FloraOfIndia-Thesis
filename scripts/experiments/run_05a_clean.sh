#!/bin/bash
#SBATCH --job-name=gbif_clean
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=48:00:00
#SBATCH --output=/scratch/dp23301/Thesis/logs/gbif_clean_%j.out
#SBATCH --error=/scratch/dp23301/Thesis/logs/gbif_clean_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=dp23301@uga.edu

cd /scratch/dp23301/Thesis
mkdir -p logs
module purge
unset PYTHONPATH
module load R/4.5.1-gfbf-2025a
Rscript scripts/experiments/05a_GBIF_clean.R
