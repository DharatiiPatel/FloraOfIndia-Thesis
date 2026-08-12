# Chapter 3 — Data Sources and Computational Pipeline

> **Draft status:** First draft for thesis writing. Numbers verified against the clean
> (treatment-parser) pipeline unless otherwise noted. Replace placeholder citations
> with your reference manager entries before submission. Sections on LLM evaluation,
> RAG, and sensitivity analysis will be expanded once those experiments are complete;
> this chapter focuses on the end-to-end data pipeline that underpins all subsequent
> analyses.

---

## 3.1 Overview

This chapter describes the data sources and computational pipeline used to convert
unstructured botanical prose from the *Flora of India* into a structured, analysis-ready
trait–environment dataset. The pipeline comprises seven stages: (i) acquisition and
text extraction from scanned floristic volumes; (ii) species-level treatment parsing;
(iii) large-language-model (LLM) extraction of flower colour; (iv) categorical
standardisation of free-text colour phrases; (v) linkage to georeferenced occurrence
records; (vi) environmental characterisation and dimensionality reduction; and
(vii) Bayesian hierarchical modelling of colour–environment associations. Later chapters
evaluate extraction quality (Chapter 4), characterise failure modes (Chapter 5), test
methodological interventions (Chapter 6), and assess whether extraction quality alters
ecological inference (Chapter 7). The present chapter therefore establishes the
empirical substrate shared by all subsequent analyses.

A central design principle is **reproducibility with open tools**. All model inference
is performed with openly available instruction-tuned transformers hosted on the
university high-performance computing cluster; spatial and statistical stages use
standard open-source R packages. The original analytic pipeline is preserved as a
stable baseline, while experimental extensions (improved parsing, multi-model
extraction, and sensitivity analyses) are isolated in a parallel directory so that
methodological innovations can be evaluated without compromising previously reported
results.

---

## 3.2 Data Sources

### 3.2.1 Flora of India

The primary textual corpus is the *Flora of India*, a multi-volume taxonomic treatment
published by the Botanical Survey of India (BSI). Unlike born-digital floras such as
the online *Flora of China*, the volumes used here are distributed primarily as scanned
PDF documents. Eight volumes with downloadable PDFs were retained for analysis
(Volumes 1–5, 12, 13, and 23), spanning a broad set of angiosperm families represented
in the Indian flora.

Each volume comprises species treatments written in formal botanical English. A typical
treatment includes nomenclature, morphological description, phenology, and geographic
distribution. Flower colour, when stated, appears as free text embedded in the
morphological description (e.g., “petals white,” “flowers yellowish with a red blotch”)
rather than as a structured field. This property motivates an information-extraction
approach: the scientific challenge is not the absence of trait information, but its
encoding in unstructured prose.

Text was recovered from PDFs using pdfminer-based extraction. Because the source
documents are scanned, the resulting text inherits optical character recognition (OCR)
artefacts—including abbreviated genera after first mention within a section, occasional
line-break truncations, and rare digit–letter confusions—that affect both parsing and
downstream name matching. These artefacts are treated as an intrinsic property of the
data regime rather than as the primary scientific claim of the thesis; their effects on
extraction quality are quantified in Chapter 5.

### 3.2.2 Global Biodiversity Information Facility (GBIF)

Occurrence records were obtained from the Global Biodiversity Information Facility
(GBIF) using the `rgbif` R interface. For each species with an inferred flower colour,
GBIF was queried for georeferenced occurrences with coordinate information. Records
flagged with geospatial issues were removed, and near-duplicate coordinates within a
species were collapsed at approximately 1 km resolution prior to environmental
extraction. Only species retaining at least six cleaned occurrence records after
spatial filtering were retained for environmental summarisation, following the
threshold used in the Flora of China study that this work extends.

### 3.2.3 Climate and soil layers

Environmental covariates were drawn from two complementary global products. WorldClim
version 2.1 provided nineteen bioclimatic variables (Bio1–Bio19) and elevation at
10-arcminute resolution. SoilGrids supplied surface soil properties (0–5 cm) including
bulk density, cation exchange capacity, nitrogen, pH, organic carbon metrics, and
particle-size fractions. Together these layers characterise the climatic and edaphic
niche occupied by each species’ occurrence set.

