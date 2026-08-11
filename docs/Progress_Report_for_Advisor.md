# Thesis Progress Report — For Advisor Meeting

**Student:** Dharati Patel  
**Degree:** MS Computer Science, University of Georgia  
**Working title:** *Benchmarking and Improving Open-Source LLM Extraction of Plant Traits from Botanical Text: A Flora of India Case Study*  
**Date:** August 2026  

This document explains **what the project is**, **what has been completed**, **why each advanced piece was added**, and **how it maps to the request for RAG and specificity improvement**. It is written so it can be walked through in a meeting (motivation first, then evidence).

---

## 1. One-paragraph pitch

Plant trait databases under-represent Indian flora. Flower colour is written in natural language inside scanned *Flora of India* volumes, not as structured fields. The project builds an end-to-end pipeline that extracts flower colour with open LLMs, links species to GBIF occurrences and climate/soil data, and tests colour–environment associations with Bayesian mixed models. The **computer-science contribution** goes beyond “we applied an LLM”: it **measures** extraction quality against a human gold standard, **diagnoses** systematic failures, **improves** specificity with a better categoriser plus retrieval-augmented generation (RAG) and abstention, and **tests** whether label quality changes the ecological conclusions.

---

## 2. Does this address “RAG and specificity improvement”?

**Yes — that is explicitly RQ3 in the current plan.**

| Advisor ask | How the thesis addresses it | Status |
|---|---|---|
| **RAG** | Leave-one-out TF-IDF retrieval of similar gold exemplars; few-shot RAG prompt for Qwen-7B on the gold set; floral-only + primary-colour instructions | **Done** (gold-set experiment complete) |
| **Specificity improvement** | (a) Error taxonomy showing *where* specificity fails (fruit vs flower, multi-colour, category priority); (b) improved categoriser (first colour + compound handling); (c) RAG prompt rules that ignore fruit/berry colour and allow `uncertain` abstention | **Done / measured** |

In plain language for the meeting:

> “Specificity” here means: extract the *right* trait (flower pigment, not fruit colour), assign the *right* colour class when several colours appear, and *not* invent a colour when none is stated. We improve that with better post-processing rules, retrieval of labelled examples, and an abstain option when the model is unsure.

---

## 3. Research questions (the story you tell)

1. **RQ1 — Benchmark:** How accurate are open LLMs vs a rule baseline, and does a much larger model help?  
2. **RQ2 — Errors:** Where do systems fail (semantic vs data/pipeline issues)?  
3. **RQ3 — Improvement:** Do a better categoriser + RAG + abstention raise accuracy / specificity?  
4. **RQ4 — Downstream impact:** If we swap label sources, do the ecological findings hold?

---

## 4. Phase A — Original pipeline (baseline thesis work)

This is the “ecology + LLM application” foundation, analogous to Bamba & Sato (2025) but on *Flora of India* with an open model.

### 4.1 What was built and why

| Stage | Purpose |
|---|---|
| Scrape / extract text from Flora PDFs | Get unstructured botanical descriptions |
| Parse species blocks | Turn continuous OCR text into per-species records |
| Qwen2.5-7B colour extraction | Free-text colour phrases from descriptions |
| Keyword categorisation | Map phrases → WHITE / YELLOW / RED / PINK / PURPLE-BLUE → REDTYPE |
| GBIF occurrences | Geographic points for each coloured species |
| WorldClim + SoilGrids + PCA | Environmental niche summary (PC1–PC10) |
| MCMCglmm (genus random effect) | Test colour ~ environment with relatedness control |
| Elevation analysis | India-specific novel ecology extension |

### 4.2 Key numbers (analysis-ready ecology set)

| Quantity | Value |
|---|---:|
| Volumes used | 8 |
| Unique treatments (clean parser) | 3,857 |
| With morphological description | 3,230 |
| Final ecology *n* (colour + env complete) | **1,174** |
| WHITE / YELLOW / REDTYPE | 502 / 428 / 244 |
| Env variables → PCA | 30 → PC1–PC10 (~97% variance) |
| Headline ecology result | WHITE↑ with PC2; YELLOW↓ with PC2 (significant) |

