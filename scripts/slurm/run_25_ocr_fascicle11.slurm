#!/bin/bash
#SBATCH --job-name=ocr_f11
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=/scratch/dp23301/Thesis/logs/ocr_f11_%j.out
#SBATCH --error=/scratch/dp23301/Thesis/logs/ocr_f11_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=dp23301@uga.edu

# OCR Fascicle 11 (Cucurbitaceae) on a compute node.
# Do NOT use module purge on this cluster - it breaks the module system.
# Ghostscript must be loaded before ocrmypdf (needs `gs` on PATH).

set -euo pipefail

module load Ghostscript/10.03.1-GCCcore-13.3.0
module load tesseract/5.5.0-GCCcore-13.3.0
module load ocrmypdf/16.12.0-GCCcore-13.3.0-gbpip

cd /scratch/dp23301/Thesis
mkdir -p logs raw_data/fascicles

IN=raw_data/fascicles/F11_Cucurbitaceae.pdf
OUT_PDF=raw_data/fascicles/F11_Cucurbitaceae_ocr.pdf
OUT_TXT=raw_data/fascicles/F11_Cucurbitaceae.txt

echo "host=$(hostname)  date=$(date)"
echo "IN=$IN ($(wc -c < "$IN") bytes)"
which gs tesseract ocrmypdf
gs --version | head -1
tesseract --version | head -1
ocrmypdf --version

# Keep previous sidecar if present, for comparison
if [[ -f "$OUT_TXT" ]]; then
  mv -f "$OUT_TXT" "${OUT_TXT}.pre_slurm"
  echo "moved prior txt -> ${OUT_TXT}.pre_slurm"
fi

# --force-ocr: pages are image scans with no usable text layer
# --jobs: match allocated CPUs
# --sidecar: write plain text for the parser without needing a second pass
ocrmypdf \
  --force-ocr \
  --jobs "${SLURM_CPUS_PER_TASK}" \
  --sidecar "$OUT_TXT" \
  --output-type pdf \
  "$IN" \
  "$OUT_PDF"

echo "DONE $(date)"
ls -la "$OUT_PDF" "$OUT_TXT"
wc -l -c "$OUT_TXT"
echo "=== text head ==="
head -30 "$OUT_TXT"
echo "=== text tail ==="
tail -20 "$OUT_TXT"