---

## 3.3 Species Treatment Parsing

Species treatments were segmented from continuous volume text using a rule-based parser
that identifies numbered taxonomic headings of the form “*N. Genus epithet* …”. An
initial parser recovered a larger set of candidate blocks but also admitted
identification-key stubs, genus-level headers, and duplicated abbreviated entries that
inflated the apparent species count and degraded subsequent GBIF matching.

An improved treatment parser was therefore developed to retain only species-level
treatments with recoverable genus and epithet fields, to recover abbreviated-genus
treatments when supported by descriptive context, and to deduplicate binomials by
preferring the longer (typically more complete) textual block. Applied to the eight
volumes, this procedure yielded **3,857 unique species treatments**, of which **3,230**
contained substantive morphological description text suitable for colour extraction.
All downstream extraction and ecological analyses reported in the clean experimental
pipeline use this treatment-level corpus.

---

## 3.4 LLM-Based Flower Colour Extraction

### 3.4.1 Model and prompt design

Flower colour was extracted with **Qwen2.5-7B-Instruct**, an open-weight
instruction-tuned transformer (approximately 7 billion parameters). Inference was
performed on GPU nodes of the Sapelo2 cluster (Georgia Advanced Computing Resource
Center) under deterministic decoding (greedy search; temperature = 0) to ensure
reproducibility.

The model was prompted as an expert botanical extractor and instructed to return a
short free-text colour phrase (e.g., “flowers white,” “flowers yellow with red centre”)
or the exact string “no flower colour mentioned” when colour was absent. The same
prompt template is retained across all models evaluated in Chapter 4, so that
cross-model differences reflect model capacity rather than prompt variation.

### 3.4.2 Categorical standardisation

Free-text phrases were mapped to a closed set of categories using deterministic keyword
rules applied in priority order: WHITE, YELLOW, PINK, RED, PURPLE/BLUE, GREENISH,
UNKNOWN, and OTHER. For ecological modelling, PINK, RED, and PURPLE/BLUE were
subsequently aggregated into a single **REDTYPE** class, following the grouping used by
Bamba and Sato (2025) and reflecting the practical sample sizes of the finer red–pink–
purple spectrum in the Indian corpus.

Species lacking an extractable colour (UNKNOWN/OTHER/GREENISH) were excluded from
occurrence–environment modelling but remain available for evaluation of extraction
recall and for optional trait-imputation extensions.

---

## 3.5 Occurrence Linkage and Spatial Cleaning

Species with known colour categories were matched to GBIF using scientific binomial
queries via the GBIF name backbone, then occurrence search with coordinate filters.
Under the clean treatment pipeline, **1,674** known-colour candidates were submitted;
**1,184** species retained ≥6 cleaned occurrence records prior to environmental
aggregation. After environmental extraction, grid-cell deduplication, and completeness
filtering (Section 3.6), the final analysis set comprised **1,174** species
(**502** WHITE, **428** YELLOW, **244** REDTYPE).

Relative to an earlier parser that admitted abbreviated and duplicate blocks, the
clean pipeline improved GBIF match rate while yielding a nearly identical final *n*,
indicating that sample-size gains from naïve block inflation were largely illusory:
many surplus records failed taxonomic matching or spatial thresholds. This observation
motivates the sensitivity analyses in Chapter 7, which ask whether *label quality*,
rather than raw *n*, is the more consequential lever for ecological inference.

---

## 3.6 Environmental Characterisation and PCA

For each retained occurrence, environmental values were extracted at the point location
using the `terra` raster stack comprising Bio1–Bio19, elevation, and available
SoilGrids layers (thirty variables after excluding organic carbon stock, which is
unavailable at the requested 0–5 cm depth in the `geodata` interface). To reduce spatial
pseudoreplication within species, occurrences were deduplicated to unique ≈10 km grid
cells (coordinates rounded to one decimal degree). Species retaining fewer than six
cells after this step were removed.

