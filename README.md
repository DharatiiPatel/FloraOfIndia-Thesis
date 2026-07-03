# Flora of India — Flower Colour Thesis

**Analysis complete.** Use this layout:

```
Thesis/
├── Results/              ← THESIS WRITING: figures + tables (start here)
├── docs/                 ← Documentation and progress reports
├── scripts/              ← Pipeline code (04–08, run_*.sh)
├── Processed Data/       ← Raw pipeline outputs (by step)
├── raw_data/             ← Flora of India PDFs / extracted text
├── logs/                 ← SLURM .err logs (verbose .out → logs/archive/)
└── R_library/            ← R packages (ggplot2, etc.)
```

## For your thesis document

| Need | Location |
|------|----------|
| Main figures (fig1–fig5, fig2b) | `Results/figures/main/` |
| Supplementary (trace plots) | `Results/figures/supplementary/` |
| Elevation figures (fig6) | `Results/figures/elevation/` |
| MCMC tables | `Results/tables/mcmc/` |
| Elevation tables | `Results/tables/elevation/` |

## Regenerate figures

```bash
module load R/4.5.1-gfbf-2025a
Rscript scripts/07_Generate_Figures.R
```

## Full documentation

See `docs/FloraOfIndia_Thesis_Documentation.md` and `docs/ElevationGradient_NovelResearch.md`.
