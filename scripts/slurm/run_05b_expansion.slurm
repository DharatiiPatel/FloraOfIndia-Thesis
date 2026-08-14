#!/bin/bash
#SBATCH --job-name=env_expand
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=06:00:00
#SBATCH --output=/scratch/dp23301/Thesis/logs/env_expand_%j.out
#SBATCH --error=/scratch/dp23301/Thesis/logs/env_expand_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=dp23301@uga.edu

set -euo pipefail
cd /scratch/dp23301/Thesis
module load GDAL/3.11.1-foss-2025a
module load R/4.5.1-gfbf-2025a
Rscript scripts/05b_Environment_Expansion.R
