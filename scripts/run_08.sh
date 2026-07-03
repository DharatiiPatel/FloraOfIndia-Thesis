#!/bin/bash
#SBATCH --job-name=elev_grad
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=24:00:00
#SBATCH --output=/scratch/dp23301/Thesis/logs/elev_grad_%j.out
#SBATCH --error=/scratch/dp23301/Thesis/logs/elev_grad_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=dp23301@uga.edu

cd /scratch/dp23301/Thesis
module load R/4.5.1-gfbf-2025a
echo "Starting Step 08: Elevation Gradient Analysis"
Rscript scripts/08_ElevationGradient_Analysis.R
