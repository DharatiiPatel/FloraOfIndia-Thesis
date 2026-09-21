#!/usr/bin/env python3
"""
Regression audit: recompute every number cited in docs/VERIFIED_Numbers_for_Thesis.md
straight from the raw outputs and compare against the documented value.

Nothing here reads the prose doc; the expected values are hard-coded below, so this
doubles as a regression test. If a rerun legitimately changes a number, update the
EXPECTED entry in the same commit that changes the result.

    python3 scripts/27_Audit_All_Numbers.py

Exit status: 0 if every check passes, 1 if any FAIL. Outputs still being produced by
an in-flight job report PENDING (not FAIL) so the harness is safe to run any time.
"""

import csv
import json
import importlib.util
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "Processed Data" / "experiments"
REL = EXP / "reliability"

# ---------------------------------------------------------------- expected values
E_CORPUS = {"treatments": 3857, "with_description": 3230}
E_ECOLOGY = {"primary_n": 1438, "primary": {"WHITE": 613, "YELLOW": 494, "REDTYPE": 331},
             "clean_n": 1174, "clean": {"WHITE": 502, "YELLOW": 428, "REDTYPE": 244}}
E_GOLD = {"template": 100, "labelled": 98, "junk": 9, "n89": 89}
# (v1 accuracy, v2 accuracy, v1 on n=89, v2 on n=89, n scored)
E_BENCH = {
    "baseline":   (0.7629, 0.7835, 0.7727, 0.7955, 97),
    "qwen7b":     (0.8776, 0.9388, 0.8989, 0.9438, 98),
    "qwen72b":    (0.8776, 0.9184, 0.8989, 0.9326, 98),
    "llama70b":   (0.8571, 0.9184, 0.8989, 0.9438, 98),
    "qwen7b_rag": (0.8980, 0.9490, 0.8989, 0.9438, 98),
}
E_KAPPA = {"baseline": 0.6956, "qwen7b": 0.8352, "qwen72b": 0.8348, "llama70b": 0.8077}
E_RAG = {"abstentions": 5, "abstain_junk": 1, "abstain_genuine": 4,
         "vs_zeroshot_differ": 4, "rag_fixes": 2, "rag_breaks": 2}
E_RQ2_QWEN7B = {"CATEGORY_PRIORITY": 4, "JUNK_NON_SPECIES": 3, "MULTI_COLOUR": 2,
                "CONTAMINATION": 1, "FALSE_POSITIVE": 1, "FALSE_NEGATIVE": 1}
E_RQ4_N = {"baseline": 901, "qwen7b": 1174, "qwen72b": 1166, "llama70b": 1169}
# variant -> (WHITE~PC2 mean, p, YELLOW~PC2 mean, p)
E_RQ4_PC2 = {"baseline": (0.0950, 0.0004, -0.0985, 0.0005),
             "qwen7b":   (0.0718, 0.0003, -0.0837, 0.0006),
             "qwen72b":  (0.0722, 0.0005, -0.0842, 0.0003),
             "llama70b": (0.0780, 0.0003, -0.0819, 0.0004)}
E_RQ4_SIG = {"WHITE~PC2": ["baseline", "llama70b", "qwen72b", "qwen7b"],
             "YELLOW~PC2": ["baseline", "llama70b", "qwen72b", "qwen7b"],
             "YELLOW~PC4": ["qwen72b", "qwen7b"],
             "WHITE~PC9": ["baseline"],
             "REDTYPE~PC7": ["llama70b", "qwen72b"]}
E_PRIMARY_PC = {("WHITE", "PC2"): (0.0720, 0.0002), ("YELLOW", "PC2"): (-0.0697, 0.0010),
                ("REDTYPE", "PC3"): (-0.0776, 0.0162)}
