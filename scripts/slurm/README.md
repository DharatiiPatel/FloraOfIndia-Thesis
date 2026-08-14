# SLURM / job wrappers

All cluster submission scripts live here (`run_*.slurm`, `run_*.sh`, and
`submit_expansion_chain.sh`). Pipeline `.py` / `.R` scripts stay in `scripts/`
(and `scripts/legacy/`).

## Submit from repo root

```bash
cd /scratch/dp23301/Thesis
sbatch scripts/slurm/<name>.slurm
# or
bash scripts/slurm/submit_expansion_chain.sh
```

Wrappers `cd` to the Thesis root before calling `python scripts/...` or
`Rscript scripts/...`, so relative paths remain correct when submitted via
`sbatch scripts/slurm/...`. Log paths use absolute `/scratch/dp23301/Thesis/logs/`.

## Notes

- Active ecology / expansion / OCR / recovery jobs: `run_05*`–`run_08*`, `run_30*`–`run_35*`.
- Multimodel / RAG / MCMC array: `run_11_*`, `run_15_rag.slurm`, `run_19_array.slurm`.
- Archived LoRA jobs (Python stays in `scripts/legacy/`): `run_26_lora*.slurm`.
- Older GBIF/env wrappers renamed on move: `run_05a_legacy.sh`, `run_05b_legacy.sh`.