### 4.3 Figures already made (ecology / pipeline)

| Figure | What it shows (how to explain it) |
|---|---|
| `fig1_colour_counts` | How many species fall in each colour class — dataset composition |
| `fig2_mcmc_coefficients` | Which environmental PCs predict each colour (forest-style coefficients) |
| `fig2b_mcmc_env_variables` | Same idea for individual climate/soil variables |
| `fig3_pca_loadings` | What PC1/PC2 *mean* environmentally (loadings heatmap) |
| `fig4_convergence` | MCMC diagnostics — models are trustworthy |
| `fig5_pipeline_summary` | End-to-end pipeline overview |
| `figS_traceplots` | Supplementary MCMC traces |
| `fig6_*` elevation set | Colour composition and elevation associations along India’s altitude gradient |

These figures support the **ecological** chapters. The CS/method chapters have their own figure set (§7).

---

## 5. Phase B — Advanced work added in recent weeks

This is what turns a replication into a **method thesis**. All of it lives under `scripts/experiments/` and `Processed Data/experiments/` so the original pipeline stays intact.

### 5.1 Cleaner species parsing (data quality)

**Problem.** The first parser mixed identification-key stubs and abbreviated-genus duplicates with real treatments, which hurt GBIF matching and polluted labels.

**What we did.** A treatment-focused parser that keeps species treatments, recovers abbreviated genera when justified, and deduplicates binomials.

**Why it matters.** Higher GBIF match rate; final *n* stayed ~1,174 but on cleaner identities — quality over illusory sample-size inflation.

### 5.2 Human gold standard (evaluation foundation)

**Problem.** Without human labels, you cannot claim “the LLM is accurate” — only that it produced outputs.

**What we did.** Stratified gold set (~100 rows; **98 labelled**): clear colours, ambiguous phrases, and “no colour mentioned.” Human filled `gold_free_text` + `gold_category`.

**Why it matters.** Every accuracy number below is against this answer key. That is standard NLP evaluation practice.

### 5.3 RQ1 — Multi-model benchmark (accuracy / specificity measurement)

**Problem.** One model run is anecdotal. We need a floor (rules), open mid-size models, and large open models.

**What we did.**

- Rule-based regex baseline (keyword on floral sentences only)  
- Qwen2.5-7B, Qwen2.5-72B, Llama-3.3-70B on the same gold descriptions  
- Metrics: accuracy, macro-F1, Cohen’s κ, confusion matrices  

**Results (coarse classes WHITE / YELLOW / REDTYPE / UNKNOWN; original categoriser):**

| System | Accuracy | Cohen’s κ |
|---|---:|---:|
| Rule baseline | 0.763 | 0.696 |
| Qwen-7B | **0.878** | **0.835** |
| Qwen-72B | 0.878 | 0.835 |
| Llama-70B | 0.857 | 0.808 |

**How to explain this.** Open LLMs clearly beat naive rules. Scaling to 70B/72B **does not** improve accuracy on this task — a useful negative result about cost–benefit of large models for short botanical extraction.

### 5.4 RQ2 — Error taxonomy (where specificity fails)

**Problem.** “88% accurate” hides *which* mistakes hurt scientific use.

**What we found for Qwen-7B’s 12/98 disagreements:**

| Error type | Count | Interpretation |
|---|---:|---|
| Category priority | 4 | Free text mostly right; keyword order (e.g. WHITE before PINK) flipped the class |
| Junk / non-species rows | 3 | Genus headers / key stubs in the sample |
| Multi-colour ambiguity | 2 | “pink or white” style phrases |
| Contamination | 1 | Parser merged another species’ text (*Oxalis* example) |
| False positive / false negative | 1 + 1 | Invented colour or missed colour |

**How to explain this.** Most remaining errors are **specificity / aggregation / data** issues, not “the model cannot read English.” That directly motivates better categorisation and RAG, not only a bigger model.

