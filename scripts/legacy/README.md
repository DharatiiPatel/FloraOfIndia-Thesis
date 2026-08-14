# Legacy scripts

Superseded pipeline versions and abandoned experiments. Kept for provenance;
do not treat as the active thesis path.

## LoRA / supervised adaptation (archived 2026-08-14)

Moved here because LoRA fine-tuning on the gold set was judged not to make
sense for the thesis scope (small labelled n; protocol abandoned):

- `24_Prepare_Finetune_Data.py`
- `25_Lock_Baselines.py`
- `26_LoRA_Finetune.py`
- `27_Score_Adaptation.py`
- `../slurm/run_26_lora.slurm` / `../slurm/run_26_lora_pilot.slurm` (moved to scripts/slurm/)

## UNKNOWN-colour diagnosis (archived 2026-08-14)

- `28_Diagnose_Unknown_Colour.py` — early diagnosis of UNKNOWN / dropped species.

That diagnosis was **superseded by the recovery pipeline** (`scripts/29`+;
fascicle OCR / recover lost treatments / colour extract). Keep 29+ as the
active path; do not re-run 28 for thesis results.

## Other moved SLURM wrappers

- `gpu_extract_flower_color_qwen.slurm` → `scripts/slurm/` (with all other job wrappers).