E_ELEV = {"WHITE": (-0.1227, 0.0224), "YELLOW": (0.0109, 0.8692), "REDTYPE": (0.1742, 0.0064)}
E_ELEV_CHISQ = (31.246, 0.000127)
E_CLEAN_PC = {("WHITE", "PC2"): 0.0718, ("YELLOW", "PC2"): -0.0841, ("REDTYPE", "PC3"): -0.0603}
E_CLEAN_ELEV = {"WHITE": -0.109, "YELLOW": 0.036, "REDTYPE": 0.132}
E_CLEAN_CHISQ = (21.964, 0.004982)
E_FUNNEL = {"primary_ecology": 1438, "three_llm_coverage": 1313, "common_known_support": 1149,
            "high_confidence": 1129, "disagreement": 20, "unsupported": 26, "wrong_context": 11,
            "agreement_rate": 0.9733}
E_ROBUST = ["WHITE~PC2", "YELLOW~PC2"]
# Posterior means cited in VERIFIED_Numbers §8c, pooled over 3 chains (job 48203984).
E_REL_EFFECTS = {
    ("common_known", "WHITE", "PC2"): 0.066741,
    ("common_known", "YELLOW", "PC2"): -0.080198,
    ("common_known", "REDTYPE", "PC3"): -0.019717,
    ("high_confidence", "WHITE", "PC2"): 0.070539,
    ("high_confidence", "YELLOW", "PC2"): -0.079732,
    ("high_confidence", "REDTYPE", "PC3"): -0.018921,
}
# Convergence thresholds for the reliability chapter (§8c).
E_REL_CONVERGENCE = {"n_chains": 3, "pooled_samples": 30000,
                     "mpsrf_max": 1.01, "ess_min": 1000}
E_PRED = {"n_species": 1438, "n_genera": 417,
          "majority": (0.4263, 0.3333, 0.1993), "logreg": (0.4325, 0.3595, 0.3135),
          "random_forest": (0.4131, 0.3628, 0.3500), "genus_prior_macro_f1": 0.6077,
          "ratio": 2.7, "only_positive_axis": "PC2"}
FIGURES = [
    "ecology/fig1_colour_counts.png", "ecology/fig2_mcmc_coefficients.png",
    "ecology/fig3_pca_loadings.png", "ecology/fig4_convergence.png",
    "ecology/fig5_pipeline_summary.png", "ecology/fig6_elevation_colour_proportions.png",
    "ecology/fig6_elevation_density.png", "ecology/fig6_elevation_mcmc_coefficients.png",
    "ecology/fig6_elevation_pc2_boxplot.png", "ecology/fig6_elevation_species_counts.png",
    "methods/fig7_benchmark.png", "methods/fig8_confusion.png", "methods/fig9_label_flow.png",
    "methods/fig10_error_taxonomy.png", "methods/fig11_interventions.png",
    "methods/fig12_rq4_forest.png", "methods/fig13_rq4_concordance.png",
    "methods/fig14_prediction.png", "reliability/fig15_reliability_pipeline.png",
    "reliability/fig16_agreement_counts.png", "reliability/fig17_reliability_forest.png",
    "supplementary/coefficient_plot_PC1_PC3.png", "supplementary/fig2_supp_PC6_10.png",
    "supplementary/figS_traceplots.png",
]

# ------------------------------------------------------------------------ harness
RESULTS = []


MARK = {"PASS": "✓", "FAIL": "✗", "PEND": "…"}


def record(status, section, name, detail):
    RESULTS.append((status, section, name, detail))
    print(f"  {MARK[status]} {name}: {detail}")


def eq(section, name, got, want, tol=5e-4):
    if got is None:
        record("PEND", section, name, "not yet produced")
        return
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    fmt = (lambda v: f"{v:.4f}") if isinstance(want, float) else str
    record("PASS" if ok else "FAIL", section, name,
           f"{fmt(got)}" + ("" if ok else f"  EXPECTED {fmt(want)}"))


def same(section, name, got, want):
    ok = got == want
    record("PASS" if ok else "FAIL", section, name,
           f"{got}" + ("" if ok else f"  EXPECTED {want}"))


