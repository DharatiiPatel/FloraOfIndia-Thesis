# Elevation Gradient Analysis — Novel Research Contribution

This document explains **what Step 08 adds** to your thesis beyond replicating Bamba & Sato (2025) on Flora of India.

---

## Why elevation?

| Criterion | Elevation gradient | Pollinator data |
|-----------|-------------------|-----------------|
| Data already in pipeline | ✅ `alt` from WorldClim in step 05b | ❌ New databases needed |
| India-specific story | ✅ Sea level → Himalayas (~8,000 m) | Moderate |
| Time to complete | ~1 day analysis + writing | Weeks |
| Masters thesis fit | ✅ Strong | Better for PhD / future work |

The original China paper did **not** analyse elevation as a dedicated gradient. This is your **novel contribution**.

---

## What we are incorporating (Step 08)

### Script: `scripts/08_ElevationGradient_Analysis.R`
### SLURM: `scripts/run_08.sh` (submit with `sbatch scripts/run_08.sh`)

### Input data (already exists — no new scraping)
- `Processed Data/step05_outputs/species_color_environment_final.csv` — colour flags + PC1–PC10
- `Processed Data/step05_outputs/species_environment_trimmed.csv` — species-level `alt` (metres)

### New outputs → `Processed Data/step08_outputs/`

| File | What it contains |
|------|------------------|
| `species_with_elevation.csv` | Analysis dataset + `alt`, `elev_band`, `alt_scaled` |
| `elevation_band_summary.csv` | Species counts and colour **percentages** per band |
| `elevation_mcmc_results.csv` | Bayesian coefficients: colour ~ elevation |
| `pc2_by_elevation_band.csv` | Mean PC2 per band (links to main WHITE/YELLOW finding) |
| `elevation_chisq_test.txt` | Chi-square test: colour × elevation band |
| `elevation_analysis_summary.txt` | One-page run summary |
| `model_elev_WHITE.rds` etc. | Saved MCMC models |

### New figures → `Processed Data/figures/` (prefix `fig6_`)

| Figure | Thesis section | What it shows |
|--------|----------------|---------------|
| `fig6_elevation_colour_proportions.png` | Results 4.5 | **Stacked %** of WHITE / YELLOW / REDTYPE in each elevation band |
| `fig6_elevation_species_counts.png` | Results 4.5 | Absolute species counts by band × colour |
| `fig6_elevation_density.png` | Results 4.5 | **Density curves** of elevation by colour group |
| `fig6_elevation_mcmc_coefficients.png` | Results 4.5 | **Forest plot**: does elevation predict each colour? (genus-controlled) |
| `fig6_elevation_pc2_boxplot.png` | Results 4.5 | How **PC2** (fertile forest axis) changes with elevation |

---

## Elevation bands (India-relevant)

Species are assigned to bands using **trimmed-mean altitude** at GBIF occurrence points:

| Band | Elevation | Typical habitat (India) |
|------|-----------|-------------------------|
| Lowland | 0–500 m | Plains, coast, Deccan |
| Submontane | 500–1500 m | Foothills, lower Western Ghats |
| Montane | 1500–3000 m | Mid-Himalaya, high Ghats |
| Subalpine | 3000–4500 m | High Himalaya |
| Alpine | >4500 m | Upper alpine (sparse species) |

---

## Three research questions (for your thesis text)

### RQ1 — Descriptive (colour composition vs elevation)
> Do the **proportions** of white, yellow, and red-type flowers change across elevation bands?

- Method: Cross-tabulation + **chi-square test**
- Output: `elevation_band_summary.csv`, proportion bar chart

### RQ2 — Inferential (elevation predicts colour)
> After accounting for shared evolutionary history (genus random effect), is **elevation associated** with each colour group?

- Method: **MCMCglmm** threshold model (same settings as Step 06):
  - `is_white ~ alt_scaled + (1|genus)`
  - `is_yellow ~ alt_scaled + (1|genus)`
  - `is_redtype ~ alt_scaled + (1|genus)`
- Output: `elevation_mcmc_results.csv`, forest plot

### RQ3 — Connection to main finding (PC2 context)
> Does the **PC2 environment axis** (where WHITE is + and YELLOW is −) shift along elevation?

- Method: Boxplot of PC2 by elevation band
- Interpretation: If PC2 increases at mid-elevation moist forests, you can discuss whether elevation **mediates** the colour–environment relationship

---

## How this fits in your thesis structure

```
4. Results
   4.1 Dataset statistics          ← existing
   4.2 Colour distribution         ← fig1
   4.3 PCA results                 ← fig3
   4.4 MCMCglmm results            ← fig2, fig2_supp
   4.5 Elevation gradient analysis ← NEW (fig6_*)
5. Discussion
   5.1 Interpretation of PC2 finding
   5.2 Comparison with Flora of China
   5.3 Elevation patterns in Indian flora  ← NEW paragraph
   5.4 Limitations
```

---

## Suggested thesis wording (Methods snippet)

> *As a novel extension specific to the Indian flora, we analysed flower colour composition along altitudinal gradients. Species-level elevation was derived from WorldClim (Bio-altitude layer) at GBIF occurrence coordinates, aggregated using the same 20% trimmed mean as other environmental variables. Species were classified into five elevation bands reflecting Indian biogeography. We tested whether colour category frequencies differed across bands using Pearson's chi-square test. We further fitted Bayesian threshold models (MCMCglmm, genus random effect, identical MCMC settings to Section 3.7) with scaled elevation as the sole fixed effect for each colour group.*

---

## How to run

```bash
# Submit to batch (do NOT run MCMC on login node)
cd /scratch/dp23301/Thesis
sbatch scripts/run_08.sh

# Monitor
squeue -u dp23301
tail -f logs/elev_grad_*.out
```

**Expected runtime:** ~8–20 hours (3 MCMC models × 1.05M iterations each).

---

## What this does NOT do (scope limits — mention in thesis)

- Does not test **elevation × PC2 interaction** (could be future work)
- Does not replace regional analysis (Himalaya vs peninsula by coordinates)
- Uses genus random effect, not full phylogeny (same as main analysis)
- Elevation is species-level mean — not individual occurrence-level

---

## Relationship to other running jobs

| Job | Purpose | When done |
|-----|---------|-----------|
| `run_06b.sh` (45825091) | Single env-variable MCMC → fig2b | Days |
| `run_08.sh` | **Elevation novel analysis** → fig6_* | ~1 day |
| `run_07_after_06b.sh` | Regenerate fig2b after 06b | After 06b |

Step 08 is **independent** — you can run it now while 06b continues.
