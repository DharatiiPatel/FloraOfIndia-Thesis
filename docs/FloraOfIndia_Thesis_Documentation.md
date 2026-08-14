# Flora of India Thesis — Complete Project Documentation

**Student:** Dharati Patel | Student ID: 811171038  
**Degree:** Masters in Computer Science  
**Thesis Title:** Flower Colour Extraction from Flora of India Using Large Language Models  
**First Draft Deadline:** June 29, 2026  
**University:** University of Georgia  
**Cluster:** Sapelo2 (GACRC)

---

## Table of Contents

1. [What This Thesis Is About](#1-what-this-thesis-is-about)
2. [The Original Paper This Thesis Replicates](#2-the-original-paper-this-thesis-replicates)
3. [Background — Key Concepts](#3-background--key-concepts)
4. [Data Sources Used](#4-data-sources-used)
5. [Complete Pipeline — Step by Step](#5-complete-pipeline--step-by-step)
6. [Results](#6-results)
7. [Dataset Statistics](#7-dataset-statistics)
8. [Comparison with Original Paper](#8-comparison-with-original-paper)
9. [Known Limitations](#9-known-limitations)
10. [File Structure on Sapelo](#10-file-structure-on-sapelo)
11. [Scripts Summary](#11-scripts-summary)
12. [What Has Been Done So Far](#12-what-has-been-done-so-far)
13. [What Needs to Be Done Next](#13-what-needs-to-be-done-next)
14. [Key Numbers to Remember](#14-key-numbers-to-remember)
15. [Technical Setup](#15-technical-setup)

---

## 1. What This Thesis Is About

### The Problem

Plant trait databases — like the TRY Plant Trait Database — are essential for understanding ecological and evolutionary patterns across thousands of plant species. However, these databases are heavily biased toward plants from **Europe and North America**. Indian flora, despite being incredibly diverse, is severely underrepresented.

The **Flora of India** is a multi-volume scientific publication by the Botanical Survey of India (BSI) that documents all plant species found in India. It contains detailed descriptions of each species including flower colour — but this information is written in **natural language prose**, not structured data. Nobody has extracted this information into a machine-readable database before.

### The Solution

This thesis builds an **automated pipeline** that:
1. Scrapes Flora of India PDFs from the BSI website
2. Extracts text from the PDFs
3. Uses a **Large Language Model (LLM)** to extract flower colour information from species descriptions
4. Categorizes colours into standard groups
5. Links species to their geographic occurrence records from GBIF
6. Attaches environmental data (climate + soil) to each species
7. Runs statistical analysis to find relationships between flower colour and environment

### The Goal

To demonstrate that:
- LLMs can automate the extraction of structured trait data from unstructured botanical text
- Indian flower colour data can be extracted at scale for the first time
- Flower colour in Indian flora shows statistically significant associations with environmental variables

---

## 2. The Original Paper This Thesis Replicates

**Title:** Expanding plant trait databases using large language model: A case study on flower color extraction  
**Authors:** Masaru Bamba & Shusei Sato  
**Published:** bioRxiv, February 2025  
**DOI:** https://doi.org/10.1101/2025.02.11.637746  
**GitHub:** https://github.com/mbamba2093/Flower-Color-Habitat-Environment-Association

### What the Original Paper Did

- Used **Flora of China** (born-digital text from eFloras.org) instead of Flora of India
- Used **ChatGPT-4o** to extract flower colour from species descriptions
- Integrated extracted data with TRY Plant Trait Database
- Linked species to GBIF occurrence records
- Added WorldClim climate data and SoilGrids soil data
- Ran **MCMCglmm** Bayesian statistical analysis
- Found that white, yellow, and red-type flowers occupy distinct environmental niches

### What This Thesis Does Differently

| Aspect | Original Paper | This Thesis |
|--------|---------------|-------------|
| Flora source | Flora of China (born-digital) | Flora of India (scanned PDFs) |
| LLM used | ChatGPT-4o (paid API) | Qwen2.5-7B-Instruct (free, open source) |
| Geographic focus | China | India |
| TRY integration | Yes | No (future work) |
| Novel extension | None | Regional/elevation analysis (planned) |

---

## 3. Background — Key Concepts

### What is a Plant Trait?
A trait is any measurable characteristic of an organism. Flower colour is a **morphological trait** — it is visible and categorizable. It is one of the most studied plant traits because it varies enormously and affects pollinator attraction.

### What is the TRY Database?
The world's largest plant trait database. Contains 15 million trait records for 305,594 plant taxa. Started in 2007. Flower colour has TraitID = 207. Problem: biased toward European and American species.

### What is GBIF?
**Global Biodiversity Information Facility** — a database of where species have been found worldwide. Contains ~3 billion occurrence records with latitude/longitude. Used to find where each species lives so we can extract environmental conditions.

### What is Flora of India?
A multi-volume scientific publication by the Botanical Survey of India documenting all plant species in India. Written in natural language. Available as PDFs. 25+ volumes exist — this thesis processed 8 volumes.

### What is an LLM?
**Large Language Model** — an AI trained on billions of text documents to understand and generate language. Examples: GPT-4, LLaMA, Qwen. This thesis used **Qwen2.5-7B-Instruct** — a 7 billion parameter open-source model by Alibaba, free to download and run on a GPU cluster.

### What is OCR?
**Optical Character Recognition** — converting scanned images of text into digital text. Flora of India PDFs are scanned documents, so OCR introduces errors like abbreviated genus names (`A. tetrasepala` instead of `Anemone tetrasepala`) and garbled text.

### What is WorldClim?
A global dataset of climate variables at 10km resolution. Provides 19 bioclimatic variables (Bio1-Bio19) like annual mean temperature, annual precipitation, temperature seasonality etc. Used to characterize the climate where each species lives.

### What is SoilGrids?
A global dataset of soil properties at 250m resolution. Provides 11 soil variables like soil pH, nitrogen content, organic carbon, clay fraction etc. Used to characterize the soil conditions where each species lives.

### What is PCA?
**Principal Component Analysis** — a technique to compress many correlated variables into fewer uncorrelated ones. You had 31 environmental variables (Bio1-19 + elevation + 11 soil). PCA compressed these into 10 principal components (PC1-PC10) that together explain ~82% of environmental variation. This removes multicollinearity and makes statistical modelling more stable.

### What is MCMCglmm?
**Markov Chain Monte Carlo Generalised Linear Mixed Model** — a Bayesian statistical model. Used to test whether environmental PC axes predict flower colour (white, yellow, or redtype), while accounting for the fact that closely related species (same genus) are more similar to each other. Runs 1,050,000 iterations to estimate the posterior probability distribution of each coefficient.

---

## 4. Data Sources Used

| Source | What It Provides | How Accessed |
|--------|-----------------|--------------|
| BSI Website (bsi.gov.in) | Flora of India PDFs | Web scraping (requests + BeautifulSoup) |
| Flora of India PDFs | Species descriptions with flower colour | pdfminer text extraction |
| Qwen2.5-7B-Instruct | LLM for colour extraction | HuggingFace, run on Sapelo GPU |
| GBIF | Species occurrence records (lat/lon) | rgbif R package |
| WorldClim | Climate variables Bio1-Bio19 + elevation | geodata R package |
| SoilGrids | Soil variables (11 variables) | geodata R package |

---

## 5. Complete Pipeline — Step by Step

### Step 01a — Web Scraping
**Script:** `01a_Scraping_FloraOfIndia.py`  
**What it does:** Visits the BSI website and finds the download links for each Flora of India volume PDF  
**Input:** BSI website URL  
**Output:** `flora_of_india_volumes.csv` — list of volume titles and PDF download URLs  
**Key libraries:** `requests` (HTTP calls), `BeautifulSoup` (HTML parsing), `csv`

### Step 01b — PDF Text Extraction
**Script:** `01b_Extract_text_from_pdfs.py`  
**What it does:** Downloads each PDF and extracts the text using pdfminer  
**Input:** PDF files for 8 volumes  
**Output:** `FLORA OF INDIA VOL.1.txt` through `VOL.23.txt`  
**Key library:** `pdfminer.high_level.extract_text`  
**Important:** Since these are scanned PDFs, the extracted text has OCR errors

### Step 01c — Species Block Parsing
**Script:** `01c_Parsing_to_species.py`  
**What it does:** Reads each volume's text file and splits it into individual species blocks using regex pattern matching. Each numbered heading like `"15. Anemone tetrasepala Royle"` marks the start of a new species entry.  
**Input:** VOL*.txt files  
**Output:** `flora_of_india_species_descriptions.csv`  
**Key regex:** `\n\s*(\d+)\.\s+([A-Z][^\n]+)` — matches lines starting with a number followed by a capitalized name  
**Result:** 7,220 species/genera blocks extracted (verified from Qwen log: `DONE. Processed 7220 species.`)

### Step 02 — Flower Colour Extraction (LLM)
**Script:** `02_Extract_flower_color_qwen_gpu.py`  
**What it does:** For each species description, sends it to Qwen2.5-7B-Instruct with a carefully designed prompt asking it to extract the flower colour phrase  
**Input:** `flora_of_india_species_descriptions.csv`  
**Output:** `flora_of_india_flower_color_qwen.csv`  
**Model:** Qwen/Qwen2.5-7B-Instruct (7 billion parameters)  
**Run on:** Sapelo GPU cluster (SLURM job with `--partition=gpu_p`)  
**Prompt strategy:**
- System message: "You are an expert botanist. Extract flower colour only."
- Returns phrases like "flowers white", "flowers yellow with red centre"
- Returns "no flower colour mentioned" when no colour found
- Temperature = 0.0 (deterministic, reproducible)

### Step 03 — Colour Categorization
**Script:** `03_Categorize_Flower_color.py`  
**What it does:** Converts free-text colour phrases into standardized categories  
**Input:** `flora_of_india_flower_color_qwen.csv`  
**Output:** `flora_of_india_flower_color_categories.csv`  

**Categorization rules (in order of priority):**

| Category | Keywords |
|----------|----------|
| WHITE | white, whitish |
| YELLOW | yellow, golden, pale yellow, bright yellow |
| PINK | pink, pinkish |
| RED | red |
| PURPLE/BLUE | purple, purplish, violet, blue |
| GREENISH | greenish |
| UNKNOWN | no flower colour mentioned, or empty |
| OTHER | anything else |

### Step 04 — Data Preprocessing
**Script:** `04_Data_PreProcessing.R`  
**What it does:** Cleans and filters the categorized data  
**Input:** `flora_of_india_flower_color_categories.csv`  
**Output:** Multiple files in `step04_outputs/`  
**Key operations:**
- Strips leading numbers from species names (`"15. Anemone"` → `"Anemone"`)
- Extracts genus and epithet from species names
- Filters to **species-level only** (epithet starts with lowercase letter — e.g., `tetrasepala`)
- Removes genus-level entries (e.g., `Mangifera L.`) and junk rows
- Generates summary statistics and bar plots  
**Result:** 5,796 species-level records

### Step 05a — GBIF Occurrence Fetching
**Script:** `05a_GBIF_seed_cache.R`  
**What it does:** For each species with known flower colour, fetches occurrence records from GBIF  
**Input:** `flora_india_color_clean_species_only.csv`  
**Output:** `gbif_occurrences_all.csv`  
**Key features:**
- Filters to the 5 named colour categories (WHITE, YELLOW, RED, PINK, PURPLE/BLUE) — drops UNKNOWN, OTHER, GREENISH → 1,881 species-level entries
- After deduplicating identical binomials across volumes → 1,849 unique species sent to GBIF
- Groups: PINK + RED + PURPLE/BLUE → **REDTYPE** (matching original paper)
- Fetches up to 10,000 occurrences per species
- **Checkpointing:** saves each species separately so job can resume if interrupted
- Removes records with geospatial issues
- Deduplicates near-identical points within a species at ~1 km resolution (round to 2 decimals)
- Keeps only species with ≥6 records after dedup
- Run as SLURM batch job (8 hour limit)  
**Result:** 1,376,616 occurrence records combined across 1,185 species (408 species failed GBIF matching, mostly due to abbreviated genera and synonymy)

### Step 05b — Environmental Data Linking
**Script:** `05b_EnvironmentData_Link.R`  
**What it does:** Downloads climate and soil data, extracts environmental values at each occurrence point, calculates species-level summaries, runs PCA  
**Input:** `gbif_occurrences_all.csv`  
**Output:** `species_color_environment_final.csv`, `pca_loadings.csv`, `species_pca_scores.csv`  
**Key operations:**
1. Downloads WorldClim Bio1-19 + elevation at 10-arcmin resolution
2. Attempts to download 11 SoilGrids variables; **`ocs` (organic carbon stock) failed** — geodata only exposes it for depth=30, not the requested depth=5. The other 10 succeed (bdod, cec, nitrogen, phh2o, soc, ocd, clay, silt, sand, cfvo)
3. Extracts environmental values at each of 1,376,616 GPS points using `terra`
4. Removes duplicate grid cells per species at ~10 km resolution (round lat/lon to 1 decimal) → 815,554 unique species×cell records
5. Calculates **20% trimmed mean** per species per variable
6. Runs PCA on **30 variables** (19 bio + 1 alt + 10 soil) → PC1-PC10
7. Creates binary columns: `is_white`, `is_yellow`, `is_redtype`
8. Run as SLURM batch job (6 hour limit, 32GB RAM)  
**Result:** 1,174 species with complete environmental + colour data

**PCA variance explained (verified from log):**

| PC | Variance |
|----|---------|
| PC1 | 45.7% |
| PC2 | 22.0% |
| PC3 | 9.8% |
| PC4 | 5.8% |
| PC5 | 4.3% |
| PC6 | 3.2% |
| PC7 | 2.4% |
| PC8 | 1.8% |
| PC9 | 1.0% |
| PC10 | 0.8% |
| **Total PC1–PC10** | **96.8%** |

### Step 06 — MCMCglmm Statistical Analysis
**Script:** `06_MCMCglmm.R`  
**What it does:** Fits Bayesian hierarchical threshold models to test flower colour ~ environment relationships  
**Input:** `species_color_environment_final.csv`  
**Output:** `all_fixed_effects_combined.csv`, `gelman_rubin_*.csv`, `model_*.rds`, trace plots  
**Model details:**
- **Response variables:** `is_white`, `is_yellow`, `is_redtype` (binary 0/1)
- **Fixed effects:** PC1 + PC2 + ... + PC10
- **Random effect:** genus (accounts for evolutionary relatedness)
- **Family:** threshold (appropriate for binary outcomes)
- **Iterations:** 1,050,000 total, 50,000 burn-in, thin=100 → 10,000 effective samples
- **3 chains** run for Gelman-Rubin convergence diagnostics
- Also runs single-variable models for individual environmental variables
- Run as SLURM batch job (24 hour limit, 64GB RAM)  
**Result:** 4 significant associations found, all models converged (MPSRF ~1.000)

### Step 07 — Figure Generation
**Script:** `07_Generate_Figures.R`  
**What it does:** Generates publication-quality figures  
**Output:** 4 PNG figures in `Processed Data/figures/`

| Figure | Content |
|--------|---------|
| `fig1_colour_counts.png` | Bar chart of species per colour category |
| `fig2_mcmc_coefficients.png` | Coefficient plot for PC1-PC10 for all three colours |
| `fig3_pca_loadings.png` | PCA factor loadings heatmap (PC1-PC3) |
| `fig4_convergence.png` | Gelman-Rubin convergence diagnostics |

---

## 6. Results

### Significant Findings from MCMCglmm

| Colour | PC Axis | Direction | pMCMC | Interpretation |
|--------|---------|-----------|-------|----------------|
| WHITE | PC2 | **Positive** | **0.0006** | White flowers more common in nutrient-rich, high soil carbon environments |
| YELLOW | PC2 | **Negative** | **0.0018** | Yellow flowers more common in nutrient-poor, low carbon environments |
| YELLOW | PC4 | **Positive** | **0.039** | Yellow flowers more common in sandier, less silty soils |
| REDTYPE | PC7 | **Negative** | **0.0496** | Red/pink/purple flowers avoid high cation exchange capacity, clay-rich environments |

### What PC2 Represents (Most Important Finding)
From `pca_loadings.csv` (verified):

**Strong positive loadings on PC2:**
- ocd (+0.357) — organic carbon density
- soc (+0.323) — soil organic carbon
- nitrogen (+0.296)
- bio17 (+0.285) — precipitation of driest quarter
- bio14 (+0.279) — precipitation of driest month

**Strong negative loadings on PC2:**
- bdod (−0.319) — soil bulk density
- bio2 (−0.289) — mean diurnal temperature range
- phh2o (−0.274) — soil pH (lower pH = more acidic)
- bio15 (−0.225) — precipitation seasonality

So PC2 represents a **fertile-wet-acidic forest-soil axis**:
- **High PC2** = high organic carbon, high nitrogen, low bulk density (loose, organic-rich), acidic, with reliable rainfall in the dry season → typical of moist evergreen forest soils
- **Low PC2** = compacted soils (high bulk density), more alkaline, larger temperature swings, more seasonal precipitation → typical of arid / scrub / open habitat

**WHITE flowers prefer high PC2** (β = +0.073, pMCMC = 0.0006) — common in moist, fertile, forested settings  
**YELLOW flowers prefer low PC2** (β = −0.077, pMCMC = 0.0018) — common in open, drier, more compacted soils where carotenoid signalling against UV/oxidative stress is favoured

### Convergence Diagnostics

| Model | MPSRF | Status |
|-------|-------|--------|
| WHITE | ~1.000 | ✅ Converged |
| YELLOW | ~1.000 | ✅ Converged |
| REDTYPE | 1.000321 | ✅ Converged |

All models converged excellently (MPSRF well below threshold of 1.1).

---

## 7. Dataset Statistics (verified against actual files)

| Stage | Count |
|-------|-------|
| Total blocks parsed from 8 volumes | 7,220 |
| Species-level entries (after step 04) | 5,796 |
| With known flower colour | 1,928 (33.3% of species-level, 26.7% of all blocks) |
| WHITE | 805 |
| YELLOW | 644 |
| PINK | 155 |
| PURPLE/BLUE | 145 |
| RED | 132 |
| GREENISH | 1 |
| OTHER | 46 |
| UNKNOWN | 3,868 |
| Unique binomials sent to GBIF | 1,849 |
| Failed GBIF matching | 408 |
| GBIF occurrence records (after ~1km dedup) | 1,376,616 |
| Records after 10km dedup (used for env extraction) | 815,554 |
| Species with ≥6 records | 1,185 |
| Final analysis dataset | 1,174 |
| WHITE (final) | 506 |
| YELLOW (final) | 424 |
| REDTYPE = PINK + PURPLE/BLUE + RED (final) | 244 (85 + 81 + 78) |

---

## 8. Comparison with Original Paper

| Metric | Original (Flora of China) | This Thesis (Flora of India) |
|--------|--------------------------|------------------------------|
| Volumes processed | 22 | 8 |
| Species parsed | 37,723 | 7,220 |
| Colour yield (over all parsed blocks) | 46.6% | 26.7% |
| Colour yield (over species-level only) | not reported | 33.3% |
| LLM used | GPT-4o | Qwen2.5-7B |
| Final dataset | 7,938 species | 1,174 species |
| Phylogenetic correction | Full TimeTree phylogeny | Genus random effect |
| Convergence | MPSRF ~1.000 | MPSRF ~1.000 ✅ |
| Source format | Born-digital HTML | Scanned PDFs |

---

## 9. Known Limitations

### 1. Abbreviated Genera (Most Important)
- **32.3% of species-level entries (1,870 of 5,796)** have abbreviated genus names like `A. tetrasepala` instead of `Anemone tetrasepala`
- Caused by OCR of scanned PDFs (the BSI typeset uses an abbreviated genus after the first occurrence in a section, and OCR loses the section context)
- These cannot be matched to GBIF — directly reduces dataset size
- A "fixed parser" that carries forward the most recent fully-spelled genus has NOT yet been written. (Earlier draft of this doc claimed `01c_Parsing_to_species_fixed.py` exists — it does not. Listed as a TODO.)

### 2. Only 8 of 25+ Volumes
- Not all volumes are available as downloadable PDFs from BSI
- Many plant families not represented

### 3. Qwen vs GPT-4o
- Qwen2.5-7B is less capable than GPT-4o
- May have lower colour extraction accuracy
- LLaMA-3 access was pending at time of this work

### 4. Genus Instead of Phylogeny
- Full phylogenetic tree would give more rigorous statistical control
- Genus random effect is a cruder approximation

### 5. No Pollinator Data
- Cannot distinguish environmental vs pollinator-mediated selection
- Planned as novel extension

---

## 10. File Structure on Sapelo

```
/scratch/dp23301/Thesis/
├── raw_data/                          # Flora of India PDF and TXT files
├── logs/                              # SLURM job output and error logs
├── Results/                           # Thesis-ready copies (sync via step 09)
│   ├── README.md
│   ├── figures/
│   │   ├── main/                      # fig1–fig5, MCMC coefficients
│   │   ├── supplementary/             # Trace plots, diagnostics
│   │   └── elevation/                 # fig6_* (after step 08 completes)
│   └── tables/
│       ├── mcmc/                      # Fixed effects, convergence, significant results
│       ├── elevation/                 # Elevation band summaries
│       └── descriptive/               # Colour counts, PCA loadings
├── scripts/                           # All pipeline scripts
│   ├── 01a_Scraping_FloraOfIndia.py
│   ├── 01b_Extract_text_from_pdfs.py
│   ├── 01c_Parsing_to_species.py
│   ├── 02_Extract_flower_color_description.py  # legacy (pre-Qwen) — superseded
│   ├── 02_Extract_flower_color_qwen_gpu.py
│   ├── 03_Categorize_Flower_color.py
│   ├── 04_Data_PreProcessing.R
│   ├── 05a_GBIF_seed_cache.R
│   ├── 05b_EnvironmentData_Link.R
│   ├── 06_MCMCglmm.R
│   ├── 06b_SingleVariable_MCMCglmm.R
│   ├── 07_Generate_Figures.R
│   ├── 08_ElevationGradient_Analysis.R
│   └── slurm/                         # SLURM / job wrappers (sbatch from repo root)
│       ├── run_05a.sh
│       ├── run_05b.sh
│       ├── run_06.sh
│       ├── run_06b.sh
│       ├── run_07.sh
│       ├── run_07_after_06b.sh
│       ├── run_08.sh
│       └── …
│   # NOTE: 01c_Parsing_to_species_fixed.py does NOT exist yet — TODO
└── Processed Data/
    ├── flora_of_india_species_descriptions.csv
    ├── flora_of_india_flower_color_qwen.csv
    ├── flora_of_india_flower_color_categories.csv
    ├── figures/                        # Step 07 final figures
    │   ├── fig1_colour_counts.png
    │   ├── fig2_mcmc_coefficients.png
    │   ├── fig2_supp_PC6_10.png
│   ├── fig2b_mcmc_env_variables.png   # after step 06b completes
│   ├── fig3_pca_loadings.png
│   ├── fig4_convergence.png
│   ├── fig5_pipeline_summary.png
│   └── figS_traceplots.png
│   # fig6_* live in step08_outputs/figures/ (linked via Results/)
    ├── step04_outputs/
    │   ├── flora_india_color_clean_all.csv
    │   ├── flora_india_color_clean_species_only.csv
    │   ├── summary_color_category.csv
    │   └── fig_color_category_counts.png
    ├── step05_env_data/
    │   ├── climate/wc2.1_10m/         # WorldClim rasters
    │   ├── elevation/                  # Elevation rasters
    │   └── soil_world/                 # SoilGrids rasters
    ├── step05_gbif_cache/              # Per-species GBIF CSV cache files
    ├── step05_outputs/
    │   ├── gbif_occurrences_all.csv
    │   ├── gbif_failed_species.txt
    │   ├── species_environment_trimmed.csv
    │   ├── species_pca_scores.csv
    │   ├── pca_loadings.csv
    │   └── species_color_environment_final.csv
    ├── step06_outputs/                 # MCMCglmm (see README.md inside)
    │   ├── README.md
    │   ├── tables/
    │   │   ├── combined/
    │   │   │   ├── all_fixed_effects_combined.csv
    │   │   │   └── single_variable_models.csv
    │   │   ├── fixed_effects/
    │   │   ├── convergence/
    │   │   └── random_effects/
    │   ├── models/
    │   │   ├── model_WHITE.rds
    │   │   ├── model_YELLOW.rds
    │   │   └── model_REDTYPE.rds
    │   └── figures/
    │       ├── trace_WHITE.png
    │       ├── trace_YELLOW.png
    │       ├── trace_REDTYPE.png
    │       └── coefficient_plot_PC1_PC3.png
    └── step08_outputs/                 # Elevation gradient novel analysis
        ├── figures/
        ├── elevation_band_summary.csv
        └── elevation_mcmc_results.csv
```

---

## 11. Scripts Summary

| Script | Language | Purpose | Run Where |
|--------|----------|---------|-----------|
| `01a_Scraping_FloraOfIndia.py` | Python | Scrape BSI website for PDF links | Login node |
| `01b_Extract_text_from_pdfs.py` | Python | Extract text from PDFs | Login node |
| `01c_Parsing_to_species.py` | Python | Parse species blocks | Login node |
| `02_Extract_flower_color_description.py` | Python | Legacy LLM extractor (pre-Qwen, superseded) — **not used in final pipeline** | Login node |
| `02_Extract_flower_color_qwen_gpu.py` | Python | Final LLM colour extraction (Qwen2.5-7B) | GPU node (SLURM) |
| `03_Categorize_Flower_color.py` | Python | Categorize colour phrases | Login node |
| `04_Data_PreProcessing.R` | R | Clean and filter data | Login node |
| `05a_GBIF_seed_cache.R` | R | Fetch GBIF occurrences | Batch node (SLURM) |
| `05b_EnvironmentData_Link.R` | R | Link environmental data + PCA | Batch node (SLURM) |
| `06_MCMCglmm.R` | R | Bayesian MCMCglmm (colour ~ PC1–PC10) | Batch node (SLURM) |
| `06b_SingleVariable_MCMCglmm.R` | R | Single-environment-variable MCMC models | Batch node (SLURM array) |
| `07_Generate_Figures.R` | R | Generate publication figures | Batch node (SLURM) |
| `08_ElevationGradient_Analysis.R` | R | Elevation gradient novel analysis | Batch node (SLURM) |

### R Packages Used

| Package | Purpose |
|---------|---------|
| `rgbif` | GBIF API access |
| `dplyr` | Data manipulation |
| `terra` | Raster spatial data handling |
| `geodata` | Download WorldClim and SoilGrids |
| `MCMCglmm` | Bayesian mixed models |
| `ape` | Phylogenetics |
| `coda` | MCMC diagnostics |

### Python Libraries Used

| Library | Purpose |
|---------|---------|
| `requests` | HTTP requests for web scraping |
| `beautifulsoup4` | HTML parsing |
| `pdfminer` | PDF text extraction |
| `transformers` | Load and run Qwen LLM |
| `torch` | GPU computation |

---

## 12. What Has Been Done So Far

✅ **Step 01a** — Web scraping of BSI website complete  
✅ **Step 01b** — PDF text extraction complete  
✅ **Step 01c** — Species parsing complete → 7,220 blocks  
✅ **Step 02** — Qwen LLM flower colour extraction complete → 1,928 with colour  
✅ **Step 03** — Colour categorization complete  
✅ **Step 04** — Data preprocessing complete → 5,796 species-level records  
✅ **Step 05a** — GBIF occurrence fetching complete → 1,376,616 records  
✅ **Step 05b** — Environmental data linking + PCA complete → 1,174 species, 30 env variables, PC1–10 explain 96.8%  
✅ **Step 06** — MCMCglmm analysis complete → 4 significant findings, all converged (max MPSRF = 1.0007)  
✅ **Step 07** — Figure generation complete → 4 publication figures  
⬜ **Fixed parser** — `01c_Parsing_to_species_fixed.py` is a TODO, not yet written  
✅ **Progress report written** — Updated May 2026  
✅ **GitHub repository** — https://github.com/DharatiiPatel/FloraOfIndia-Thesis  

---

## 13. What Needs to Be Done Next

### Immediate (Before Writing)

- [ ] **Review all 4 figures** — check they look correct and publication-quality
- [ ] **Review MCMCglmm results** — understand what each significant finding means
- [ ] **Review PCA loadings** — understand what PC2, PC4, PC7 represent environmentally

### Novel Analysis (Choose One or Two)

The replication of the original paper is complete. A novel contribution needs to be added:

**Option 1 — Elevation Analysis** *(Easiest — 1 day)*
- Use elevation (alt) already in your dataset
- Ask: Do flower colours shift with altitude in India?
- India has extreme elevation gradients (sea level to Himalayas)
- This is India-specific and genuinely novel

**Option 2 — Regional Analysis** *(Strongest — 2 days)*
- Split species by biogeographic zone using GBIF coordinates
- Himalayan vs Peninsular India vs Andaman islands
- Ask: Do colour-environment relationships differ across Indian regions?
- Very novel — original paper had no regional breakdown

**Option 3 — Monsoon Climate Analysis** *(Easy — 1 day)*
- Use Bio16 (wettest quarter) and Bio17 (driest quarter) already in dataset
- India has unique monsoon seasonality
- Ask: Does monsoon precipitation predict flower colour?

**Option 4 — Colour Co-occurrence** *(Easy — 1 day)*
- Analyse which colour combinations occur together
- Do co-occurring colours share similar environments?

### Thesis Writing (June 29 Deadline)

Write in this order:

1. **Methods** — easiest to write, just describe what you did step by step
2. **Results** — present your figures and significant findings
3. **Discussion** — interpret results, compare to original paper
4. **Introduction** — write last, you will know exactly what you need to introduce
5. **Abstract** — write very last, summarizes everything
6. **Limitations** — already documented above

### Thesis Structure

```
Abstract
1. Introduction
   1.1 Plant trait databases and their limitations
   1.2 Large Language Models for scientific text extraction
   1.3 Flower colour ecology and evolution
   1.4 Gap: Indian flora underrepresented
   1.5 Thesis contributions
2. Related Work
   2.1 TRY database and GBIF
   2.2 LLM for ecological data extraction
   2.3 Flower colour and environment
3. Methodology
   3.1 Data collection (Steps 01a-01c)
   3.2 LLM-based colour extraction (Step 02)
   3.3 Colour categorization (Step 03)
   3.4 Data preprocessing (Step 04)
   3.5 GBIF occurrence data (Step 05a)
   3.6 Environmental data and PCA (Step 05b)
   3.7 Statistical analysis — MCMCglmm (Step 06)
4. Results
   4.1 Dataset statistics
   4.2 Colour distribution
   4.3 PCA results
   4.4 MCMCglmm results
   4.5 Novel analysis results
5. Discussion
   5.1 Interpretation of significant findings
   5.2 Comparison with Flora of China results
   5.3 Implications for Indian flora
6. Limitations and Future Work
7. Conclusion
References
```

### Papers to Cite in Literature Review

| Paper | Why Cite It |
|-------|------------|
| Bamba & Sato (2025) — bioRxiv | Primary reference — the paper you are replicating |
| Kattge et al. (2020) — Global Change Biology | TRY database — cite as main plant trait database |
| Hampton et al. (2013) — Frontiers in Ecology | Big data in ecology — motivation for large databases |
| Gougherty & Clipp (2024) — npj Biodiversity | LLMs for ecological data extraction — 50x faster than humans |
| Domazetoski et al. (2025) — Applications in Plant Sciences | LLMs for plant trait extraction from text |
| Rausher (2008) — Int J Plant Sciences | Flower colour evolution — classic reference |
| Dagdelen et al. (2024) — Nature Communications | Structured information extraction using LLMs |
| Fick & Hijmans (2017) — Int J Climatology | WorldClim — cite as climate data source |
| Poggio et al. (2021) — SOIL | SoilGrids — cite as soil data source |
| Hadfield (2010) — J Statistical Software | MCMCglmm R package |

---

## 14. Key Numbers to Remember

| Number | What It Represents |
|--------|-------------------|
| 7,220 | Total species/genera blocks parsed |
| 5,796 | Species-level entries after preprocessing |
| 1,928 | Species with known flower colour (33.3% of species-level) |
| 1,849 | Unique binomials sent to GBIF (after de-duplicating same species across volumes) |
| 408 | Species that failed GBIF matching |
| 1,376,616 | GBIF occurrence records (after ~1km dedup) |
| 815,554 | Records after 10km dedup (the inputs to per-species trimmed mean) |
| 1,185 | Species with ≥6 GBIF records (after 05a dedup) |
| 1,174 | Final analysis dataset size (after 05b dedup + complete env data) |
| 506 / 424 / 244 | WHITE / YELLOW / REDTYPE in final dataset |
| 30 | Environmental variables (19 bio + 1 alt + 10 soil; `ocs` failed to download) |
| 10 | Principal components used (PC1-PC10) |
| 96.8% | Variance explained by PC1-PC10 |
| 45.7% | Variance explained by PC1 alone |
| 1,050,000 | MCMC iterations per model |
| 10,000 | Effective posterior samples |
| 4 | Significant colour-environment associations |
| 0.0006 | Strongest pMCMC (WHITE ~ PC2) |
| ≤1.0007 | MPSRF convergence values (all models converged) |
| 32.3% | Species with abbreviated genera (key limitation) |
| 1,870 | Species-level entries affected by abbreviated genus problem |
| 8 | Volumes of Flora of India processed (Vol. 1, 2, 3, 4, 5, 12, 13, 23) |

---

## 15. Technical Setup

### Sapelo Cluster (GACRC)
- **Login nodes:** ss-sub1, ss-sub4 (for job submission only — do NOT run heavy scripts here)
- **Compute nodes:** c4-* (batch), ra1-* (various)
- **GPU nodes:** gpu_p partition
- **File system:** `/scratch/dp23301/` (working directory)
- **Job scheduler:** SLURM (`sbatch` to submit, `squeue -u dp23301` to check)

### R Setup on Sapelo
```bash
module load R/4.5.1-gfbf-2025a        # For terra/geodata (needs newer R)
module load R/4.4.1-gfbf-2023b        # For rgbif/MCMCglmm
module load GDAL/3.11.1-foss-2025a    # Required for terra spatial package
```

Personal R library: `~/R/library`  
Always add to scripts: `.libPaths(c("~/R/library", .libPaths()))`

### Python Setup on Sapelo
```bash
module load Python/3.13.5-GCCcore-14.3.0
export HF_HOME=/scratch/dp23301/.cache/huggingface
```

### VS Code Remote Connection
- Connect via Remote-SSH to `sapelo2.gacrc.uga.edu`
- Open folder: `/scratch/dp23301/Thesis`
- PNG figures can be viewed directly by clicking in the explorer panel
- Terminal submits SLURM jobs directly

### GitHub Repository
- URL: https://github.com/DharatiiPatel/FloraOfIndia-Thesis
- Branch: main
- Large files (CSVs, rasters, logs) excluded via `.gitignore`
- Only scripts and documentation committed

---

*Documentation last verified against actual files: May 3, 2026*  
*Internal reference document only — not for thesis submission*
 

