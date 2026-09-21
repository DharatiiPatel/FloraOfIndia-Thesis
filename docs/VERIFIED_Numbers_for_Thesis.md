# Verified numbers

Locked values from the published outputs. Every quantity below is recomputed by
`scripts/27_Audit_All_Numbers.py`. Use the cited CSV when a table rounds.

---

## 1. Primary analysis set

Source: `Processed Data/experiments/expansion/step05b_outputs/species_color_environment_final_expanded.csv`.
The folder name `expansion/` is a leftover path; this is the published analysis.
Figures under `Results/figures/` are written by `scripts/07_Generate_Figures.R`.

| Quantity | Value |
|---|---:|
| Unique species treatments | 3,857 |
| Treatments with a morphological description | 3,230 |
| Analysis *n* | **1,438** |
| WHITE / YELLOW / REDTYPE | **613 / 494 / 331** |

---

## 2. Earlier clean set (n = 1,174)

Source: `Processed Data/experiments/step05b_outputs_clean/species_color_environment_final_clean.csv`.
Used for the four label-source variants. Not the published ecology figures
and not the prediction task (those use n = 1,438).

The clean-set models were regenerated at full chain length with `ECOLOGY_SET=clean`,
which writes to `step06_outputs_clean/` and `step08_outputs_clean/` and does not
overwrite `Results/`. Minimum effective sample size on the rebuilt PC models is
8,766.

| Quantity | Value |
|---|---:|
| Analysis *n* | 1,174 |
| WHITE / YELLOW / REDTYPE | 502 / 428 / 244 |

### Colour × environmental PCs (genus random effect)

Significant at raw pMCMC < 0.05. Sources:
`step06_outputs_clean/tables/combined/all_fixed_effects_combined.csv` and
`experiments/expansion/step06_outputs/tables/combined/all_fixed_effects_combined.csv`.

| Effect | Clean n = 1,174 | Primary n = 1,438 |
|---|---|---|
| WHITE ~ PC2 | +0.0718, p = 0.0004 | +0.0720, p = 0.0002 |
| YELLOW ~ PC2 | -0.0841, p = 0.0008 | -0.0697, p = 0.0010 |
| REDTYPE ~ PC3 | -0.0603, p = 0.111 | -0.0776, p = 0.0162 |
| All other colour × PC1-PC10 | non-significant | non-significant |

WHITE increases and YELLOW decreases with PC2 on both sets. REDTYPE decreases
with PC3 only on the primary set (raw p = 0.0162; see §3).

### Elevation (genus-controlled MCMCglmm and χ²)

Sources: `step08_outputs_clean/` and `experiments/expansion/step08_outputs/`.

| Test | Clean n = 1,174 | Primary n = 1,438 |
|---|---|---|
| χ² colour × elevation band | X² = 21.96, p = 0.0050 | X² = 31.25, p = 0.00013 |
| WHITE ~ elevation | -0.109, p = 0.058 | -0.123, p = 0.022 |
| YELLOW ~ elevation | +0.036, p = 0.602 | +0.011, p = 0.869 |
| REDTYPE ~ elevation | +0.132, p = 0.060 | +0.174, p = 0.0064 |

On the primary set, colour composition differs across elevation bands; after
genus control, WHITE declines and REDTYPE increases with elevation. YELLOW has
no elevation association. The clean-set elevation slopes for WHITE and REDTYPE
were not significant.

---

## 3. Multiple testing

Each colour × environment analysis is a grid of tests. Benjamini-Hochberg
q-values are recomputed from the published CSVs by `27_Audit_All_Numbers.py`.

| Analysis | Tests | Expected FP at 0.05 | Raw significant | Survives BH q < 0.05 |
|---|---:|---:|---:|---|
| Primary ecology, colour × PC1-PC10 | 30 | 1.5 | 3 | WHITE ~ PC2 (q = 0.006), YELLOW ~ PC2 (q = 0.015) |
| Primary elevation, colour × `alt_scaled` | 3 | 0.15 | 2 | REDTYPE (q = 0.019), WHITE (q = 0.034) |
| Label-source grid (4 sources) | 120 | 6 | 13 | WHITE ~ PC2 and YELLOW ~ PC2, all four sources (q ≤ 0.009) |
| Reliability chapter (pre-specified) | 12 | 0.6 | 4 | all 4 (WHITE / YELLOW × PC2, q ≤ 0.013) |