Corpus scan (supporting): ~14 clear cross-family contaminated blocks (~0.4% of 3,857); fruit-near-colour wording appears more often as a *risk surface*.

### 5.5 RQ3 — Specificity improvement + RAG (advisor-requested)

#### A. Improved categoriser (specificity of class assignment)

**Idea.** Prefer the **first colour word** in the phrase (usually the dominant pigment), expand synonyms (`scarlet` → red), and normalise compounds (`greenish-white` → white).

**Effect on the same free-text predictions (no re-running LLMs):**

| System | Acc (old cat.) | Acc (new cat.) | Gain |
|---|---:|---:|---:|
| Qwen-7B | 0.878 | **0.939** | **+0.061** |
| Qwen-72B | 0.878 | 0.918 | +0.041 |
| Llama-70B | 0.857 | 0.918 | +0.061 |

**How to explain this.** A large share of “errors” was post-processing, not generation. Fixing specificity at the mapping stage is cheap and high-impact.

#### B. RAG + abstention (specificity of *what* is extracted)

**Idea.** For each gold description, retrieve the 3 most similar *other* labelled descriptions (TF-IDF, leave-one-out — no label leakage). Add them as few-shot exemplars. Prompt explicitly: use flower/petal colour only; ignore fruit/berry; if ambiguous return `uncertain`.

**Results:**

| System | Categoriser | Accuracy | Notes |
|---|---|---:|---|
| Qwen-7B zero-shot | v1 | 0.878 | Original setup |
| Qwen-7B zero-shot | v2 | 0.939 | Categoriser only |
| **Qwen-7B RAG** | v1 | **0.898** | +RAG alone |
| **Qwen-7B RAG** | v2 | **0.949** | RAG + better categoriser |
| RAG abstentions | — | 5 of 98 scored | Model said `uncertain` |

**How to explain this.** RAG alone helps a little; **RAG + specificity-aware categorisation** reaches ~95% on the gold set. Abstention is the start of selective prediction (“know when not to guess”).

#### C. What RAG actually contributes (ablation)

Excluding the 9 gold rows flagged `JUNK_NON_SPECIES` (genus headers and key stubs) and re-scoring:

| System | full n=98, v1 → v2 | species-only n=89, v1 → v2 |
|---|---|---|
| Qwen-7B zero-shot | 0.8776 → 0.9388 | 0.8989 → 0.9438 |
| Qwen-7B RAG | 0.8980 → 0.9490 | 0.8989 → 0.9438 |

On species treatments alone, **RAG and zero-shot are identical**. RAG's measured advantage is concentrated entirely in correctly abstaining on malformed, non-species input.

**How to explain this.** Each intervention fixed the error class it was designed to fix — that is what the RQ2 taxonomy predicted. Category-priority errors were never RAG's target (they are post-processing, hence categoriser v2); RAG targeted malformed input and ambiguity, and it eliminated the malformed-input errors. Together the two interventions clear 10 of the original 12 errors. Honest limitation: only ~4–5 of the 98 gold items are of the type RAG addresses, so the correct statement is **“no measurable effect on ordinary species treatments at this sample size,”** not “no effect.”

Side note: excluding junk rows, all three LLMs tie at **0.8989** under v1 — Llama-70B's apparent deficit was junk-row handling, not colour extraction. This strengthens the “scale does not help” result.

### 5.6 RQ4 — Downstream sensitivity (why CS quality matters scientifically)

**Idea.** Environmental PCs are fixed; only colour labels change by model. Re-fit MCMCglmm under baseline / Qwen-7B / Qwen-72B / Llama-70B labels.

**Result.** The headline associations **WHITE~PC2 (+)** and **YELLOW~PC2 (−)** remain significant under **all four** label sources. Convergence excellent (MPSRF ≈ 1.000).

Across the 30 colour × PC fixed effects per label source, five reach significance somewhere. Two hold under **all four** sources; **three are label-dependent**:

