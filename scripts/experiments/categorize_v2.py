#!/usr/bin/env python3
"""
Improved colour categoriser (RQ3).

Problem diagnosed in RQ2: the original keyword priority
  WHITE > YELLOW > PINK > RED > PURPLE/BLUE
mis-labels multi-colour phrases such as
  "flowers pinkish or white"  -> WHITE  (gold: REDTYPE)
  "brilliant scarlet, yellow in centre" -> YELLOW  (gold: REDTYPE)
because WHITE/YELLOW are checked before red-family words, and "scarlet"
does not contain the substring "red".

Fix: take the FIRST colour word mentioned in the free-text phrase as the
primary colour (botanical descriptions usually lead with the dominant
pigment), with an expanded synonym list (scarlet/crimson/etc.).

Usage (re-score existing free-text predictions, no GPU needed):
  python categorize_v2.py --rescore
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

BASE = Path("/scratch/dp23301/Thesis")
EXP = BASE / "Processed Data" / "experiments"
GOLD = EXP / "gold_set_labeled.csv"
OUTDIR = EXP / "rq3_outputs"

# ordered list of (regex, fine_category)
# first match in left-to-right text order wins
COLOUR_PATTERNS = [
    (r"whitish|white", "WHITE"),
    (r"yellowish|yellow|golden", "YELLOW"),
    (r"pinkish|pink", "PINK"),
    (r"scarlet|crimson|reddish|\bred\b", "RED"),
    (r"purplish|purple|violet|bluish|\bblue\b", "PURPLE/BLUE"),
    (r"orange", "OTHER"),
    (r"greenish|\bgreen\b", "GREENISH"),
    (r"cream", "OTHER"),
]

# Combined regex with named finding of earliest span
_COMBINED = re.compile(
    "|".join(f"(?P<c{i}>{pat})" for i, (pat, _) in enumerate(COLOUR_PATTERNS)),
    re.I,
)
_IDX_TO_CAT = {i: cat for i, (_, cat) in enumerate(COLOUR_PATTERNS)}


def categorize_v1(text: str) -> str:
    """Original pipeline categoriser (for comparison)."""
    if not text or not text.strip():
        return "UNKNOWN"
    t = text.lower()
    if "white" in t or "whitish" in t:
        return "WHITE"
    if "yellow" in t or "golden" in t:
        return "YELLOW"
    if "pink" in t or "pinkish" in t:
        return "PINK"
    if "red" in t:
        return "RED"
    if "purple" in t or "purplish" in t or "violet" in t or "blue" in t:
        return "PURPLE/BLUE"
    if "greenish" in t:
        return "GREENISH"
    if "no flower colour" in t:
        return "UNKNOWN"
    return "OTHER"


def categorize_v2(text: str) -> str:
    """First-mentioned colour word wins; expanded synonyms.

    Compound modifiers are normalised first so that
    'greenish-white' / 'yellowish-white' / 'cream-white' count as WHITE,
    and 'greenish-yellow' / 'pale yellow' count as YELLOW — matching
    botanical usage and the gold labels.
    """
    if not text or not text.strip():
        return "UNKNOWN"
    t = text.strip()
    tl = t.lower()
    if "no flower colour" in tl:
        return "UNKNOWN"

    # Compound / modifier normalisation (order matters)
    tl = re.sub(
        r"\b(?:greenish|yellowish|creamy|cream|greyish|grayish|bluish|pinkish|"
        r"purplish|reddish|pale|dull|bright|dirty)[\s\-]+white\b",
        "white",
        tl,
    )
    tl = re.sub(
        r"\b(?:greenish|creamy|cream|pale|dull|bright|dirty)[\s\-]+yellow\b",
        "yellow",
        tl,
    )
    tl = re.sub(r"\bcream(?:\-?coloured|\-?colored)?\b", "yellow", tl)
    tl = re.sub(r"\borange\b", "yellow", tl)  # orange → YELLOW group (gold convention)

    m = _COMBINED.search(tl)
    if not m:
        return "OTHER" if t else "UNKNOWN"
    for i, (_, cat) in enumerate(COLOUR_PATTERNS):
        if m.group(f"c{i}"):
            return cat
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


PRED_FILES = {
    "baseline": EXP / "benchmark/gold_pred_baseline.csv",
    "qwen7b": EXP / "benchmark/gold_pred_qwen7b_full.csv",
    "qwen72b": EXP / "benchmark/gold_pred_qwen72b.csv",
    "llama70b": EXP / "benchmark/gold_pred_llama70b.csv",
}


def score(pred_map, gold, categorizer):
    ids = [sid for sid in gold if sid in pred_map]
    y_true = [gold[sid] for sid in ids]
    y_pred = [to_class(categorizer(pred_map[sid])) for sid in ids]
    n = len(ids)
    correct = sum(a == b for a, b in zip(y_true, y_pred))
    acc = correct / n if n else 0.0
    # macro-F1 + kappa
    classes = ["WHITE", "YELLOW", "REDTYPE", "UNKNOWN", "OTHER"]
    f1s = []
    for c in classes:
        tp = sum(a == c and b == c for a, b in zip(y_true, y_pred))
        fp = sum(a != c and b == c for a, b in zip(y_true, y_pred))
        fn = sum(a == c and b != c for a, b in zip(y_true, y_pred))
        support = sum(a == c for a in y_true)
        if support == 0:
            continue
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if (prec + rec) else 0.0)
    macro = sum(f1s) / len(f1s) if f1s else 0.0
    po = acc
    labels = set(y_true) | set(y_pred)
    pe = 0.0
    for c in labels:
        pe += (sum(a == c for a in y_true) / n) * (sum(b == c for b in y_pred) / n)
    kappa = (po - pe) / (1 - pe) if (1 - pe) else 0.0
    return dict(n=n, accuracy=acc, macro_f1=macro, kappa=kappa,
                n_wrong=n - correct)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rescore", action="store_true")
    args = ap.parse_args()

    if not args.rescore:
        # quick self-checks
        cases = [
            ("flowers pinkish or white", "PINK"),
            ("flowers brilliant scarlet, yellow in centre", "RED"),
            ("corolla mostly yellow with a dark purple centre", "YELLOW"),
            ("petals violet", "PURPLE/BLUE"),
            ("no flower colour mentioned", "UNKNOWN"),
            ("flowers white", "WHITE"),
        ]
        print("Self-check categorize_v2:")
        for text, expect in cases:
            got = categorize_v2(text)
            ok = "OK" if got == expect else "FAIL"
            print(f"  [{ok}] {text!r} -> {got} (expect {expect})")
        return

    OUTDIR.mkdir(parents=True, exist_ok=True)
    with open(GOLD, encoding="utf-8-sig") as f:
        gold_rows = list(csv.DictReader(f))
    gold = {r["species_id"]: to_class(r["gold_category"])
            for r in gold_rows if (r.get("gold_category") or "").strip()}

    summary = []
    for model, path in PRED_FILES.items():
        with open(path, encoding="utf-8-sig") as f:
            pred_map = {r["species_id"]: r.get("flower_color_free_text", "")
                        for r in csv.DictReader(f)}
        s1 = score(pred_map, gold, categorize_v1)
        s2 = score(pred_map, gold, categorize_v2)
        summary.append(dict(
            model=model,
            n=s1["n"],
            acc_v1=round(s1["accuracy"], 4),
            kappa_v1=round(s1["kappa"], 4),
            wrong_v1=s1["n_wrong"],
            acc_v2=round(s2["accuracy"], 4),
            kappa_v2=round(s2["kappa"], 4),
            wrong_v2=s2["n_wrong"],
            delta_acc=round(s2["accuracy"] - s1["accuracy"], 4),
        ))
        print(f"{model:10s}  v1 acc={s1['accuracy']:.3f} (wrong={s1['n_wrong']})  "
              f"v2 acc={s2['accuracy']:.3f} (wrong={s2['n_wrong']})  "
              f"Δ={s2['accuracy']-s1['accuracy']:+.3f}")

    out = OUTDIR / "categoriser_v1_vs_v2_scores.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