Species-level niche summaries were computed as **20% trimmed means** of each
environmental variable across retained cells, reducing the influence of extreme
outlier localities. The resulting species × environment matrix was standardised and
subjected to principal component analysis (PCA). The first ten principal components
(PC1–PC10) explained approximately **96.8%** of environmental variance
(PC1 ≈ 45.5%, PC2 ≈ 21.9%, PC3 ≈ 9.9% in the clean pipeline), providing an
orthogonal, multicollinearity-reduced predictor set for hierarchical modelling.
Binary indicators `is_white`, `is_yellow`, and `is_redtype` were attached for use as
Bernoulli responses under a threshold formulation.

Interpretation of individual PC axes is deferred to the Results chapters; briefly,
PC2 in this corpus loads strongly on soil organic carbon, nitrogen, and dry-season
precipitation versus bulk density and diurnal temperature range, and is the axis most
consistently associated with WHITE versus YELLOW flower colour in the primary
MCMCglmm analysis.

---

## 3.7 Statistical Modelling of Colour–Environment Associations

Colour–environment relationships were estimated with Bayesian generalised linear mixed
models implemented in the `MCMCglmm` package. For each binary colour indicator, a
threshold (probit-equivalent) model was fitted with PC1–PC10 as fixed effects and a
**genus-level random intercept** to account for phylogenetic non-independence among
congeners. Residual variance was fixed at unity, as is conventional for binary
threshold models in which residual scale is not separately identifiable.

Markov chain Monte Carlo sampling used 1,050,000 iterations, a burn-in of 50,000, and
thinning interval 100, yielding 10,000 retained posterior samples per chain. Convergence
was assessed with the Gelman–Rubin potential scale reduction factor across three
independent chains (target multivariate PSRF ≈ 1.0). Fixed-effect coefficients whose
95% credible intervals exclude zero are treated as significant associations
(equivalently, low two-sided pMCMC).

This modelling stage constitutes the ecological endpoint of the pipeline. Chapters 4–6
focus on the *quality and improvement* of the colour labels that enter this stage;
Chapter 7 re-fits the same model family under alternative label sources to test whether
extraction quality changes which associations are recovered.

---

## 3.8 Computational Environment and Reproducibility

All stages were executed on the Sapelo2 cluster. LLM inference used GPU partitions;
GBIF harvesting, raster extraction, and MCMCglmm fitting used batch CPU partitions
with job-array parallelisation for multi-chain and multi-variant sensitivity runs.
Python stages rely on `transformers`/`torch` for model inference and the Python
standard library for parsing and categorisation. R stages use `rgbif`, `terra`,
`geodata`, `dplyr`, `MCMCglmm`, and `coda`.

Method-depth scripts (numbered 09+) live alongside the main pipeline in `scripts/`
and write to `Processed Data/experiments/`, leaving the original pipeline artefacts
intact as a stable reference. Checkpointed GBIF caches and Hugging Face model
caches on scratch storage enable resumable long-running jobs.

---

## 3.9 Summary of the Analysis-Ready Dataset

Table 3.1 summarises the clean experimental pipeline at successive filters.

| Stage | Count |
|-------|------:|
| Unique species treatments (8 volumes) | 3,857 |
| Treatments with morphological description | 3,230 |
| Species with known colour after LLM + categorisation (GBIF candidates) | 1,674 |
| Species with ≥6 cleaned GBIF occurrences | 1,184 |
| Final species with complete environment + colour (analysis set) | **1,174** |
| WHITE / YELLOW / REDTYPE | 502 / 428 / 244 |
| Environmental variables entering PCA | 30 |
| Principal components used as predictors | 10 |
| Variance explained by PC1–PC10 | ≈96.8% |

This dataset is the shared input to (i) the primary ecological analysis,
(ii) multi-model extraction benchmarks against a human gold set (Chapter 4), and
(iii) label-source sensitivity experiments that reassign colour while holding
environmental scores fixed (Chapter 7).

---

## 3.10 Chapter Summary

This chapter has described an end-to-end pipeline that transforms scanned floristic
prose into a structured trait–environment resource for Indian angiosperms. Relative to
prior work on born-digital Chinese flora, the present setting emphasises open-weight
LLM extraction under OCR-degraded text and a carefully audited species-treatment
parser. The resulting analysis set of 1,174 species supports both ecological inference
and the computer-science questions that organise the remainder of the thesis: how
accurate open models are at trait extraction, where they fail, how failures can be
mitigated, and whether extraction quality changes scientific conclusions.

---

*End of Chapter 3 draft.*