| Effect | baseline | qwen7b | qwen72b | llama70b |
|---|---|---|---|---|
| WHITE~PC2 | ✓ | ✓ | ✓ | ✓ |
| YELLOW~PC2 | ✓ | ✓ | ✓ | ✓ |
| YELLOW~PC4 | ✗ (p=0.51) | ✓ (p=0.0497) | ✓ (p=0.030) | ✗ (p=0.060) |
| WHITE~PC9 | ✓ (p=0.036) | ✗ | ✗ | ✗ |
| REDTYPE~PC7 | ✗ | ✗ | ✓ (p=0.040) | ✓ (p=0.030) |

Effects significant under **both** the baseline and an LLM source agree to within **0.023** in posterior mean. So: label source never flips a headline association, but it flips **three of the four secondary ones**, all of which sit at p ≈ 0.03–0.06 where instability is expected.

*Caveat to state in the write-up:* the baseline variant is fitted on a different subset (n=901 vs 1,174), so baseline-vs-LLM coefficient differences confound label accuracy with sample composition.

**How to explain this.** Extraction noise does not overturn the main ecological story — important for trusting the science — while still justifying better labels for secondary findings and database quality.

---

## 6. Side-by-side: old work vs new advanced work

| | Earlier work | Recent advanced work |
|---|---|---|
| Goal | Build dataset + ecology | Evaluate & improve extraction |
| Evaluation | Informal / none | Human gold set + κ / F1 |
| Models | Qwen-7B only | Baseline + 7B + 72B + Llama-70B |
| Failure analysis | Anecdotal | Formal error taxonomy |
| Improvement | — | Categoriser v2 + RAG + abstention |
| Ecology robustness | Single label source | Multi-source sensitivity (RQ4) |
| Advisor themes | Application | **RAG + specificity** |

---

## 7. Figures

### Ecology / pipeline chapters

- Colour counts, MCMC coefficients, PCA loadings, convergence, pipeline summary, elevation suite (§4.3).

### CS / method chapters — **generated**

Built by `scripts/experiments/build_cs_figures.py` (fig7–fig13) and
`build_prediction_figure.py` (fig14); 400-dpi PNG + vector PDF, living
alongside the ecology figures in `Results/figures/main/` — one flat,
continuously numbered sequence rather than a separate folder.

| Figure | RQ | What it shows | Why the professor will care |
|---|---|---|---|
| `fig7_benchmark` | RQ1 | Accuracy and κ as dot plots with 4,000-replicate bootstrap intervals, plus per-class F₁ heatmap | Open LLMs beat rules; 7B vs 72B intervals overlap, so scale genuinely does not help |
| `fig8_confusion` | RQ1 | Row-normalised confusion structure, four models | Exactly *which* classes confuse — REDTYPE is the weak class everywhere |
| `fig9_label_flow` | RQ1 | Alluvial gold → predicted, baseline vs Qwen-7B | Baseline bleeds into UNKNOWN/OTHER (recall failure); LLM error is a thin REDTYPE band |
| `fig10_error_taxonomy` | RQ2 | Bubble matrix of failure modes × system, with totals | Specificity failure modes, and the qualitative shift from recall to adjudication errors |
| `fig11_interventions` | RQ3 | Slopegraph cat. v1→v2, plus item-level grid of every item any configuration fails or abstains on | Directly answers “did RAG/specificity help?”, and exposes the irreducible hard core |
| `fig12_rq4_forest` | RQ4 | Forest of all colour × PC effects under four label sources | Which associations survive a change of label source |
| `fig13_rq4_concordance` | RQ4 | Coefficient concordance vs identity line, significance-coded | Links NLP quality to science: significant effects agree to within 0.023 |
| `fig14_prediction` | prediction task | Macro-F1 under genus-grouped CV, grouped vs ungrouped comparison, permutation importance | Environment barely beats the majority floor; genus predicts colour ~3x better than climate/soil |

Abstention is reported inside `fig11_interventions` (hatched cells) rather than as a separate
accuracy–coverage curve, since a single abstention threshold gives only one operating point.

**Not yet made:** cost vs accuracy (GPU-hours). Needs Slurm accounting to be pulled from
the job logs; a small job, worth doing only if the professor wants the deployment argument.