WHITE ~ PC2 (positive) and YELLOW ~ PC2 (negative) survive BH in every family,
including Bonferroni, and hold under all four label sources and both reliability
subsets.

REDTYPE ~ PC3 on the primary set (p = 0.0162) has q = 0.162 and does not survive
correction over the 30-test grid. The five secondary hits (YELLOW ~ PC4,
WHITE ~ PC9, REDTYPE ~ PC7) have q = 0.36-0.46 against about 6 expected false
positives. Elevation slopes survive BH; only REDTYPE survives Bonferroni
(0.05 / 3 = 0.0167). WHITE ~ elevation at p = 0.0224 is the weaker of the two.

---

## 4. Gold set

| Quantity | Value |
|---|---:|
| Template rows | 100 |
| Human-labelled | **98** |
| Unlabelled (excluded from scoring) | **2** (row 49 genus header `Ginalloa Korth.`; row 100 incomplete `Erigeron uniflorus` stub) |

---

## 5. Benchmark (categoriser v1)

Scored only on rows that have a gold label and a prediction.
Source predictions: `benchmark/gold_pred_*.csv`.
Summary: `benchmark/benchmark_summary.csv`.

| Model | n | Accuracy | Cohen's κ | Macro-F1 | Wrong |
|---|---:|---:|---:|---:|---:|
| Rule baseline | 97 | 0.7629 | 0.6956 | 0.8035 | 23 |
| Qwen2.5-7B | 98 | 0.8776 | 0.8352 | 0.8745 | 12 |
| Qwen2.5-72B | 98 | 0.8776 | 0.8348 | 0.8735 | 12 |
| Llama-3.3-70B | 98 | 0.8571 | 0.8077 | 0.8606 | 14 |

To 3 d.p.: baseline 0.763; Qwen-7B and Qwen-72B 0.878; Llama 0.857.
Under v1 the 72B model does not beat the 7B model.

---

## 6. Error taxonomy (Qwen-7B, categoriser v1)

Twelve disagreements with gold.

| Error class | Count |
|---|---:|
| CATEGORY_PRIORITY | 4 |
| JUNK_NON_SPECIES | 3 |
| MULTI_COLOUR | 2 |
| CONTAMINATION | 1 |
| FALSE_POSITIVE | 1 |
| FALSE_NEGATIVE | 1 |
| **Total** | **12** |

---

## 7. Categoriser v2 and RAG

Same free-text, new class mapping (v2). RAG is Qwen-7B with 3 TF-IDF exemplars,
leave-one-out. Predictions: `gold_pred_qwen7b_rag.csv`.
RAG `uncertain` outputs are scored as UNKNOWN, as in `15_RAG_Extract_Gold.py`.

| Model | Accuracy v1 | Accuracy v2 | Change |
|---|---:|---:|---:|
| Keyword baseline | 0.7629 | 0.7835 | +0.0206 |
| Qwen-7B | 0.8776 | **0.9388** | **+0.0612** |
| Qwen-72B | 0.8776 | 0.9184 | +0.0408 |
| Llama-70B | 0.8571 | 0.9184 | +0.0612 |

| Setup | n | Accuracy | `uncertain` |
|---|---:|---:|---:|
| Zero-shot + v1 | 98 | 0.8776 | 0 |
| Zero-shot + v2 | 98 | 0.9388 | 0 |
| RAG + v1 | 98 | 0.8980 | 5 |
| RAG + v2 | 98 | **0.9490** | 5 |

Best gold-set accuracy is **0.949** (RAG + categoriser v2), with 5 abstentions
out of 100 rows. RAG was run on the gold set only.

---

## 8. Gold-set robustness (junk rows excluded)

Excluding the 9 rows flagged `JUNK_NON_SPECIES` leaves n = 89.

| System | n = 98 v1 | n = 98 v2 | n = 89 v1 | n = 89 v2 |
|---|---:|---:|---:|---:|
| Keyword baseline | 0.7629 | 0.7835 | 0.7727 | 0.7955 |
| Qwen-7B | 0.8776 | 0.9388 | 0.8989 | 0.9438 |
| Qwen-72B | 0.8776 | 0.9184 | 0.8989 | 0.9326 |
| Llama-70B | 0.8571 | 0.9184 | 0.8989 | 0.9438 |
| Qwen-7B RAG | 0.8980 | 0.9490 | 0.8989 | 0.9438 |

