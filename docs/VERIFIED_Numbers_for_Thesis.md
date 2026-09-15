## 1. Primary ecology pipeline (analysis set)

| Quantity | Exact value |

| Unique species treatments | 3,857 |
| Treatments with description | 3,230 |
| Final analysis *n* (**primary / published**) | **1,438** |
| WHITE / YELLOW / REDTYPE | **613 / 494 / 331** |

Source: `Processed Data/experiments/expansion/step05b_outputs/species_color_environment_final_expanded.csv`  
(Internal folder name `experiments/expansion/` is retained for script paths; this is the **primary** analysis output.)  
Figures: `Results/figures/` synced by `scripts/07_Generate_Figures.R`.  
The earlier n=1,174 ecology outputs remain under `Processed Data/experiments/` (not published figures).

### Prior clean set (historical / RQ4 / prediction)

| Quantity | Exact value |
|---|---:|
| Final analysis *n* (earlier clean set) | 1,174 |
| WHITE / YELLOW / REDTYPE | 502 / 428 / 244 |

Source: `Processed Data/experiments/step05b_outputs_clean/species_color_environment_final_clean.csv`  
Used by RQ4 label-sensitivity and the prediction task; **not** the published ecology figure set.

---

## 1b. Ecology: n=1,174 clean vs n=1,438 primary (verified)

### MCMCglmm colour × environmental PCs (genus random effect)

Significant = pMCMC &lt; 0.05. Sources:  
`step06_outputs_clean/tables/combined/all_fixed_effects_combined.csv` vs  
`experiments/expansion/step06_outputs/tables/combined/all_fixed_effects_combined.csv`.

| Effect | Clean n=1,174 | Primary n=1,438 | Change |
|---|---|---|---|
| WHITE ~ PC2 | +0.0718, p=0.0004 ✓ | +0.0720, p=0.0002 ✓ | **Same** (direction + sig) |
| YELLOW ~ PC2 | −0.0841, p=0.0008 ✓ | −0.0697, p=0.0010 ✓ | **Same** (direction + sig; slightly smaller |β|) |
| REDTYPE ~ PC3 | −0.0603, p=0.111 ✗ | −0.0776, p=0.0162 ✓ | **Newly significant** (same − direction) |
| All other colour × PC1–PC10 | non-sig | non-sig | No other newly significant PC effects |

**Headline claim (unchanged):** WHITE increases and YELLOW decreases with PC2.  
**New secondary claim on primary set:** REDTYPE decreases with PC3 (p=0.016).

### Elevation (genus-controlled MCMCglmm + χ²)

Sources: `step08_outputs_clean/` vs `experiments/expansion/step08_outputs/`.

| Test | Clean n=1,174 | Primary n=1,438 | Change |
|---|---|---|---|
| χ² colour × elev. band | X²=21.96, p=0.0050 ✓ | X²=31.25, p=0.00013 ✓ | **Same** (sig; stronger) |
| WHITE ~ elevation | −0.109, p=0.058 ✗ | −0.123, p=0.022 ✓ | **Newly significant** (−) |
| YELLOW ~ elevation | +0.036, p=0.602 ✗ | +0.011, p=0.869 ✗ | **Same** (non-sig) |
| REDTYPE ~ elevation | +0.132, p=0.060 ✗ | +0.174, p=0.0064 ✓ | **Newly significant** (+) |

**Correct claim on primary n=1,438:** colour composition differs across elevation bands; after genus control, WHITE declines and REDTYPE increases with elevation. YELLOW has no elevation association.  
(Do not cite the earlier clean-set claim that *no* colour had a significant elevation slope — that applied only to n=1,174.)

---

## 2. Gold set

| Quantity | Exact value |
|---|---:|
| Template rows | 100 |
| Human-labelled | **98** |
| Unlabelled (exclude from scoring) | **2** (row 49 genus header `Ginalloa Korth.`; row 100 incomplete `Erigeron uniflorus` stub) |

---

## 3. RQ1 — Benchmark (categoriser **v1** = original pipeline rules)

Scored only on rows with gold labels and a prediction.

| Model | n | Accuracy | Cohen’s κ | Macro-F1 | # wrong |
|---|---:|---:|---:|---:|---:|
| Rule baseline | 97 | 0.7629 | 0.6956 | 0.8035 | 23 |
| Qwen2.5-7B | 98 | 0.8776 | 0.8352 | 0.8745 | 12 |
| Qwen2.5-72B | 98 | 0.8776 | 0.8348 | 0.8735 | 12 |
| Llama-3.3-70B | 98 | 0.8571 | 0.8077 | 0.8606 | 14 |

