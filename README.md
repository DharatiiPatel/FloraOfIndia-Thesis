# Flora of India — Flower Colour Thesis

MS Computer Science thesis (Dharati Patel, UGA): open-source LLM extraction of flower
colour from *Flora of India*, benchmarked against a human gold set, and linked to
GBIF / WorldClim / SoilGrids ecology via Bayesian mixed models.

The project has two halves:

- **Phase A — pipeline + ecology.** Scrape → parse → extract colour → GBIF → environment → MCMCglmm. Scripts `01`–`08` at the top of `scripts/`.
- **Phase B — method depth (RQ1–RQ4).** Gold-set benchmark, error taxonomy, categoriser v2 + RAG + abstention, and downstream label-sensitivity. Lives entirely under `scripts/experiments/` and `Processed Data/experiments/` so Phase A stays reproducible.

---

## Where things are

```
Thesis/
├── Results/                      ← THESIS WRITING STARTS HERE
│   ├── figures/
│   │   ├── main/                 fig1–fig5 (symlinks into Processed Data/figures)
│   │   ├── supplementary/        trace plots, PC1–PC3 coefficients
│   │   ├── elevation/            fig6_* elevation suite
│   │   └── cs_method/            fig_cs1–fig_cs7 (RQ1–RQ4), PNG + PDF
│   └── tables/                   mcmc/, descriptive/, elevation/
│
├── docs/
│   ├── Progress_Report_for_Advisor.md      ← walkthrough for meetings
│   ├── VERIFIED_Numbers_for_Thesis.md      ← every number, with its source
│   ├── Thesis_MethodDepth_Plan.md          ← RQ1–RQ4 plan
│   ├── FloraOfIndia_Thesis_Documentation.md
│   ├── ElevationGradient_NovelResearch.md
│   └── drafts/Chapter3_Data_and_Pipeline_Draft.md
│
├── scripts/
│   ├── 01a–08                    Phase A pipeline (Python + R)
│   ├── run_*.sh                  Phase A job wrappers
│   ├── experiments/              Phase B (RQ1–RQ4)
│   │   ├── parse_treatments.py           clean treatment parser
│   │   ├── make_gold_set.py              stratified gold sample
│   │   ├── baseline_rule_extractor.py    rule floor for RQ1
│   │   ├── extract_flower_color_multimodel.py   Qwen-7B/72B, Llama-70B
│   │   ├── score_models_vs_gold.py       RQ1 metrics
│   │   ├── rq2_error_taxonomy.py         RQ2 failure classes
│   │   ├── categorize_v2.py              RQ3 categoriser v2
│   │   ├── rag_extract_gold.py           RQ3 RAG + abstention
│   │   ├── score_rq3_interventions.py    RQ3 scoring
│   │   ├── wp4_*.{py,R}                  RQ4 label variants + MCMC
│   │   ├── build_cs_figures.py           all fig_cs* figures
│   │   └── *.slurm                       cluster jobs
│   └── legacy/                   superseded, kept for provenance
│
├── Processed Data/               pipeline outputs (gitignored, 3.6 GB)
│   ├── figures/                  canonical Phase A figures
│   ├── step04–step08_outputs/    Phase A stage outputs
│   ├── step05_env_data/          WorldClim / SoilGrids rasters
│   └── experiments/              Phase B outputs
│       ├── gold_set_labeled.csv          98 labelled items
│       ├── benchmark/                    RQ1 predictions + summary
│       ├── rq2_outputs/                  RQ2 taxonomy
│       ├── rq3_outputs/                  RQ3 RAG + intervention scores
│       ├── wp4_label_variants/results/   RQ4 fixed effects
│       └── figures/                      canonical fig_cs* output
│
├── raw_data/pdfs/                Flora of India source PDFs
├── logs/                         SLURM logs (verbose .out → logs/archive/)
└── R_library/                    R packages (hidden in the Explorer)
```

### Explorer is filtered

`.vscode/settings.json` hides `R_library`, `.venv_figs`, `__pycache__` and the two GBIF
cache directories (~10,700 files of the ~11,700 in the workspace). They are still on disk
and every script still reads them — only the sidebar is filtered. Set an entry to `false`
in `files.exclude` to bring one back.

---

## Key numbers

| Quantity | Value |
|---|---:|
| Unique treatments (clean parser) | 3,857 |
| With morphological description | 3,230 |
| Ecology *n* (colour + environment complete) | 1,174 |
| WHITE / YELLOW / REDTYPE | 502 / 428 / 244 |
| Gold set labelled | 98 |
| Best gold-set accuracy | 0.949 (Qwen-7B, RAG + categoriser v2) |

Always cite the categoriser version with an accuracy: 0.878 is zero-shot + v1,
0.939 is the same predictions + v2, 0.949 is RAG + v2. Full provenance for every
number is in `docs/VERIFIED_Numbers_for_Thesis.md`.

---

## Regenerating outputs

```bash
# Phase A ecology figures
module load R/4.5.1-gfbf-2025a
Rscript scripts/07_Generate_Figures.R

# Phase B CS/method figures (needs the local venv)
python -m venv .venv_figs && .venv_figs/bin/pip install matplotlib numpy pandas
.venv_figs/bin/python scripts/experiments/build_cs_figures.py
```

GPU extraction and MCMC runs are submitted with `sbatch` from `scripts/experiments/*.slurm`.
Login nodes are for submission only.
