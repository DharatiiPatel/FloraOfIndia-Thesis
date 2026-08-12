#!/bin/bash
#SBATCH --job-name=wp4_mcmc
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=08:00:00
#SBATCH --output=/scratch/dp23301/Thesis/logs/wp4_mcmc_%A_%a.out
#SBATCH --error=/scratch/dp23301/Thesis/logs/wp4_mcmc_%A_%a.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=dp23301@uga.edu

# Submit with an explicit array range printed by 18_Make_MCMC_Manifest.py, e.g.:
#   sbatch --array=0-17 scripts/run_19_array.slurm
# Each task runs ONE (variant x colour x chain) MCMCglmm in parallel.

module purge
unset PYTHONPATH
module load R/4.5.1-gfbf-2025a

cd /scratch/dp23301/Thesis
Rscript scripts/19_MCMCglmm_Array.R