**Prose (3 d.p.):** baseline 0.763; Qwen-7B/72B **0.878**; Llama **0.857**.

Source predictions: `benchmark/gold_pred_*.csv`  
Saved summary matches recomputation: `benchmark/benchmark_summary.csv`

---

## 4. RQ3 — Categoriser v2 (same free-text, new mapping)

| Model | Acc v1 | Acc v2 | Δ |
|---|---:|---:|---:|
| baseline | 0.7629 | 0.7835 | +0.0206 |
| Qwen-7B | 0.8776 | **0.9388** | **+0.0612** |
| Qwen-72B | 0.8776 | 0.9184 | +0.0408 |
| Llama-70B | 0.8571 | 0.9184 | +0.0612 |

**Prose:** Qwen-7B 0.878 → **0.939** with categoriser v2.

---

## 5. RQ3 — RAG (Qwen-7B + 3 TF-IDF exemplars, leave-one-out)

| Setup | n | Accuracy | # `uncertain` |
|---|---:|---:|---|
| Zero-shot + v1 | 98 | 0.8776 | 0 |
| Zero-shot + v2 | 98 | 0.9388 | 0 |
| RAG + v1 | 98 | 0.8980 | 5 |
| **RAG + v2** | 98 | **0.9490** | 5 |

**Prose:** best reported system **0.949** (RAG + categoriser v2); 5/100 abstentions.

RAG predictions file: 100 rows (`rq3_outputs/gold_pred_qwen7b_rag.csv`).

---

## 6. RQ2 — Qwen-7B disagreements under v1 (exactly 12)

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

## 7. RQ4 — Downstream sensitivity

| Check | Status |
|---|---|
| MCMC chain files | **36/36** present (4 variants × 3 colours × 3 chains) |
| Max MPSRF | **&lt; 1.01** (all ≈ 1.000) |
| WHITE~PC2 (+) significant for all 4 label sources | **Verified** |
| YELLOW~PC2 (−) significant for all 4 label sources | **Verified** |

### WP4 analysis *n* by label source

| Variant | n |
|---|---:|
| baseline | 901 |
| qwen7b | 1,174 |
| qwen72b | 1,166 |
| llama70b | 1,169 |

### Headline PC2 (cite from `wp4_fixed_effects_all_variants.csv`)

| Variant | WHITE~PC2 mean | pMCMC | YELLOW~PC2 mean | pMCMC |
|---|---:|---:|---:|---:|
| baseline | +0.0950 | 0.0004 | −0.0985 | 0.0005 |
| qwen7b | +0.0718 | 0.0003 | −0.0837 | 0.0006 |
| qwen72b | +0.0722 | 0.0005 | −0.0842 | 0.0003 |
| llama70b | +0.0780 | 0.0003 | −0.0819 | 0.0004 |

(Values above rounded to 4 decimals from verification run; use CSV for full precision.)

### Label-dependent (secondary) effects — 30 effects per variant, 5 significant somewhere

| Effect | baseline | qwen7b | qwen72b | llama70b | Holds? |
|---|---|---|---|---|---|
| WHITE~PC2 | ✓ | ✓ | ✓ | ✓ | **all four** |
| YELLOW~PC2 | ✓ | ✓ | ✓ | ✓ | **all four** |
| YELLOW~PC4 | ✗ 0.51 | ✓ 0.0497 | ✓ 0.030 | ✗ 0.060 | label-dependent |
| WHITE~PC9 | ✓ 0.036 | ✗ | ✗ | ✗ | label-dependent |
| REDTYPE~PC7 | ✗ | ✗ | ✓ 0.040 | ✓ 0.030 | label-dependent |

**Correct claim:** label source never flips a headline association, but flips **three of four** secondary ones.
**Do not write** "the one genuine divergence is YELLOW~PC4" — that undercounts.
**Caveat:** baseline n=901 vs LLM n≈1,170, so baseline comparisons confound label accuracy with sample composition.

---

## 7b. Gold-set robustness — junk rows excluded

Excluding the 9 rows flagged `JUNK_NON_SPECIES`:

| System | n=98 v1 | n=98 v2 | n=89 v1 | n=89 v2 |
|---|---:|---:|---:|---:|
| baseline | 0.7629 | 0.7835 | 0.7727 | 0.7955 |
| qwen7b | 0.8776 | 0.9388 | 0.8989 | 0.9438 |
| qwen72b | 0.8776 | 0.9184 | 0.8989 | 0.9326 |
| llama70b | 0.8571 | 0.9184 | 0.8989 | 0.9438 |
| qwen7b RAG | 0.8980 | 0.9490 | 0.8989 | 0.9438 |

Two consequences: **RAG ties zero-shot on species-only rows** (both 84/89 = 0.9438 under v2),
and **all three LLMs tie at 0.8989** under v1 once junk is removed.

**Scoring rule (required to reproduce the RAG figures):** RAG may output `uncertain`;
those are scored as **UNKNOWN**, per `15_RAG_Extract_Gold.py`. Neither categoriser has a
rule for `uncertain`, so without this mapping it falls through to OTHER and RAG scores
0.8539/0.8989 instead. (Historical lock script: `scripts/legacy/25_Lock_Baselines.py`.)

**Do not write** "RAG's only gain is abstention on malformed input" — that is wrong.
Of RAG's 5 abstentions, **4 are on genuine species rows and 1 on a junk row**; all 4
genuine ones have gold = UNKNOWN, i.e. RAG correctly declines to invent a colour when the
treatment states none. The tie is also **not** prediction-identity: zero-shot and RAG
differ on 4 of the 89 rows (2 RAG fixes, 2 RAG breaks) which exactly offset, so McNemar
gives no evidence either way. Correct claim: *RAG matches zero-shot accuracy on genuine
species text while abstaining on rows that carry no colour information.*

---

## 7c. Prediction task (colour ~ environment)

Source: `prediction_outputs/prediction_cv_summary.csv`. **Refreshed on the primary
n=1,438 set** (417 genera; WHITE/YELLOW/REDTYPE = 613/494/331), 5-fold CV.
Figure: `Results/figures/methods/fig14_prediction.{png,pdf}` — all title/caption
numbers are generated from the run, not hardcoded.

Genus-grouped CV (headline; a genus never spans a split):

| Model | Accuracy | Balanced acc. | Macro-F1 [95% CI] |
|---|---:|---:|---|
| Majority class | 0.4263 | 0.3333 | 0.1993 [0.191, 0.208] |
| Logistic regression | 0.4325 | 0.3595 | 0.3135 [0.292, 0.335] |
| **Random forest** (best env. model) | 0.4131 | 0.3628 | 0.3500 [0.325, 0.375] |
| Genus prior | 0.4263 | 0.3333 | 0.1993 [0.191, 0.208] |
| Genus prior, **ungrouped** CV | 0.6161 | 0.6015 | 0.6077 [0.580, 0.633] |

Under grouped CV every test genus is unseen, so the genus prior necessarily
collapses to the majority class — that is expected, not a bug.

**Claims:** environment is statistically associated with colour but **weakly
predictive** (balanced accuracy **0.363 vs 0.333** chance). Relatedness lifts
macro-F1 **2.7× further above the majority floor** than the entire climate+soil
niche (genus prior ungrouped 0.608 vs random forest 0.350, floor 0.199).
Permutation importance: **PC2 = +0.0193 is the only axis with positive
importance** (next, PC8, is −0.0015) — PC2 independently reproduces the MCMCglmm result.

*Historical (earlier clean n=1,174 set): majority 0.200, logreg 0.300, RF 0.326,
genus prior ungrouped 0.605; balanced accuracy 0.342 vs 0.333. Conclusions unchanged.*

---

## 7d. Elevation — primary set (n=1,438; supersedes clean n=1,174 wording)

| Test | Clean n=1,174 | **Primary n=1,438** |
|---|---|---|
| Chi-square colour × band | X²=21.96, p=0.0050 | **X²=31.25, p=0.00013** |
| WHITE ~ elevation | −0.109, p=0.058 ✗ | **−0.123, p=0.022 ✓** |
| YELLOW ~ elevation | +0.036, p=0.602 ✗ | +0.011, p=0.869 ✗ |
| REDTYPE ~ elevation | +0.132, p=0.060 ✗ | **+0.174, p=0.0064 ✓** |

