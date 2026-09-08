# Flora of India — Flower Colour Thesis

MS Computer Science thesis (Dharati Patel, University of Georgia).
Open-source language models extract flower colour from the *Flora of India*;
those labels are evaluated against a human gold set and linked to GBIF /
WorldClim / SoilGrids for Bayesian colour–environment models.

Scripts are numbered `01a`–`23` in run order. See `scripts/README.md`.

## Layout

```
Thesis/
├── Results/                 figures and tables for the thesis
│   ├── figures/ecology/     fig1–fig6
│   ├── figures/methods/     fig7–fig14
│   ├── figures/supplementary/
│   └── tables/              mcmc/, elevation/, descriptive/
├── docs/
│   └── VERIFIED_Numbers_for_Thesis.md
├── scripts/                 01a–23, then lib/ and slurm/
├── Processed Data/          pipeline outputs (gitignored)
└── raw_data/                Flora of India PDFs (gitignored)
```

## Key numbers

| Quantity | Value |
|---|---:|
| Unique treatments | 3,857 |
| With morphological description | 3,230 |
| Ecology *n* (primary) | 1,438 |
| WHITE / YELLOW / REDTYPE | 613 / 494 / 331 |
| Gold set labelled | 98 |
| Best gold-set accuracy | 0.949 (Qwen-7B, RAG + categoriser v2) |

Always cite the categoriser with an accuracy: 0.878 is zero-shot + v1,
0.939 is the same predictions + v2, 0.949 is RAG + v2.
Provenance: `docs/VERIFIED_Numbers_for_Thesis.md`.

## Regenerating figures

```bash
module load R/4.5.1-gfbf-2025a
Rscript scripts/07_Generate_Figures.R

python -m venv .venv_figs && .venv_figs/bin/pip install matplotlib numpy pandas scikit-learn
.venv_figs/bin/python scripts/22_Build_Method_Figures.py
.venv_figs/bin/python scripts/21_Predict_Colour_from_Env.py
.venv_figs/bin/python scripts/23_Build_Prediction_Figure.py
```

GPU and MCMC jobs: `sbatch` from `scripts/slurm/` at the thesis root.