On species-only rows under v2, RAG and zero-shot both score 84 / 89 = 0.9438.
Under v1, all three LLMs score 0.8989 once junk is removed.

Of RAG's 5 abstentions, 4 are genuine species rows and 1 is a junk row. All 4
genuine abstentions have gold = UNKNOWN. Zero-shot and RAG differ on 4 of the
89 rows (2 RAG fixes, 2 RAG breaks), so the accuracies tie and McNemar is
uninformative. RAG matches zero-shot accuracy on genuine species text and
abstains on rows that carry no colour information.

---

## 9. Label-source sensitivity

MCMC: 36 / 36 chain files present (4 variants × 3 colours × 3 chains).
Maximum MPSRF < 1.01 (all ≈ 1.000).
WHITE ~ PC2 (+) and YELLOW ~ PC2 (-) are significant for all four label sources.

### Analysis n by label source

| Variant | n |
|---|---:|
| Keyword baseline | 901 |
| Qwen-7B | 1,174 |
| Qwen-72B | 1,166 |
| Llama-70B | 1,169 |

The baseline labels fewer species than the LLMs, so those comparisons mix label
accuracy with sample composition.

### PC2 coefficients

From `wp4_fixed_effects_all_variants.csv` (4 d.p.; use the CSV for full precision).

| Variant | WHITE ~ PC2 mean | pMCMC | YELLOW ~ PC2 mean | pMCMC |
|---|---:|---:|---:|---:|
| Keyword baseline | +0.0950 | 0.0004 | -0.0985 | 0.0005 |
| Qwen-7B | +0.0718 | 0.0003 | -0.0837 | 0.0006 |
| Qwen-72B | +0.0722 | 0.0005 | -0.0842 | 0.0003 |
| Llama-70B | +0.0780 | 0.0003 | -0.0819 | 0.0004 |

### Other effects that reach raw pMCMC < 0.05

Thirty colour × PC effects per variant. Five combinations are significant under
at least one label source.

| Effect | Baseline | Qwen-7B | Qwen-72B | Llama-70B |
|---|---|---|---|---|
| WHITE ~ PC2 | yes | yes | yes | yes |
| YELLOW ~ PC2 | yes | yes | yes | yes |
| YELLOW ~ PC4 | no (0.51) | yes (0.0497) | yes (0.030) | no (0.060) |
| WHITE ~ PC9 | yes (0.036) | no | no | no |
| REDTYPE ~ PC7 | no | no | yes (0.040) | yes (0.030) |

Label source does not flip either PC2 association. It does change three of the
four secondary associations. The label-source grid is 3 colours × 10 PCs × 4 sources =
120 tests, so about 6 hits are expected at pMCMC < 0.05; 13 are observed. Under
BH, only WHITE ~ PC2 and YELLOW ~ PC2 survive (q ≤ 0.009). The five secondary
hits have q = 0.36-0.46 and are consistent with the expected false-positive rate.

---

## 10. Prediction (colour from environment)

Source: `prediction_outputs/prediction_cv_summary.csv`.
Run on the primary n = 1,438 set (417 genera; 613 / 494 / 331).
Figure: `Results/figures/methods/fig14_prediction.{png,pdf}`.
Five-fold CV. Genus-grouped CV is the headline split: a genus never spans a fold,
so the genus prior collapses to the majority class.

| Model | Accuracy | Balanced acc. | Macro-F1 [95% CI] |
|---|---:|---:|---|
| Majority class | 0.4263 | 0.3333 | 0.1993 [0.191, 0.208] |
| Logistic regression | 0.4325 | 0.3595 | 0.3135 [0.292, 0.335] |
| Random forest (best environment model) | 0.4131 | 0.3628 | 0.3500 [0.325, 0.375] |
| Genus prior (grouped CV) | 0.4263 | 0.3333 | 0.1993 [0.191, 0.208] |
| Genus prior, ungrouped CV | 0.6161 | 0.6015 | 0.6077 [0.580, 0.633] |

Environment is associated with colour but weakly predictive: balanced accuracy
0.363 against a 0.333 chance floor. Relatedness lifts macro-F1 2.7× further
above the majority floor than climate and soil (genus prior ungrouped 0.608 vs
random forest 0.350, floor 0.199). Permutation importance: PC2 = +0.0193 is the
only axis with positive importance (next is PC8 at -0.0015).