def read(path):
    p = Path(path)
    if not p.exists():
        return None
    with p.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_categoriser():
    spec = importlib.util.spec_from_file_location("c2", ROOT / "scripts" / "14_Categorize_v2.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


c2 = load_categoriser()


def section(title):
    print(f"\n===== {title} =====")


# ----------------------------------------------------------------------- 1 corpus
section("Corpus")
tr = read(EXP / "species_descriptions_treatments.csv")
same("corpus", "unique treatments", len(tr), E_CORPUS["treatments"])
same("corpus", "with description",
     sum(1 for r in tr if (r.get("has_description") or "").upper() in ("TRUE", "1", "YES")),
     E_CORPUS["with_description"])
same("corpus", "species_id unique", len({r["species_id"] for r in tr}), len(tr))

# ---------------------------------------------------------------------- 2 ecology
section("Ecology sets")
prim = read(EXP / "expansion/step05b_outputs/species_color_environment_final_expanded.csv")
same("ecology", "primary n", len(prim), E_ECOLOGY["primary_n"])
same("ecology", "primary colours", dict(Counter(r["color_group"] for r in prim)), E_ECOLOGY["primary"])
clean = read(EXP / "step05b_outputs_clean/species_color_environment_final_clean.csv")
same("ecology", "clean n", len(clean), E_ECOLOGY["clean_n"])
same("ecology", "clean colours", dict(Counter(r["color_group"] for r in clean)), E_ECOLOGY["clean"])

# ------------------------------------------------------------- 3 gold + benchmark
section("Gold set / RQ1 / RQ3")
gold = read(EXP / "gold_set_labeled.csv")
same("gold", "template rows", len(gold), E_GOLD["template"])
gmap = {r["species_id"]: c2.to_class(r["gold_category"])
        for r in gold if (r["gold_category"] or "").strip()}
same("gold", "labelled rows", len(gmap), E_GOLD["labelled"])
dis = read(EXP / "rq2_outputs/gold_disagreements_by_error_class.csv")
junk = {r["species_id"] for r in dis if r["error_class"] == "JUNK_NON_SPECIES"}
same("gold", "junk species", len(junk), E_GOLD["junk"])
same("gold", "n=89 subset", len(gmap) - len(junk), E_GOLD["n89"])

PRED_FILES = {"baseline": "benchmark/gold_pred_baseline.csv",
              "qwen7b": "benchmark/gold_pred_qwen7b_full.csv",
              "qwen72b": "benchmark/gold_pred_qwen72b.csv",
              "llama70b": "benchmark/gold_pred_llama70b.csv",
              "qwen7b_rag": "rq3_outputs/gold_pred_qwen7b_rag.csv"}


def preds(key):
    rows = read(EXP / PRED_FILES[key])
    return {r["species_id"]: (r.get("flower_color_free_text") or "") for r in rows}


def classify(text, v2, is_rag):
    if is_rag and "uncertain" in (text or "").lower():
        return "UNKNOWN"
    return (c2.categorize_v2 if v2 else c2.categorize_v1)(text)


def accuracy(pmap, v2, is_rag, exclude=frozenset()):
    ids = [s for s in gmap if s in pmap and s not in exclude]
    hits = sum(gmap[s] == c2.to_class(classify(pmap[s], v2, is_rag)) for s in ids)
    return len(ids), hits / len(ids)


for model, (v1, v2, v1_89, v2_89, n_exp) in E_BENCH.items():
    pmap = preds(model)
    is_rag = model.endswith("_rag")
    n, a1 = accuracy(pmap, False, is_rag)
    _, a2 = accuracy(pmap, True, is_rag)
    _, a3 = accuracy(pmap, False, is_rag, junk)
    _, a4 = accuracy(pmap, True, is_rag, junk)
    same("rq1", f"{model} n scored", n, n_exp)
    eq("rq1", f"{model} v1", a1, v1)
    eq("rq3", f"{model} v2", a2, v2)
    eq("rq3", f"{model} v1 n=89", a3, v1_89)
    eq("rq3", f"{model} v2 n=89", a4, v2_89)


def kappa(pmap):
    ids = [s for s in gmap if s in pmap]
    yt = [gmap[s] for s in ids]
    yp = [c2.to_class(c2.categorize_v1(pmap[s])) for s in ids]
    n = len(ids)
    acc = sum(a == b for a, b in zip(yt, yp)) / n
    ct, cp = Counter(yt), Counter(yp)
    pe = sum((ct[k] / n) * (cp[k] / n) for k in set(ct) | set(cp))
    return (acc - pe) / (1 - pe)


for model, k in E_KAPPA.items():
    eq("rq1", f"{model} kappa", kappa(preds(model)), k)

section("RAG behaviour")
rag = preds("qwen7b_rag")
abst = [s for s, v in rag.items() if "uncertain" in v.lower()]
same("rag", "abstentions", len(abst), E_RAG["abstentions"])
same("rag", "abstain on junk", sum(1 for s in abst if s in junk), E_RAG["abstain_junk"])
genuine = [s for s in abst if s not in junk]
same("rag", "abstain on genuine", len(genuine), E_RAG["abstain_genuine"])
same("rag", "genuine abstentions all gold=UNKNOWN",
     all(gmap.get(s) == "UNKNOWN" for s in genuine), True)
zs = preds("qwen7b")
differ = fixes = breaks = 0
for s in [x for x in gmap if x in zs and x in rag and x not in junk]:
    a = c2.to_class(classify(zs[s], True, False))
    b = c2.to_class(classify(rag[s], True, True))
    if a != b:
        differ += 1
        fixes += (b == gmap[s] and a != gmap[s])
        breaks += (a == gmap[s] and b != gmap[s])
same("rag", "differ vs zero-shot", differ, E_RAG["vs_zeroshot_differ"])
same("rag", "RAG fixes", fixes, E_RAG["rag_fixes"])
same("rag", "RAG breaks", breaks, E_RAG["rag_breaks"])

section("RQ2 error taxonomy")
same("rq2", "qwen7b breakdown",
     dict(Counter(r["error_class"] for r in dis if r["model"] == "qwen7b")), E_RQ2_QWEN7B)

# -------------------------------------------------------------------------- RQ4
section("RQ4 label sensitivity")
for variant, n in E_RQ4_N.items():
    same("rq4", f"{variant} n", len(read(EXP / f"wp4_label_variants/species_color_environment_{variant}.csv")), n)
conv = read(EXP / "wp4_label_variants/results/wp4_convergence.csv")
mp = max(float(r["mpsrf"]) for r in conv)
record("PASS" if mp < 1.01 else "FAIL", "rq4", "max MPSRF < 1.01", f"{mp:.5f}")
same("rq4", "chain files", len(list((EXP / "wp4_label_variants/mcmc_chains").glob("*.rds"))), 36)
fx = read(EXP / "wp4_label_variants/results/wp4_fixed_effects_all_variants.csv")
fidx = {(r["variant"], r["color"], r["variable"]): r for r in fx}
for variant, (wm, wp, ym, yp) in E_RQ4_PC2.items():
    eq("rq4", f"{variant} WHITE~PC2", float(fidx[(variant, "WHITE", "PC2")]["post_mean"]), wm, 5e-5)
    eq("rq4", f"{variant} WHITE~PC2 p", float(fidx[(variant, "WHITE", "PC2")]["pMCMC"]), wp, 1e-4)
    eq("rq4", f"{variant} YELLOW~PC2", float(fidx[(variant, "YELLOW", "PC2")]["post_mean"]), ym, 5e-5)
    eq("rq4", f"{variant} YELLOW~PC2 p", float(fidx[(variant, "YELLOW", "PC2")]["pMCMC"]), yp, 1e-4)
sig = defaultdict(list)
for r in fx:
    if r["variable"].startswith("PC") and float(r["pMCMC"]) < 0.05:
        sig[f"{r['color']}~{r['variable']}"].append(r["variant"])
same("rq4", "significant effect set", {k: sorted(v) for k, v in sig.items()},
     {k: sorted(v) for k, v in E_RQ4_SIG.items()})

# --------------------------------------------------------------- primary ecology
section("Primary ecology MCMC (n=1,438)")
comb = read(EXP / "expansion/step06_outputs/tables/combined/all_fixed_effects_combined.csv")
cidx = {(r["color"], r["variable"]): r for r in comb}
for (colour, effect), (mean, p) in E_PRIMARY_PC.items():
    eq("ecology", f"{colour}~{effect}", float(cidx[(colour, effect)]["post.mean"]), mean, 5e-5)
    eq("ecology", f"{colour}~{effect} p", float(cidx[(colour, effect)]["pMCMC"]), p, 5e-4)
same("ecology", "significant PC effects",
     sorted(f"{r['color']}~{r['variable']}" for r in comb
            if r["variable"].startswith("PC") and float(r["pMCMC"]) < 0.05),
     sorted(f"{c}~{e}" for c, e in E_PRIMARY_PC))
same("ecology", "all eff.samp >= 1000",
     all(float(r["eff.samp"]) >= 1000 for r in comb), True)

section("Primary elevation")
elev = read(EXP / "expansion/step08_outputs/elevation_mcmc_results.csv")
eidx = {(r["color"], r["variable"]): r for r in elev}
for colour, (mean, p) in E_ELEV.items():
    eq("elevation", f"{colour} alt_scaled", float(eidx[(colour, 'alt_scaled')]["mean"]), mean, 1e-3)
    eq("elevation", f"{colour} p", float(eidx[(colour, 'alt_scaled')]["pMCMC"]), p, 1e-3)


def parse_chisq(path):
    p = Path(path)
    if not p.exists():
        return None, None
    import re
    t = p.read_text()
    m = re.search(r"X-squared\s*=\s*([\d.]+).*?p-value\s*=\s*([\d.e-]+)", t, re.S)
    return (float(m.group(1)), float(m.group(2))) if m else (None, None)


x2, pv = parse_chisq(EXP / "expansion/step08_outputs/elevation_chisq_test.txt")
eq("elevation", "chi-square X2", x2, E_ELEV_CHISQ[0], 0.01)
eq("elevation", "chi-square p", pv, E_ELEV_CHISQ[1], 1e-5)

# ----------------------------------------------------- clean n=1,174 (regenerated)
section("Clean n=1,174 comparison set")
cc = read(EXP / "step06_outputs_clean/tables/combined/all_fixed_effects_combined.csv")
if cc is None:
    record("PEND", "clean", "step06_outputs_clean", "not yet regenerated (job 48203773)")
else:
    ccidx = {(r["color"], r["variable"]): r for r in cc}
    for (colour, effect), mean in E_CLEAN_PC.items():
        row = ccidx.get((colour, effect))
        eq("clean", f"{colour}~{effect}", float(row["post.mean"]) if row else None, mean, 0.01)
ce = read(EXP / "step08_outputs_clean/elevation_mcmc_results.csv")
if ce is None:
    record("PEND", "clean", "step08_outputs_clean", "not yet regenerated (job 48203773)")
else:
    ceidx = {(r["color"], r["variable"]): r for r in ce}
    for colour, mean in E_CLEAN_ELEV.items():
        row = ceidx.get((colour, "alt_scaled"))
        eq("clean", f"{colour} alt_scaled", float(row["mean"]) if row else None, mean, 0.02)
cx2, cpv = parse_chisq(EXP / "step08_outputs_clean/elevation_chisq_test.txt")
if cx2 is None:
    record("PEND", "clean", "clean chi-square", "not yet regenerated")
else:
    eq("clean", "clean chi-square X2", cx2, E_CLEAN_CHISQ[0], 0.01)
    eq("clean", "clean chi-square p", cpv, E_CLEAN_CHISQ[1], 1e-5)

# ------------------------------------------------------------------- reliability
section("Reliability chapter")
summ = json.loads((REL / "summary.json").read_text())
# published only under Results/tables/reliability/
agree = read(ROOT / "Results/tables/reliability/agreement_validation_table.csv")
aidx = {r["quantity"]: r for r in agree}
FUNNEL_KEYS = {"primary_ecology": "primary_ecology",
               "three_llm_coverage": "three_llm_coverage",
               "common_known_support": "common_known_support",
               "high_confidence": "high_confidence",
               "disagreement": "disagreement",
               "unsupported_known_colour": "unsupported",
               "wrong_context_evidence": "wrong_context"}
for csv_key, exp_key in FUNNEL_KEYS.items():
    same("reliability", csv_key, int(aidx[csv_key]["n"]), E_FUNNEL[exp_key])
eq("reliability", "agreement rate", float(aidx["agreement_rate_on_coverage_known"]["n"]),
   E_FUNNEL["agreement_rate"])
same("reliability", "high + disagree = common",
     summ["high_confidence_n"] + summ["disagreement_n"] == summ["common_known_support_n"], True)
common_csv = read(REL / "ecology_common_known.csv")
high_csv = read(REL / "ecology_high_confidence.csv")
same("reliability", "common_known rows", len(common_csv), E_FUNNEL["common_known_support"])
same("reliability", "high_confidence rows", len(high_csv), E_FUNNEL["high_confidence"])
same("reliability", "no UNKNOWN leaked into ecology subsets",
     all(r["color_group"] in ("WHITE", "YELLOW", "REDTYPE") for r in common_csv + high_csv), True)

# 7B text must still be the original extract, not an expansion overwrite
s2b = {r["species_id"]: " ".join((r.get("binomial") or "").lower().split()) for r in tr}
orig = {}
for r in read(EXP / "flower_color_qwen_clean.csv"):
    b = s2b.get(r.get("species_id", ""))
    if b:
        orig[b] = (r.get("flower_color_free_text") or "").strip()
relrows = read(REL / "species_reliability.csv")
same("reliability", "7B text = original extract (overwrite bug)",
     sum(1 for r in relrows
         if orig.get(r["binomial_key"]) and r["qwen7b_free_text"].strip() != orig[r["binomial_key"]]),
     0)

eff = read(REL / "reliability_mcmc_effects.csv")
rob = read(REL / "reliability_robustness_table.csv")
same("reliability", "full chain length", sorted({r["nitt"] for r in eff}), ["1050000"])
same("reliability", "robust effects",
     sorted(r["effect"] for r in rob if r["designation"] == "robust"), E_ROBUST)
# designation / CI / direction internal consistency
eidx2 = {(r["color"], r["effect"], r["subset"]): r for r in eff}
bad = 0
for r in rob:
    colour, effect = r["effect"].split("~")
    a = eidx2[(colour, effect, "common_known")]
    b = eidx2[(colour, effect, "high_confidence")]
    same_dir = a["direction"] == b["direction"]
    both = a["excludes_zero"] == "1" and b["excludes_zero"] == "1"
    want = "robust" if (same_dir and both) else (
        "same_direction_interval_changes" if same_dir else "label-sensitive")
    bad += want != r["designation"]
    for x in (a, b):
        lo, hi, mn = float(x["lower"]), float(x["upper"]), float(x["mean"])
        bad += lo > hi
        bad += int(x["excludes_zero"]) != int(lo > 0 or hi < 0)
        bad += (mn > 0 and x["direction"] != "+") or (mn < 0 and x["direction"] != "-")
same("reliability", "designation/CI/direction consistency", bad, 0)
for (subset_name, colour, effect), mean in E_REL_EFFECTS.items():
    row = eidx2.get((colour, effect, subset_name))
    eq("reliability", f"{subset_name}/{colour}~{effect} mean",
       float(row["mean"]) if row else None, mean, 1e-5)

# convergence diagnostics (added by the 3-chain rerun)
cvg = read(REL / "reliability_convergence.csv")
if cvg is None:
    record("PEND", "reliability", "convergence diagnostics",
           "not yet produced (job 48203984 - 3-chain rerun)")
else:
    same("reliability", "convergence rows", len(cvg), 12)
    same("reliability", "chains per model", sorted({r["n_chains"] for r in cvg}), ["3"])
    worst = max(float(r["mpsrf"]) for r in cvg)
    record("PASS" if worst < 1.01 else "FAIL", "reliability",
           "max MPSRF < 1.01", f"{worst:.6f}")
    same("reliability", "all models converged",
         all(r["converged"] == "1" for r in cvg), True)
    least = min(float(r["eff_samp"]) for r in cvg)
    record("PASS" if least >= 1000 else "FAIL", "reliability",
           "min pooled ESS >= 1000", f"{least:.0f}")

# -------------------------------------------------------------------- prediction
section("Prediction task")
meta = json.loads((EXP / "prediction_outputs/prediction_run_metadata.json").read_text())
same("prediction", "n_species", meta["n_species"], E_PRED["n_species"])
same("prediction", "n_genera", meta["n_genera"], E_PRED["n_genera"])
pcv = read(EXP / "prediction_outputs/prediction_cv_summary.csv")
gidx = {(r["cv"], r["model"]): r for r in pcv}
for model in ("majority", "logreg", "random_forest"):
    a, b, f = E_PRED[model]
    row = gidx[("genus-grouped", model)]
    eq("prediction", f"{model} accuracy", float(row["accuracy"]), a)
    eq("prediction", f"{model} balanced acc", float(row["balanced_accuracy"]), b)
    eq("prediction", f"{model} macro F1", float(row["macro_f1"]), f)
gp = float(gidx[("ungrouped (leaky)", "genus_prior")]["macro_f1"])
eq("prediction", "genus prior macro F1", gp, E_PRED["genus_prior_macro_f1"])
floor = float(gidx[("genus-grouped", "majority")]["macro_f1"])
envf = float(gidx[("genus-grouped", "random_forest")]["macro_f1"])
eq("prediction", "genus-vs-env ratio", (gp - floor) / (envf - floor), E_PRED["ratio"], 0.05)
pi = read(EXP / "prediction_outputs/prediction_permutation_importance.csv")
pos = [r["variable"] for r in pi if float(r["importance_mean"]) > 0]
same("prediction", "only positive-importance axis", pos, [E_PRED["only_positive_axis"]])

# ----------------------------------------------------------------------- figures
section("Figures present")
missing = [f for f in FIGURES if not (ROOT / "Results/figures" / f).exists()]
same("figures", "all expected figures exist", missing, [])
for f in FIGURES:
    p = ROOT / "Results/figures" / f
    if p.exists() and p.stat().st_size < 5000:
        record("FAIL", "figures", f"{f} suspiciously small", f"{p.stat().st_size} bytes")

# ------------------------------------------------------------------------ summary
print("\n" + "=" * 78)
n_pass = sum(1 for r in RESULTS if r[0] == "PASS")
n_fail = sum(1 for r in RESULTS if r[0] == "FAIL")
n_pend = sum(1 for r in RESULTS if r[0] == "PEND")
print(f"AUDIT SUMMARY   PASS={n_pass}   FAIL={n_fail}   PENDING={n_pend}")
if n_fail:
    print("\nFAILURES:")
    for status, sec, name, detail in RESULTS:
        if status == "FAIL":
            print(f"  [{sec}] {name}: {detail}")
if n_pend:
    print("\nPENDING (in-flight reruns):")
    for status, sec, name, detail in RESULTS:
        if status == "PEND":
            print(f"  [{sec}] {name}: {detail}")
print("=" * 78)
sys.exit(1 if n_fail else 0)
