#!/bin/bash
#SBATCH --job-name=gbif_fetch
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=08:00:00
#SBATCH --output=/scratch/dp23301/Thesis/logs/gbif_fetch_%j.out
#SBATCH --error=/scratch/dp23301/Thesis/logs/gbif_fetch_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=dp23301@uga.edu

cd /scratch/dp23301/Thesis
mkdir -p logs
module load R/4.4.1-gfbf-2023b
Rscript scripts/legacy/05a_GBIF_seed_cache.R

