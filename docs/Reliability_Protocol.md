# Reliability protocol (chapter add-on)

Question: which open-LLM flower-colour labels are reliable enough for downstream
inference?

- Primary ecology table remains n=1,438 with Qwen-7B pipeline labels.
- Three-LLM coverage is smaller: 72B and Llama were run on the 3,857 parsed
  treatments, not the fascicle/recovery increment (~125 ecology species).
- Common known-label support: all three LLMs give WHITE/YELLOW/REDTYPE.
  Ecology models on that set still use **Qwen-7B v2** as the predeclared label.
- High confidence: the three LLMs agree on that known class.
- Disagreement subset is descriptive only.
- Keyword baseline is not part of consensus.
- UNKNOWN is dropped, never coded as is_white=0.
- Source-text validator is a flag, not automatic deletion.
- Existing n=98 gold set is exploratory (v2 was developed there). No independent
  second-annotator study was performed; label quality is assessed through
  three-model agreement + source-text grounding, not human inter-annotator
  agreement.
- Mixed models are **genus-adjusted, not phylogenetically corrected.**
- Reliability ecology is run at full chain length (`nitt=1,050,000`, matching
  `scripts/06_MCMCglmm.R`) via
  `sbatch scripts/slurm/run_25_reliability_ecology.slurm` (`RELIABILITY_FULL=1`).
- **3 independent chains** per model (seeds 42/123/456); inference uses the pooled
  30,000 samples and convergence is reported as Gelman-Rubin MPSRF in
  `reliability_convergence.csv`, with trace plots in
  `experiments/reliability/figures/`.

Observed (v2 labels, three-LLM overlap; not the published n=1,438 pipeline table):

| Set | n |
|---|---:|
| Primary ecology | 1,438 |
| Three-LLM coverage | 1,313 |
| Common known support | 1,149 |
| High confidence (agree) | 1,129 |
| Disagreement | 20 |

Full-chain result (`nitt=1,050,000`, 3 chains pooled):

WHITE~PC2 and YELLOW~PC2 keep sign and exclude zero on both subsets (**robust**):
WHITE~PC2 +0.067 (common) / +0.071 (high-conf); YELLOW~PC2 −0.080 / −0.080.
REDTYPE~PC3 and all three elevation slopes keep direction but include zero on
both subsets (**not robust** under this restriction).

Convergence: all 12 models pass, worst MPSRF **1.000425** (threshold 1.01), lowest
pooled effective sample size **29,380** of 30,000. Going from one chain to three moved
the posterior means by at most 0.0006 and changed no designation.
