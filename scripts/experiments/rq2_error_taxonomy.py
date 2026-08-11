#!/usr/bin/env python3
"""
RQ2 — Error taxonomy for flower-colour extraction.

Produces:
  1. Gold-set disagreement table (human vs each model) with error-class labels
  2. Corpus-level prevalence of data-noise modes in treatments
  3. A short markdown summary for Chapter 5

Error classes (mutually assigned by priority rules below):
  CATEGORY_PRIORITY   — free-text is roughly right, but keyword priority
                        (WHITE before REDTYPE, YELLOW before RED, etc.)
                        flips the coarse class vs human judgment
  MULTI_COLOUR        — genuine multi-colour / "or" / "tinged" ambiguity
  CONTAMINATION       — block swallows another species/family's text
  FRUIT_BERRY_COLOR   — colour taken from fruit/berry, not flower
  INDUMENT_TEXTURE    — colour word attached to hair/tomentum, not pigment
  FALSE_POSITIVE      — model invents a colour; gold says UNKNOWN
  FALSE_NEGATIVE      — model says no colour; gold has a colour
  JUNK_NON_SPECIES    — genus header / key stub / non-treatment
  OTHER_MISMATCH      — residual disagreement

SAFE: reads experiments/ only; writes to experiments/rq2_outputs/.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from pathlib import Path

BASE = Path("/scratch/dp23301/Thesis")
EXP = BASE / "Processed Data" / "experiments"
GOLD = EXP / "gold_set_labeled.csv"
TREATMENTS = EXP / "species_descriptions_treatments.csv"
OUTDIR = EXP / "rq2_outputs"

PRED_FILES = {
    "baseline": EXP / "benchmark/gold_pred_baseline.csv",
    "qwen7b": EXP / "benchmark/gold_pred_qwen7b_full.csv",
    "qwen72b": EXP / "benchmark/gold_pred_qwen72b.csv",
    "llama70b": EXP / "benchmark/gold_pred_llama70b.csv",
}

csv.field_size_limit(sys.maxsize)

FAM = re.compile(r"\b([A-Z]{6,}ACEAE)\b")
END = re.compile(r"(Distrib\.|Cultivated|Endemic\.)")
FRUIT = re.compile(r"\b(berr(?:y|ies)|drupe|fruit|aril)\b", re.I)
FLORAL = re.compile(r"\b(flower|petal|corolla|perianth|tepal)\b", re.I)
COLOR = re.compile(
    r"\b(white|whitish|yellow|golden|red|scarlet|crimson|pink|purple|violet|blue|orange)\b",
    re.I,
)
INDUMENT = re.compile(
    r"\b(tomentose|pubescent|hairy|hirsute|villous|sericeous|woolly)\b", re.I
)
MULTI = re.compile(r"\b( or | to |tinged|variable|sometimes|rarely)\b", re.I)


def categorize(text: str) -> str:
    if not text or not text.strip():
        return "UNKNOWN"
    t = text.lower()
    if "white" in t or "whitish" in t:
        return "WHITE"
    if "yellow" in t or "golden" in t:
        return "YELLOW"
    if "pink" in t or "pinkish" in t:
        return "PINK"
    if "red" in t:  # identical to pipeline (scarlet/crimson without 'red' miss)
        return "RED"
    if "purple" in t or "purplish" in t or "violet" in t or "blue" in t:
        return "PURPLE/BLUE"
    if "greenish" in t:
        return "GREENISH"
    if "no flower colour" in t:
        return "UNKNOWN"
    return "OTHER"


def to_class(fine: str) -> str:
    f = (fine or "").strip().upper().replace(" ", "")
    if f == "WHITE":
        return "WHITE"
    if f == "YELLOW":
        return "YELLOW"
    if f in ("RED", "PINK", "PURPLE/BLUE", "PURPLEBLUE", "REDTYPE"):
        return "REDTYPE"
    if f in ("UNKNOWN", "NONE", "NA", "N/A", ""):
        return "UNKNOWN"
    return "OTHER"


def colors_in(text: str):
    return set(m.group(1).lower() for m in COLOR.finditer(text or ""))


def is_priority_artifact(gold_free: str, pred_free: str, gold_cls: str, pred_cls: str) -> bool:
    """True when both mention multiple colour words and the coarse mismatch
    is explained by WHITE/YELLOW keyword priority vs REDTYPE."""
    if gold_cls == pred_cls:
        return False
    blob = f"{gold_free} {pred_free}".lower()
    cols = colors_in(blob)
    redish = {"red", "scarlet", "crimson", "pink", "purple", "violet", "blue"}
    has_redish = bool(cols & redish)
    has_white = "white" in cols or "whitish" in cols
    has_yellow = "yellow" in cols or "golden" in cols
    # Classic: phrase has red-type + white/yellow; pipeline picks white/yellow first
    if has_redish and has_white and gold_cls == "REDTYPE" and pred_cls == "WHITE":
        return True
    if has_redish and has_yellow and gold_cls == "REDTYPE" and pred_cls == "YELLOW":
        return True
    if has_redish and has_yellow and gold_cls == "YELLOW" and pred_cls == "REDTYPE":
        # human preferred yellow; model/category preferred red — still priority-ish
        return True
    return False


def classify_error(g: dict, pred_free: str, gold_cls: str, pred_cls: str) -> str:
    if gold_cls == pred_cls:
        return "CORRECT"
    raw = g.get("raw_text_snippet", "") or ""
    gold_free = g.get("gold_free_text", "") or ""
    notes = g.get("notes", "") or ""

    if notes.startswith("AUTO-FLAG") or "genus-level" in notes.lower() or "abbreviated genus" in notes.lower():
        return "JUNK_NON_SPECIES"
    # contamination first (user notes / merged blocks) — before priority heuristics
    if "TWO DIFFERENT COLOURS" in notes.upper() or "CONTAMIN" in notes.upper() or "CORYMBOSA" in notes.upper():
        return "CONTAMINATION"
    if is_priority_artifact(gold_free, pred_free, gold_cls, pred_cls):
        return "CATEGORY_PRIORITY"
    # contamination: family header after Distrib
    fams = FAM.findall(raw)
    if fams:
        from collections import Counter as C
        counts = C(fams)
        for fam, c in counts.items():
            if c == 1:
                pos = raw.find(fam)
                if pos > 50 and END.search(raw[max(0, pos - 80):pos]) and len(raw) - pos > 150:
                    return "CONTAMINATION"
    # fruit/berry without nearby floral colour for the predicted colour
    if FRUIT.search(raw) and pred_cls != "UNKNOWN":
        # if gold UNKNOWN and fruit has colour → fruit confusion
        if gold_cls == "UNKNOWN":
            return "FRUIT_BERRY_COLOR"
    if gold_cls == "UNKNOWN" and pred_cls != "UNKNOWN":
        return "FALSE_POSITIVE"
    if gold_cls != "UNKNOWN" and pred_cls == "UNKNOWN":
        return "FALSE_NEGATIVE"
    if MULTI.search(gold_free) or MULTI.search(pred_free) or MULTI.search(raw[:500]):
        return "MULTI_COLOUR"
    if INDUMENT.search(raw) and ("white" in pred_free.lower() or "white" in gold_free.lower()):
        return "INDUMENT_TEXTURE"
    return "OTHER_MISMATCH"


def load_preds():
    out = {}
    for name, path in PRED_FILES.items():
        with open(path, encoding="utf-8-sig") as f:
            out[name] = {r["species_id"]: r.get("flower_color_free_text", "")
                         for r in csv.DictReader(f)}
    return out


def gold_disagreement_table(preds):
    with open(GOLD, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    out_rows = []
    for r in rows:
        if not (r.get("gold_category") or "").strip():
            continue
        gold_cls = to_class(r["gold_category"])
        sid = r["species_id"]
        for model, pmap in preds.items():
            pfree = pmap.get(sid, "")
            pred_cls = to_class(categorize(pfree))
            err = classify_error(r, pfree, gold_cls, pred_cls)
            if err == "CORRECT":
                continue
            out_rows.append({
                "species_id": sid[:120],
                "stratum": r.get("stratum", ""),
                "model": model,
                "gold_class": gold_cls,
                "pred_class": pred_cls,
                "gold_free_text": (r.get("gold_free_text") or "")[:200],
                "pred_free_text": (pfree or "")[:200],
                "error_class": err,
                "notes": (r.get("notes") or "")[:200],
            })
    return out_rows


def corpus_prevalence():
    """Scan all treatments for data-noise signatures (not gold-only)."""
    with open(TREATMENTS, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    n = len(rows)
    counts = Counter()
    examples = {k: [] for k in [
        "cross_family_contamination", "fruit_near_color",
        "truncated_epithet_suspect", "zero_O_boundary",
    ]}

    zero_O = re.compile(r"\d+\.0[a-z]{3,}")
    trunc = re.compile(r"^[a-z]{3,}$")  # checked on epithet

    for r in rows:
        txt = r.get("raw_text", "") or ""
        ep = (r.get("epithet") or "").strip()
        binom = r.get("binomial", "")

        # contamination
        fams = FAM.findall(txt)
        if fams:
            from collections import Counter as C
            counts_f = C(fams)
            for fam, c in counts_f.items():
                if c >= 2:
                    continue
                pos = txt.find(fam)
                if pos > 50 and END.search(txt[max(0, pos - 80):pos]) and len(txt) - pos > 150:
                    counts["cross_family_contamination"] += 1
                    if len(examples["cross_family_contamination"]) < 8:
                        examples["cross_family_contamination"].append(binom)
                    break

        # fruit colour mention
        if FRUIT.search(txt) and COLOR.search(txt):
            # sentence-level: fruit ... color without flower in same window
            for m in FRUIT.finditer(txt):
                win = txt[max(0, m.start() - 40): m.end() + 60]
                if COLOR.search(win) and not FLORAL.search(win):
                    counts["fruit_near_color"] += 1
                    if len(examples["fruit_near_color"]) < 8:
                        examples["fruit_near_color"].append(binom)
                    break

        if zero_O.search(txt):
            counts["zero_O_boundary"] += 1
            if len(examples["zero_O_boundary"]) < 8:
                examples["zero_O_boundary"].append(binom)

        # truncated epithet heuristic: short, no typical Latin ending
        if ep and trunc.match(ep) and not re.search(r"[aeious]$", ep) and len(ep) <= 8:
            counts["truncated_epithet_suspect"] += 1
            if len(examples["truncated_epithet_suspect"]) < 8:
                examples["truncated_epithet_suspect"].append(f"{binom}")

    return n, counts, examples


def write_summary(disagree_rows, n_treat, corpus_counts, examples, preds):
    # per-model error class counts
    by_model = {}
    for model in PRED_FILES:
        sub = [r for r in disagree_rows if r["model"] == model]
        by_model[model] = Counter(r["error_class"] for r in sub)

    # primary model focus: qwen7b
    q7 = [r for r in disagree_rows if r["model"] == "qwen7b"]
    q7c = Counter(r["error_class"] for r in q7)

    lines = []
    lines.append("# RQ2 — Error Taxonomy Summary\n")
    lines.append("## 1. Gold-set disagreements (vs human labels, n=98 labelled)\n")
    lines.append("| Model | # disagreements | Accuracy |")
    lines.append("|---|---:|---:|")
    # accuracy from earlier scoring
    acc = {"baseline": 0.763, "qwen7b": 0.878, "qwen72b": 0.878, "llama70b": 0.857}
    for m in PRED_FILES:
        n_wrong = sum(1 for r in disagree_rows if r["model"] == m)
        lines.append(f"| {m} | {n_wrong} | {acc.get(m, float('nan')):.3f} |")

    lines.append("\n## 2. Qwen-7B error-class breakdown (primary model)\n")
    lines.append("| Error class | Count | Meaning |")
    lines.append("|---|---:|---|")
    meanings = {
        "CATEGORY_PRIORITY": "Free text OK; WHITE/YELLOW keyword priority overrides REDTYPE",
        "MULTI_COLOUR": "Ambiguous multi-colour / or / tinged phrasing",
        "CONTAMINATION": "Parser merged another species/family into the block",
        "FRUIT_BERRY_COLOR": "Colour taken from fruit/berry, not flower",
        "FALSE_POSITIVE": "Model invents a colour; gold = UNKNOWN",
        "FALSE_NEGATIVE": "Model misses a colour; gold has one",
        "JUNK_NON_SPECIES": "Genus header / key stub (not a real species treatment)",
        "INDUMENT_TEXTURE": "Indument/texture colour confused with pigment",
        "OTHER_MISMATCH": "Residual",
    }
    for cls, n in q7c.most_common():
        lines.append(f"| {cls} | {n} | {meanings.get(cls, '')} |")
    lines.append(f"\n**Total Qwen-7B disagreements:** {sum(q7c.values())} / 98\n")

    # how many are "real LLM errors" vs pipeline/data
    real_llm = {"FALSE_POSITIVE", "FALSE_NEGATIVE", "FRUIT_BERRY_COLOR", "OTHER_MISMATCH", "INDUMENT_TEXTURE"}
    structural = {"CATEGORY_PRIORITY", "JUNK_NON_SPECIES", "CONTAMINATION", "MULTI_COLOUR"}
    n_real = sum(q7c[c] for c in real_llm)
    n_struct = sum(q7c[c] for c in structural)
    lines.append(
        f"Of these, **{n_struct}** are largely structural/priority/data issues "
        f"(not pure LLM failures), and **{n_real}** look like genuine extraction mistakes.\n"
    )

    lines.append("## 3. All-model error-class counts\n")
    classes = sorted({r["error_class"] for r in disagree_rows})
    header = "| Error class | " + " | ".join(PRED_FILES) + " |"
    lines.append(header)
    lines.append("|---|" + "|".join(["---:"] * len(PRED_FILES)) + "|")
    for cls in classes:
        cells = [str(by_model[m].get(cls, 0)) for m in PRED_FILES]
        lines.append(f"| {cls} | " + " | ".join(cells) + " |")

    lines.append("\n## 4. Corpus-level data-noise prevalence "
                 f"(n={n_treat} treatments)\n")
    lines.append("| Signature | Count | % of treatments | Examples |")
    lines.append("|---|---:|---:|---|")
    for key in ["cross_family_contamination", "fruit_near_color",
                "zero_O_boundary", "truncated_epithet_suspect"]:
        c = corpus_counts.get(key, 0)
        ex = ", ".join(examples.get(key, [])[:3]) or "—"
        lines.append(f"| {key} | {c} | {100*c/n_treat:.2f}% | {ex} |")

    lines.append("\n## 5. Implications for RAG (RQ3)\n")
    lines.append(
        "- **CATEGORY_PRIORITY** errors are fixed by changing the categoriser "
        "(e.g. prefer REDTYPE when a red-family word co-occurs), not by RAG.\n"
        "- **CONTAMINATION / JUNK** need better parsing or retrieval of a clean "
        "treatment boundary — RAG can help if retrieval returns the right block.\n"
        "- **FRUIT_BERRY / FALSE_POSITIVE** are prompt/RAG targets: retrieve "
        "exemplars that distinguish floral vs fruit colour.\n"
        "- **MULTI_COLOUR** benefits from few-shot exemplars with an explicit "
        "primary-colour rule.\n"
    )
    lines.append("\n*Generated by scripts/experiments/rq2_error_taxonomy.py*\n")
    return "\n".join(lines)


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    preds = load_preds()
    disagree = gold_disagreement_table(preds)

    disagree_path = OUTDIR / "gold_disagreements_by_error_class.csv"
    with open(disagree_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(disagree[0].keys()))
        w.writeheader()
        w.writerows(disagree)
    print(f"Wrote {len(disagree)} disagreement rows -> {disagree_path}")

    n_treat, corpus_counts, examples = corpus_prevalence()
    prev_path = OUTDIR / "corpus_noise_prevalence.csv"
    with open(prev_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["signature", "count", "pct", "examples"])
        w.writeheader()
        for key, c in corpus_counts.most_common():
            w.writerow({
                "signature": key, "count": c,
                "pct": round(100 * c / n_treat, 3),
                "examples": "; ".join(examples.get(key, [])),
            })
    print(f"Wrote prevalence -> {prev_path}")

    summary = write_summary(disagree, n_treat, corpus_counts, examples, preds)
    sum_path = OUTDIR / "RQ2_Error_Taxonomy_Summary.md"
    sum_path.write_text(summary, encoding="utf-8")
    print(f"Wrote summary -> {sum_path}")
    print("\n" + summary)


if __name__ == "__main__":
    main()