On the earlier n = 1,174 set the same pattern held: majority 0.200, logistic
0.300, random forest 0.326, genus prior ungrouped 0.605; balanced accuracy
0.342 vs 0.333.

---

## 11. Full-treatment prediction files

| File | Rows |
|---|---:|
| `treatments_pred_baseline.csv` | 3,857 |
| `treatments_pred_qwen72b.csv` | 3,857 |
| `treatments_pred_llama70b.csv` | 3,857 |

Full-corpus Qwen-7B colours are in `flower_color_qwen_clean.csv` from the clean
pipeline.

---

## 12. Reliability chapter

Sources: `Processed Data/experiments/reliability/summary.json`,
`reliability_robustness_table.csv`, `reliability_mcmc_effects.csv`,
`reliability_convergence.csv` (also under `Results/tables/reliability/`).
Built by `scripts/24_Build_Reliability_Set.py` and `scripts/25_Reliability_Ecology.R`
at `nitt = 1,050,000`, 3 independent chains (seeds 42 / 123 / 456), inference on
the pooled 30,000 samples. Appendix figure: fig18.

These are categoriser-v2 labels on the three-model overlap. They are not the
published n = 1,438 pipeline table in §1.

The ecology label is Qwen-7B v2. Qwen-72B and Llama contribute only to coverage
and agreement. The keyword baseline is excluded from consensus. UNKNOWN and
OTHER are dropped and never coded as `is_white = 0`.

| Set | n |
|---|---:|
| Primary ecology | 1,438 |
| Three-LLM coverage (72B + Llama present) | 1,313 |
| Common known support (all 3 give WHITE/YELLOW/REDTYPE) | **1,149** |
| High confidence (all 3 agree on class) | **1,129** |
| Disagreement (descriptive only) | **20** |

Agreement rate on common-known support: 0.9826; on coverage where 7B is known:
0.9733. Validator flags: unsupported known colour 26; wrong-context 11;
high-confidence and supported 1,105.
Colour counts — common: YELLOW 436 / WHITE 394 / REDTYPE 319;
high-confidence: 429 / 389 / 311.

### Robustness (both subsets, genus RE, threshold MCMCglmm)

Pooled posterior over 3 chains.

| Effect | Common-known (n = 1,149) | High-confidence (n = 1,129) |
|---|---|---|
| WHITE ~ PC2 | +0.067, p = 0.004, CI excludes 0 | +0.071, p = 0.003, CI excludes 0 |
| YELLOW ~ PC2 | -0.080, p = 0.001, CI excludes 0 | -0.080, p = 0.001, CI excludes 0 |
| REDTYPE ~ PC3 | -0.020, p = 0.58 | -0.019, p = 0.60 |
| WHITE ~ elevation | -0.034, p = 0.61 | -0.036, p = 0.58 |
| YELLOW ~ elevation | +0.044, p = 0.56 | +0.048, p = 0.53 |
| REDTYPE ~ elevation | +0.008, p = 0.91 | +0.011, p = 0.88 |

WHITE ~ PC2 (+) and YELLOW ~ PC2 (-) keep sign and exclude zero on both subsets.
REDTYPE ~ PC3 and the three elevation slopes keep direction but include zero.
That is robustness to disagreement among these three models, not to all
extraction error: shared OCR or prompt bias can still agree.

### Convergence

| Diagnostic | Value |
|---|---|
| Chains per model (seeds 42 / 123 / 456) | 3 |
| Pooled posterior samples per model | 30,000 |
| Worst Gelman-Rubin MPSRF (12 models) | **1.000425** |
| Worst per-parameter PSRF | 1.000249 |
| Lowest pooled effective sample size | **29,380** of 30,000 |
| Models with MPSRF < 1.01 | **12 / 12** |

All 12 models converged. Worst MPSRF 1.0004 against a 1.01 threshold; effective
sample sizes are within 2% of the nominal 30,000. Moving from one chain to three
shifted posterior means by at most 0.0006 and left every robustness designation
unchanged. Step 06 and the label-source models report the same class of
diagnostic (worst MPSRF 1.00053).

No second-annotator or human inter-annotator study was performed. Reliability
is model agreement plus lexical source grounding. The n = 98 gold set is
exploratory.

