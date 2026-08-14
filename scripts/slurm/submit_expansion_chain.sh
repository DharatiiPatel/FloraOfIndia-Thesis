#!/bin/bash
# Submit the full expansion chain with SLURM dependencies.
# Primary n=1174 outputs are never overwritten.
#
# Usage:  bash scripts/slurm/submit_expansion_chain.sh
# Then:   squeue -u $USER

set -euo pipefail
cd /scratch/dp23301/Thesis
mkdir -p logs "Processed Data/experiments/expansion"

echo "=== 0. Download missing fascicle PDFs (lightweight) ==="
module load Python/3.13.5-GCCcore-14.3.0
python scripts/30_Download_Fascicles.py

# Drop ballooned pilot OCR PDF if present (sidecar txt is enough)
rm -f raw_data/fascicles/F11_Cucurbitaceae_ocr.pdf

echo ""
echo "=== 1. Submit jobs ==="

OCR=$(sbatch --parsable scripts/slurm/run_30_ocr_fascicles_array.slurm)
echo "OCR_ARRAY          $OCR  (array 1-24%6)"

REC=$(sbatch --parsable scripts/slurm/run_31_recover_lost.slurm)
echo "RECOVER_LOST       $REC"

PARSE=$(sbatch --parsable --dependency=afterok:${OCR} scripts/slurm/run_33_parse_fascicles.slurm)
echo "PARSE_FASCICLES    $PARSE  afterok:$OCR"

BUILD_EX=$(sbatch --parsable --dependency=afterok:${PARSE}:${REC} scripts/slurm/run_35a_extract_input.slurm)
echo "BUILD_EXTRACT_IN   $BUILD_EX  afterok:$PARSE:$REC"

QWEN=$(sbatch --parsable --dependency=afterok:${BUILD_EX} scripts/slurm/run_34_extract_expansion.slurm)
echo "QWEN_EXPAND        $QWEN  afterok:$BUILD_EX  (GPU)"

BUILD_GB=$(sbatch --parsable --dependency=afterok:${QWEN} scripts/slurm/run_35b_gbif_input.slurm)
echo "BUILD_GBIF_IN      $BUILD_GB  afterok:$QWEN"

GBIF=$(sbatch --parsable --dependency=afterok:${BUILD_GB} scripts/slurm/run_05a_expansion.slurm)
echo "GBIF_EXPAND        $GBIF  afterok:$BUILD_GB  (new species only)"

ENV=$(sbatch --parsable --dependency=afterok:${GBIF} scripts/slurm/run_05b_expansion.slurm)
echo "ENV_EXPAND         $ENV  afterok:$GBIF"

MCMC=$(sbatch --parsable --dependency=afterok:${ENV} scripts/slurm/run_06_expansion.slurm)
echo "MCMC_EXPAND        $MCMC  afterok:$ENV"

FIG=$(sbatch --parsable --dependency=afterok:${MCMC} scripts/slurm/run_07_expansion.slurm)
echo "FIG_EXPAND         $FIG  afterok:$MCMC"

JOBS_FILE=Processed\ Data/experiments/expansion/JOB_CHAIN.txt
cat > "$JOBS_FILE" <<EOF
Expansion job chain submitted $(date -Is)
Primary n=1174 paths are untouched.

OCR_ARRAY=$OCR
RECOVER_LOST=$REC
PARSE_FASCICLES=$PARSE
BUILD_EXTRACT_IN=$BUILD_EX
QWEN_EXPAND=$QWEN
BUILD_GBIF_IN=$BUILD_GB
GBIF_EXPAND=$GBIF
ENV_EXPAND=$ENV
MCMC_EXPAND=$MCMC
FIG_EXPAND=$FIG

Dependency graph:
  OCR_ARRAY ──────────────────────────> PARSE_FASCICLES ──┐
  RECOVER_LOST ───────────────────────────────────────────┴> BUILD_EXTRACT_IN
        -> QWEN_EXPAND -> BUILD_GBIF_IN -> GBIF_EXPAND
        -> ENV_EXPAND -> MCMC_EXPAND -> FIG_EXPAND

Monitor:
  squeue -u \$USER
  tail -f logs/ocr_fasc_${OCR}_*.out
  tail -f logs/recover_lost_${REC}.out
  tail -f logs/qwen_expand_${QWEN}.out
  tail -f logs/gbif_expand_${GBIF}.out
  tail -f logs/mcmc_expand_${MCMC}.out

Outputs (all under Processed Data/experiments/expansion/ unless noted):
  fascicle OCR txt:     raw_data/fascicles/F{N}_{slug}.txt
  recovered texts:      ../recovered_treatments.csv (parent experiments/)
  new descriptions:     new_descriptions_for_extract.csv
  new colours:          flower_color_new.csv
  GBIF new:             gbif_outputs/gbif_occurrences_new.csv
  combined occ:         gbif_outputs/gbif_occurrences_combined.csv
  env+PCA final:        step05b_outputs/species_color_environment_final_expanded.csv
  MCMCglmm:             step06_outputs/
  figures:              figures/

NOT started: label-variant array (run_19), elevation re-run, primary pipeline overwrite.
EOF

echo ""
echo "Wrote $JOBS_FILE"
echo ""
squeue -u "$USER"
