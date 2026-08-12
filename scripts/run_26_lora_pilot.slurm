#!/bin/bash
#SBATCH --job-name=lora_pilot
#SBATCH --partition=gpu_p
#SBATCH --gres=gpu:A100:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=01:30:00
#SBATCH --output=/scratch/dp23301/Thesis/logs/lora_pilot_%j.out
#SBATCH --error=/scratch/dp23301/Thesis/logs/lora_pilot_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=dp23301@uga.edu

# Fold 0 only, with sample generations printed. Run this BEFORE the full
# 5-fold job to confirm the model is learning the task rather than memorising
# species ids, and to get a real per-fold timing for the full job's --time.

module purge
unset PYTHONPATH
module load Python/3.13.5-GCCcore-14.3.0
export HF_HOME=/scratch/dp23301/.cache/huggingface
# These nodes cannot reach huggingface.co (proxy 403), and transformers 4.57
# otherwise tries a model_info() lookup on load. The script resolves the repo
# id to its cached snapshot directory, which skips that call.
export HF_HUB_OFFLINE=1

cd /scratch/dp23301/Thesis
mkdir -p logs

nvidia-smi

python scripts/26_LoRA_Finetune.py --pilot --epochs 3