**Correct claim:** on the primary analysis set, colour composition differs across elevation bands;
with genus controlled, WHITE declines and REDTYPE increases with elevation.

---

## 8. Full-treatment prediction files

| File | Rows |
|---|---:|
| `treatments_pred_baseline.csv` | 3,857 |
| `treatments_pred_qwen72b.csv` | 3,857 |
| `treatments_pred_llama70b.csv` | 3,857 |

(Note: full-corpus Qwen-7B colours live in `flower_color_qwen_clean.csv` from the clean pipeline, not necessarily under `benchmark/`.)

---

## 8c. Reliability chapter (three-model agreement — full chain, corrected set)

Source: `Processed Data/experiments/reliability/summary.json`,
`reliability_robustness_table.csv` (also mirrored under `Results/tables/reliability/`).
Built by `scripts/24_Build_Reliability_Set.py` (join + categoriser v2 + validator)
and `scripts/25_Reliability_Ecology.R` at `nitt=1,050,000` (matches step 06).

**These are v2-recode labels on the three-model overlap. They are NOT the published
n=1,438 pipeline ecology table (§1) — do not merge the two.**

Predeclared ecology label = **Qwen-7B v2**; 72B and Llama vote only for
coverage/agreement; keyword baseline is excluded from consensus; UNKNOWN/OTHER are
dropped, never coded as `is_white=0`.

| Set | n |
|---|---:|
| Primary ecology | 1,438 |
| Three-LLM coverage (72B + Llama present) | 1,313 |
| Common known support (all 3 give WHITE/YELLOW/REDTYPE) | **1,149** |
| High confidence (all 3 agree on class) | **1,129** |
| Disagreement (descriptive only) | **20** |

Agreement rate on common-known **0.9826**; on coverage-where-7B-known **0.9733**.
Validator flags: unsupported known colour **26**, wrong-context **11**,
high-confidence-and-supported **1,105**.
Colour counts — common: YELLOW 436 / WHITE 394 / REDTYPE 319; high-conf: 429 / 389 / 311.

### Full-chain robustness (both subsets, genus RE, threshold MCMCglmm)

| Effect | Common-known (n=1,149) | High-confidence (n=1,129) | Verdict |
|---|---|---|---|
| WHITE ~ PC2 | +0.067, p=0.003, CI excl. 0 | +0.071, p=0.002, CI excl. 0 | **robust** |
| YELLOW ~ PC2 | −0.080, p=0.002, CI excl. 0 | −0.080, p=0.001, CI excl. 0 | **robust** |
| REDTYPE ~ PC3 | −0.019, p=0.60 | −0.019, p=0.60 | same direction, CI incl. 0 |
| WHITE ~ elevation | −0.034, p=0.61 | −0.036, p=0.58 | same direction, CI incl. 0 |
| YELLOW ~ elevation | +0.044, p=0.56 | +0.047, p=0.54 | same direction, CI incl. 0 |
| REDTYPE ~ elevation | +0.007, p=0.92 | +0.011, p=0.87 | same direction, CI incl. 0 |

**Correct claim:** WHITE~PC2 (+) and YELLOW~PC2 (−) survive restriction to species
where all three open models agree on a known colour plus a source-text check — i.e.
**robust to disagreement among these three models**, not to all extraction error
(shared OCR/prompt bias can still agree). Elevation and REDTYPE~PC3 do not exclude
zero on these subsets.

**No second-annotator / human IAA study was performed.** Reliability is assessed by
model agreement + lexical source grounding only; the n=98 gold set stays exploratory.

---

## 9. Safe citation checklist

1. Always state **n=98** for gold metrics (2 rows unlabelled).  
2. Always state **which categoriser** (v1 original vs v2 improved).  
3. Best accuracy claim: **0.949 with RAG + categoriser v2**, not “RAG alone = 0.949”.  
4. Scale finding: **72B does not beat 7B under v1** (both 0.8776).  
5. Ecology headlines WHITE~PC2 / YELLOW~PC2 are **robust** (across label sources on n≈1,174 and on primary n=1,438).  
6. Cite ecology composition / elevation from **n=1,438** unless explicitly discussing the earlier clean set or RQ4.  
7. Do not claim full-corpus RAG — only gold-set RAG was run.

---

*Re-run verification anytime:*  
`python3` block in session / or regenerate via re-scoring scripts; report at `Processed Data/experiments/VERIFICATION_REPORT.txt`.