---

## 8. What is finished vs still open

### Finished
- Clean treatment pipeline + ecology *n* = 1,174  
- Gold set + multi-model benchmark  
- Error taxonomy  
- Categoriser v2 gains  
- RAG gold-set run + scores  
- RQ4 sensitivity for four label sources  
- **CS/method figure set (7 figures, §7)**  
- Chapter 3 draft (`docs/drafts/Chapter3_Data_and_Pipeline_Draft.md`)  
- Method plan (`docs/Thesis_MethodDepth_Plan.md`)  
- Number verification (`docs/VERIFIED_Numbers_for_Thesis.md`)  

### Still open — decisions to raise in the meeting
1. **Thesis writing: Chapters 4–7 + Intro / Discussion.** This is the critical path; no new experiments are required to start.  
2. **Full-corpus RAG?** RAG is currently evaluated on the gold set only. Applying categoriser v2 + RAG to all 3,857 treatments and refreshing the ecology would make the pipeline self-consistent, but costs GPU time and would require re-running the MCMC set. *Ask whether this is expected for an MS scope.*  
3. **Expand the gold set beyond 98?** Would tighten the confidence intervals that currently make 7B vs 72B indistinguishable. *Ask whether the negative result needs more statistical power to be publishable.*  
4. Optional: cost–accuracy plot from Slurm accounting.  
5. Optional stretch: a closed model (e.g. GPT-4o) on the gold set as a commercial reference point.  

---

## 9. Talking points if asked tough questions

**“Is this just a replication of the China paper?”**  
No. The China paper showed feasibility. We add rigorous open-model evaluation, error analysis, RAG/specificity interventions, and a sensitivity test of ecological conclusions under label noise.

**“Did RAG help?”**  
Yes, modestly alone (0.878 → 0.898); more when combined with the specificity-aware categoriser (→ **0.949**). Many “LLM errors” were actually class-mapping errors.

**“Why not only use Llama/GPT?”**  
We compared open families. On this task, Qwen-7B matches or beats larger Llama/Qwen-72B — important for reproducible, low-cost science.

**“Is *n*=98 gold enough?”**  
Adequate for an MS demonstration and clear effect sizes; confidence intervals are wide for tiny model differences. Expanding the gold set is listed as optional strengthening.

**“What about OCR?”**  
OCR noise is a property of the data and appears in the error taxonomy (contamination, truncated names). It is **supporting** evidence, not the thesis title claim.

**“Your RAG result is on the gold set — does it hold on the whole corpus?”**  
Honest answer: unknown. RAG was evaluated on the 98 gold items only; the full 3,857-treatment corpus still uses zero-shot Qwen-7B labels. The categoriser v2 gain *does* apply corpus-wide because it is pure post-processing. Whether to re-run RAG at corpus scale is open item §8.2.

**“Why is accuracy 0.949 and not the 0.878 in the earlier table?”**  
Always cite the categoriser version. 0.878 is zero-shot with categoriser v1; 0.939 is the same predictions under v2; 0.949 is RAG **plus** v2. RAG alone under v1 is 0.898.

---

## 10. Bottom line for the advisor

1. The **ecology pipeline is complete** and produces a coherent Indian flower-colour–environment analysis (*n* = 1,174).  
2. The **CS contribution is in place**: benchmark, error taxonomy, **specificity-aware categorisation**, **RAG + abstention**, and downstream sensitivity.  
3. That directly matches the request for **advanced work: RAG and specificity improvement**, with measured numbers, not only an engineering claim.  
4. Remaining work is **writing**, not a new research direction. All experiments and figures are done; the open questions are scope decisions (full-corpus RAG, gold-set size), not missing results.

---

*Internal paths for evidence:*  
`Processed Data/experiments/benchmark/`, `rq2_outputs/`, `rq3_outputs/`, `wp4_label_variants/results/`, `docs/Thesis_MethodDepth_Plan.md`, `docs/drafts/Chapter3_Data_and_Pipeline_Draft.md`
