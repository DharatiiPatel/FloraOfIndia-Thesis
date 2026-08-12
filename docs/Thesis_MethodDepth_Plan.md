# Thesis Method-Depth Plan

**Working title:** *Benchmarking and Improving Open-Source LLM Extraction of Plant
Traits from Botanical Text: A Flora of India Case Study*

**Student:** Dharati Patel · MS Computer Science · University of Georgia
**Status:** planning doc (internal). Supersedes the "replication only" framing.

---

## 1. The core idea (what makes this a CS thesis, not a replication)

The original Bamba & Sato (2025) work showed LLMs *can* extract flower colour from
Flora of China. This thesis asks the harder, more general questions that a computer
scientist (not a botanist) should own:

1. **How good is the extraction, really?** — rigorous, multi-model evaluation
   against a human gold standard, not just "we ran an LLM and got numbers."
2. **How do we make the output trustworthy?** — retrieval augmentation and
   confidence-based abstention as *measured* interventions.
3. **Does extraction quality matter?** — do the downstream ecological conclusions
   change depending on how good the extraction was?

Flora of India (scanned PDFs, OCR-degraded) is the case study. The OCR noise is a
**property of the data that makes the error analysis interesting** — it is NOT the
thesis's central claim.

---

## 2. Thesis statement

> *Open-source LLMs can extract plant traits from unstructured botanical text at a
> quality that rivals paid models, and their remaining errors are systematic,
> characterizable, and partly correctable with retrieval and abstention. Crucially,
> extraction quality has measurable downstream consequences for the ecological
> conclusions drawn from the resulting trait database.*

---

## 3. Research questions

| RQ | Question | Deliverable |
|----|----------|-------------|
| **RQ1** | How accurately do open LLMs extract flower colour, and how does accuracy scale with model size vs. a rule-based floor vs. a paid model? | Benchmark table + confusion matrices |
| **RQ2** | Where and why do the models fail? (semantic ambiguity + data-noise error modes) | Error taxonomy + prevalence counts |
| **RQ3** | Can retrieval augmentation and/or confidence-based abstention reduce errors? | Before/after deltas on the gold set |
| **RQ4** | Does better extraction change the downstream ecological findings? | Sensitivity analysis of the MCMCglmm results |

RQ1/RQ3 are the *method* core. RQ4 is the *payoff* that ties method to science.
RQ2 is *supporting* (this is where OCR-noise analysis lives, alongside genuine
semantic ambiguity — it is one category among several, not the headline).

---

## 4. Work packages (with brief steps)

### WP1 — Multi-model extraction benchmark  *(RQ1)*  — IN PROGRESS
- [x] Build model-agnostic extractor, rule-based baseline, gold-set scorer.
- [x] Score baseline + Qwen-7B (preliminary).
- [ ] Run Qwen-72B (submitted) and Qwen-7B-on-full-gold (submitted).
- [ ] Add Llama-3.3-70B when HF access clears (one `--task` + one `--pred` line).
- [ ] (Optional) Add GPT-4o as the recognizable paid anchor (~$1 on gold set).
- **Produces:** benchmark_summary.csv, per-model confusion matrices → Results table + Fig.

### WP2 — Error taxonomy & failure analysis  *(RQ2, supporting)*
- [ ] Define the error categories from real cases already found:
      semantic — fruit/berry colour vs flower, indument vs pigment ("white-tomentose"),
      multi-colour, hallucinated "no mention";
      data-noise — cross-family block contamination, abbreviated genus, truncated
      epithet, digit/letter OCR confusion.
- [ ] Auto-detect + count prevalence of each across all 3,857 treatments.
- [ ] Sample-verify each category against the gold set.
- [ ] Quantify how many of the final ~1,174 analysis species carry a wrong label.
- **Produces:** error_taxonomy.csv, prevalence bar chart, worked examples.

### WP3 — Improvement: RAG + confidence/abstention  *(RQ3)*
- [ ] **RAG:** retrieve the correct treatment boundary / exemplar labelled
      descriptions to reduce contamination + ambiguity errors; measure delta per
      error category on the gold set.
- [ ] **Abstention:** have the model emit a confidence / "uncertain" flag; plot
      accuracy-vs-coverage (selective prediction) and calibration.
- **Produces:** RAG before/after table, accuracy–coverage curve, calibration plot.

### WP4 — Downstream impact / sensitivity  *(RQ4, the payoff)*
- [ ] Re-run the environment linking + MCMCglmm under different label sources:
      (a) rule-based baseline, (b) Qwen-7B, (c) best model, (d) gold-corrected subset.
- [ ] Report whether the significant colour–environment associations hold, strengthen,
      or flip.
- **Produces:** side-by-side coefficient table, "robustness of findings" figure.

### WP5 — Cost–accuracy frontier  *(supports RQ1)*
- [ ] Log GPU-hours, throughput, and $ per 1,000 extractions per model.
- **Produces:** cost-vs-accuracy scatter → "is a 10× bigger model worth it?"

### WP6 — (Optional, time-permitting)
- Trait imputation / classification for species where extraction/GBIF failed.
- Gold-set expansion to ~300–500 rows for statistical power.
- Cross-flora generalization test on a Flora of China subset.

---

## 5. Mapping to thesis chapters

```
1. Introduction            - trait databases, Indian gap, why LLMs, contributions
2. Related Work            - Bamba&Sato, TRY/GBIF, LLM extraction, flower-colour ecology
3. Data & Pipeline         - scraping, parsing, extraction, GBIF, environment (existing)
4. Extraction Benchmark    - RQ1  (WP1, WP5)
5. Error Analysis          - RQ2  (WP2)   <- OCR noise lives here, as one category
6. Improving Extraction    - RQ3  (WP3: RAG + abstention)
7. Downstream Impact       - RQ4  (WP4)   <- the payoff chapter
8. Ecological Results      - existing MCMCglmm + elevation (secondary novelty)
9. Discussion / Limitations / Conclusion
```

---

## 6. Priority order

1. **WP1** finish (benchmark) — running now.
2. **WP4** (downstream impact) — cheap, high-impact, reuses existing pipeline.
3. **WP2** (error taxonomy) — supporting, mostly analysis scripts.
4. **WP3** (RAG + abstention) — the main new engineering.
5. **WP5** cost frontier — free data from the runs.
6. **WP6** optional extensions.

*Everything is built in `scripts/` (numbered 09+, alongside the main pipeline)
and writes to `Processed Data/experiments/` — the original pipeline outputs
are never touched.*
