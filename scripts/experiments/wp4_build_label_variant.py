#!/usr/bin/env python3
"""
WP4 (downstream-impact) harness -- STEP 1.

Build a per-label-source analysis dataset for the sensitivity analysis:
"Do the ecological conclusions change depending on which model produced the
flower-colour labels?"

Key efficiency: the ENVIRONMENT is label-independent. Every species' PC1-PC10
scores come from GBIF occurrences + climate/soil and do NOT depend on the colour
label. So we REUSE the existing clean environment dataset and only swap in each
model's colour assignment. No GBIF/rasters/PCA re-run needed.

For a given model's treatment-level predictions we:
  1. categorise the predicted free text (same rule as the pipeline),
  2. group RED/PINK/PURPLE-BLUE -> REDTYPE,
  3. map species_id -> binomial via the treatments file,
  4. join onto the clean environment dataset by binomial (== query_name),
  5. KEEP species this source gives a known colour; DROP species it calls
     UNKNOWN/OTHER (exactly as the real pipeline drops unknown-colour species),
  6. write a dataset with the SAME PC columns but this source's colour_group.

Output feeds the MCMCglmm job array (06_MCMCglmm_array.R).

Usage
-----
  python wp4_build_label_variant.py \
      --preds "Processed Data/experiments/benchmark/treatments_pred_baseline.csv" \
      --variant baseline
"""

import argparse
import csv
import sys
from pathlib import Path

BASE = Path("/scratch/dp23301/Thesis")
EXP = BASE / "Processed Data" / "experiments"
TREATMENTS = EXP / "species_descriptions_treatments.csv"
ENV = EXP / "step05b_outputs_clean" / "species_color_environment_final_clean.csv"
OUTDIR = EXP / "wp4_label_variants"

csv.field_size_limit(sys.maxsize)

PC_COLS = [f"PC{i}" for i in range(1, 11)]


def categorize_color(text: str) -> str:
    if not text or text.strip() == "":
        return "UNKNOWN"
    t = text.lower()
    if "white" in t or "whitish" in t:
        return "WHITE"
    if "yellow" in t or "golden" in t or "pale yellow" in t or "bright yellow" in t:
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


def to_group(cat: str):
    if cat == "WHITE":
        return "WHITE"
    if cat == "YELLOW":
        return "YELLOW"
    if cat in ("RED", "PINK", "PURPLE/BLUE"):
        return "REDTYPE"
    return None  # UNKNOWN / OTHER / GREENISH -> dropped (no known colour)


def resolve(p: str) -> Path:
    q = Path(p)
    return q if q.is_absolute() else BASE / q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds", required=True,
                    help="treatments predictions CSV (species_id, flower_color_free_text)")
    ap.add_argument("--variant", required=True, help="short name, e.g. baseline/qwen7b/qwen72b")
    args = ap.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)

    # species_id -> binomial
    with open(TREATMENTS, encoding="utf-8") as f:
        sid_to_binomial = {r["species_id"]: r["binomial"].strip()
                           for r in csv.DictReader(f)}

    # binomial -> colour_group under THIS source
    preds_path = resolve(args.preds)
    with open(preds_path, encoding="utf-8-sig") as f:
        preds = list(csv.DictReader(f))
    binom_group = {}
    for r in preds:
        sid = r.get("species_id", "")
        binom = sid_to_binomial.get(sid)
        if not binom:
            continue
        grp = to_group(categorize_color(r.get("flower_color_free_text", "")))
        if grp:
            binom_group[binom] = grp

    # join onto the environment dataset (PC scores reused)
    with open(ENV, encoding="utf-8") as f:
        env_rows = list(csv.DictReader(f))

    out_rows = []
    n_in_env = len(env_rows)
    n_kept = n_dropped_unknown = n_flipped = 0
    for r in env_rows:
        binom = r["query_name"].strip()
        grp = binom_group.get(binom)
        if grp is None:
            n_dropped_unknown += 1
            continue  # this source gives no known colour -> excluded
        if grp != r["color_group"]:
            n_flipped += 1
        out = {"query_name": binom, "color_group": grp}
        for c in PC_COLS:
            out[c] = r[c]
        out["n_records"] = r["n_records"]
        out["is_white"] = 1 if grp == "WHITE" else 0
        out["is_yellow"] = 1 if grp == "YELLOW" else 0
        out["is_redtype"] = 1 if grp == "REDTYPE" else 0
        out_rows.append(out)
        n_kept += 1

    out_path = OUTDIR / f"species_color_environment_{args.variant}.csv"
    fields = ["query_name", "color_group"] + PC_COLS + \
             ["n_records", "is_white", "is_yellow", "is_redtype"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)

    from collections import Counter
    dist = Counter(r["color_group"] for r in out_rows)
    print(f"Variant '{args.variant}':")
    print(f"  env species available        : {n_in_env}")
    print(f"  kept (known colour here)      : {n_kept}")
    print(f"  dropped (unknown/other here)  : {n_dropped_unknown}")
    print(f"  colour FLIPPED vs Qwen-7B base: {n_flipped}")
    print(f"  distribution                  : {dict(dist)}")
    print(f"  wrote                         : {out_path}")


if __name__ == "__main__":
    main()
