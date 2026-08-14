#!/bin/bash
#SBATCH --job-name=lora_5fold
#SBATCH --partition=gpu_p
#SBATCH --gres=gpu:A100:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=06:00:00
#SBATCH --output=/scratch/dp23301/Thesis/logs/lora_5fold_%j.out
#SBATCH --error=/scratch/dp23301/Thesis/logs/lora_5fold_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=dp23301@uga.edu

# Full 5-fold LoRA run. Resumable: folds already present in
# finetune/lora_predictions.csv are skipped, so a requeue picks up where it
# stopped rather than retraining from fold 0.

module purge
unset PYTHONPATH
module load Python/3.13.5-GCCcore-14.3.0
export HF_HOME=/scratch/dp23301/.cache/huggingface
# See run_26_lora_pilot.slurm: offline + cached-snapshot resolution avoids the
# transformers 4.57 model_info() call that these nodes cannot make.
export HF_HUB_OFFLINE=1

cd /scratch/dp23301/Thesis
mkdir -p logs

nvidia-smi

python scripts/legacy/26_LoRA_Finetune.py --folds all --epochs 3
