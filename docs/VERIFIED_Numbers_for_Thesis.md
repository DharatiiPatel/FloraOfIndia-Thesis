## 1. Clean ecology pipeline

| Quantity | Exact value |
|---|---:|
| Unique species treatments | 3,857 |
| Treatments with description | 3,230 |
| Final analysis *n* | **1,174** |
| WHITE | 502 |
| YELLOW | 428 |
| REDTYPE | 244 |

Source: `species_descriptions_treatments.csv`, `step05b_outputs_clean/species_color_environment_final_clean.csv`

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
|---|---:|---:|---:|
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
0.8539/0.8989 instead. Verified by `25_Lock_Baselines.py`.

**Do not write** "RAG's only gain is abstention on malformed input" — that is wrong.
Of RAG's 5 abstentions, **4 are on genuine species rows and 1 on a junk row**; all 4
genuine ones have gold = UNKNOWN, i.e. RAG correctly declines to invent a colour when the
treatment states none. The tie is also **not** prediction-identity: zero-shot and RAG
differ on 4 of the 89 rows (2 RAG fixes, 2 RAG breaks) which exactly offset, so McNemar
gives no evidence either way. Correct claim: *RAG matches zero-shot accuracy on genuine
species text while abstaining on rows that carry no colour information.*

---

## 7c. Prediction task (colour ~ environment)

Source: `prediction_outputs/prediction_cv_summary.csv`. n=1,174 species, 338 genera, 5-fold CV.

| Model | Accuracy | Balanced acc. | Macro-F1 [95% CI] |
|---|---:|---:|---|
| Majority class | 0.4276 | 0.3333 | 0.200 [0.190, 0.209] |
| Logistic regression | 0.4250 | 0.3460 | 0.300 [0.279, 0.320] |
| Random forest | 0.4012 | 0.3424 | 0.326 [0.300, 0.351] |
| Genus prior, **ungrouped** CV | 0.6210 | 0.5997 | 0.605 [0.575, 0.634] |

**Claims:** environment is statistically associated with colour but **weakly predictive**
(balanced accuracy 0.342 vs 0.333 chance). **Genus predicts ~3× better than environment.**
Permutation importance: PC2 = 0.0236, next axis PC4 = 0.0028 — PC2 independently reproduces the MCMCglmm result.

---

## 7d. Elevation — clean pipeline (supersedes old numbers)

Source: `step08_outputs_clean/`. Old `step08_outputs/` numbers are superseded.

| Test | Old data | **Clean data** |
|---|---|---|
| Chi-square colour × band | X²=19.96, p=0.0105 | **X²=21.96, p=0.0050** |
| WHITE ~ elevation | −0.107, p=0.071 ✗ | −0.109, p=0.058 ✗ |
| YELLOW ~ elevation | +0.023, p=0.749 ✗ | +0.036, p=0.602 ✗ |
| REDTYPE ~ elevation | +0.136, p=0.044 ✓ | **+0.132, p=0.060 ✗** |

**Correct claim:** colour composition differs across elevation bands, but **no colour has a
significant elevation association once genus is controlled.** Do not cite the old p=0.044 REDTYPE result.

---

## 8. Full-treatment prediction files

| File | Rows |
|---|---:|
| `treatments_pred_baseline.csv` | 3,857 |
| `treatments_pred_qwen72b.csv` | 3,857 |
| `treatments_pred_llama70b.csv` | 3,857 |

(Note: full-corpus Qwen-7B colours live in `flower_color_qwen_clean.csv` from the clean pipeline, not necessarily under `benchmark/`.)

---

## 9. Safe citation checklist

1. Always state **n=98** for gold metrics (2 rows unlabelled).  
2. Always state **which categoriser** (v1 original vs v2 improved).  
3. Best accuracy claim: **0.949 with RAG + categoriser v2**, not “RAG alone = 0.949”.  
4. Scale finding: **72B does not beat 7B under v1** (both 0.8776).  
5. Ecology headline is **robust across four label sources**.  
6. Do not claim full-corpus RAG — only gold-set RAG was run.

---

*Re-run verification anytime:*  
`python3` block in session / or regenerate via re-scoring scripts; report at `Processed Data/experiments/VERIFICATION_REPORT.txt`.
