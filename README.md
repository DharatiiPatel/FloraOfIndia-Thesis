# Flora of India — Flower Colour Thesis

MS Computer Science thesis (Dharati Patel, UGA): open-source LLM extraction of flower
colour from *Flora of India*, benchmarked against a human gold set, and linked to
GBIF / WorldClim / SoilGrids ecology via Bayesian mixed models.

It is one pipeline, not two parallel tracks, and everything lives directly
in `scripts/`: `01a`–`08` scrape, parse, extract colour, fetch
GBIF/environment data, and fit the Bayesian models; `09`–`23` are the
method-depth work built on top of that same pipeline — a gold-set
benchmark (RQ1), an error taxonomy (RQ2), interventions: categoriser v2 +
RAG + abstention (RQ3), a label-sensitivity check across four independent
label sources (RQ4), and a prediction task testing whether colour is
predictable from environment at all. Superseded script versions live in
`scripts/legacy/` for provenance, not because two pipelines coexist.

---

## Where things are

```
Thesis/
├── Results/                      ← THESIS WRITING STARTS HERE
│   ├── figures/
│   │   ├── main/                 fig1–fig14: ecology (fig1–fig5, symlinks into Processed Data/figures)
│   │   │                         + method depth RQ1–RQ4 and prediction (fig7–fig14), PNG + PDF
│   │   ├── supplementary/        trace plots, PC1–PC3 coefficients
│   │   └── elevation/            fig6_* elevation suite
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
│   ├── 01a_Scraping_FloraOfIndia.py       scrape BSI PDF links
│   ├── 01b_Extract_text_from_pdfs.py      OCR / text extraction
│   ├── 01c_Parse_Treatments.py            treatment-boundary parser
│   ├── 02_Extract_Flower_Colour.py        Qwen2.5-7B colour extraction (GPU)
│   ├── 03_04_Categorize_and_Prepare.py    categorise + prep (absorbs old 03+04)
│   ├── 05a_GBIF_Occurrences.R             GBIF occurrence fetch
│   ├── 05b_Environment_Link.R             WorldClim/SoilGrids + PCA
│   ├── 06_MCMCglmm.R / 06b_*.R            Bayesian mixed models
│   ├── 07_Generate_Figures.R              fig1–fig6 + Results/ symlinks
│   ├── 08_ElevationGradient_Analysis.R    elevation gradient extension
│   ├── run_*.sh / run_*.slurm             SLURM wrappers for the above
│   ├── 09_Make_Gold_Set.py                stratified gold sample
│   ├── 09b_Flag_Gold_Set_Junk.py          pre-flag malformed rows
│   ├── 10_Baseline_Rule_Extractor.py      rule floor for RQ1
│   ├── 11_Extract_Multimodel.py           Qwen-7B/72B, Llama-70B
│   ├── 12_Score_Models_vs_Gold.py         RQ1 metrics
│   ├── 13_Error_Taxonomy.py               RQ2 failure classes
│   ├── 14_Categorize_v2.py                RQ3 categoriser v2
│   ├── 15_RAG_Extract_Gold.py             RQ3 RAG + abstention
│   ├── 16_Score_Interventions.py          RQ3 scoring
│   ├── 17_Build_Label_Variant.py          RQ4 per-label-source datasets
│   ├── 18_Make_MCMC_Manifest.py           RQ4 job-array manifest
│   ├── 19_MCMCglmm_Array.R                RQ4 MCMC (4 variants x 3 colours x 3 chains)
│   ├── 20_Combine_Label_Results.R         RQ4 combine + concordance
│   ├── 21_Predict_Colour_from_Env.py      prediction task (genus-grouped CV)
│   ├── 22_Build_Method_Figures.py         fig7–fig13
│   ├── 23_Build_Prediction_Figure.py      fig14
│   ├── run_11_*.slurm / run_15_rag.slurm / run_19_array.slurm   cluster jobs
│   └── legacy/                    superseded scripts, kept for provenance
│       └── exploratory/           evaluated, not adopted (re-OCR pilot, genus-fix heuristic)
│
├── Processed Data/               pipeline outputs (gitignored, 3.6 GB)
│   ├── figures/                  canonical fig1–fig6 output (07_Generate_Figures.R)
│   ├── step06_outputs_clean/     MCMCglmm models + tables
│   ├── step08_outputs_clean/     elevation gradient outputs
│   ├── step0*_outputs/           superseded pre-clean stage outputs (see legacy/)
│   └── experiments/
│       ├── species_descriptions_treatments.csv   3,857 unique treatments (01c)
│       ├── clean_species_only.csv                species-level colour labels (03_04)
│       ├── step05b_outputs_clean/        env-linked data + PCA (05b)
│       ├── gold_set_labeled.csv          98 labelled items (09)
│       ├── benchmark/                    RQ1 predictions + summary
│       ├── rq2_outputs/                  RQ2 taxonomy
│       ├── rq3_outputs/                  RQ3 RAG + intervention scores
│       ├── wp4_label_variants/results/   RQ4 fixed effects
│       ├── prediction_outputs/           prediction task results
│       └── figures/                      canonical fig7–fig14 output
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
# Ecology figures (fig1-fig6) + Results/ symlinks
module load R/4.5.1-gfbf-2025a
Rscript scripts/07_Generate_Figures.R

# Method-depth figures fig7-fig13 (needs the local venv)
python -m venv .venv_figs && .venv_figs/bin/pip install matplotlib numpy pandas scikit-learn
.venv_figs/bin/python scripts/22_Build_Method_Figures.py

# Prediction task + its figure (fig14)
.venv_figs/bin/python scripts/21_Predict_Colour_from_Env.py
.venv_figs/bin/python scripts/23_Build_Prediction_Figure.py
```

GPU extraction and MCMC runs are submitted with `sbatch` from `scripts/*.slurm`.
Login nodes are for submission only.
