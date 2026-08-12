#!/bin/bash
#SBATCH --job-name=reocr_pilot
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=04:00:00
#SBATCH --output=/scratch/dp23301/Thesis/logs/reocr_pilot_%A.out

# Re-OCR pilot: ONE volume, compare quality before committing to all 8.
# tesseract is CPU-only, so no GPU needed. Uses cluster modules (all free).

module purge
module load tesseract/5.5.0-GCCcore-13.3.0
module load poppler/25.07.0-GCC-13.3.0
module load pdf2image/1.17.0-GCCcore-13.3.0-gbpip
module load pytesseract/0.3.13-GCCcore-13.3.0-gbpip

cd /scratch/dp23301/Thesis

# ---- EDIT THIS to the PDF you transferred ----
PDF="raw_data/pdfs/FLORA OF INDIA VOL.1.pdf"
OUT="Processed Data/experiments/reocr_text/VOL.1.txt"

# For a FAST pilot, do the first 40 pages only (remove --max-pages for full volume).
python scripts/experiments/exploratory/reocr_pdf.py \
    --pdf "$PDF" \
    --out "$OUT" \
    --dpi 400 --psm 6 --oem 1 \
    --max-pages 40

echo "Pilot OCR complete. Next: run compare_ocr_quality.py"
