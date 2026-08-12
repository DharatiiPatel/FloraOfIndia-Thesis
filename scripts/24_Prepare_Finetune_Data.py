#!/usr/bin/env python3
"""
Supervised adaptation - STEP 1: freeze the evaluation protocol and build the
LoRA fine-tuning dataset from the human gold set.

Why this script exists
----------------------
Every method so far (zero-shot, RAG) is *prompted*: the model never learns from
the 98 human labels. LoRA fine-tuning does, which means we need a protocol that
cannot leak those labels into evaluation. This script fixes that protocol ONCE,
writes it to disk, and every later script reads it instead of re-deriving splits.

Protocol
--------
  * Evaluation universe = the 89 gold rows that are genuine species treatments.
    The 9 rows classed JUNK_NON_SPECIES by the RQ2 error taxonomy (genus
    headers, key stubs, OCR fragments) are NEVER trained on and are held out
    as a separate malformed-input set for the abstention / selective-prediction
    analysis. This matches the n=89 figures already reported.
  * 5-fold cross-validation, stratified by gold_category, seed 42. Each fold is
    predicted by a model trained only on the other four, so every one of the 89
    rows gets an out-of-fold prediction and the headline number is computed on
    exactly the same rows as the zero-shot and RAG baselines.
  * Target = gold_free_text (the free-text colour phrase), NOT the category.
    The categoriser then maps that phrase to a class exactly as it does for the
    zero-shot and RAG outputs, so the only thing that differs between methods is
    the adaptation, not the downstream mapping.
  * Prompt = byte-identical to the zero-shot extractor in
    02_Extract_Flower_Colour.py, so LoRA vs zero-shot is a clean ablation.

Caveat worth stating in the thesis: PINK has only 4 members, so it cannot be
represented in all 5 folds. This is recorded in protocol.json rather than
silently smoothed over.

  READS  : Processed Data/experiments/gold_set_labeled.csv
           Processed Data/experiments/rq2_outputs/gold_disagreements_by_error_class.csv
  WRITES : Processed Data/experiments/finetune/
             protocol.json          frozen protocol + class counts + exclusions
             folds.json             species_id -> fold assignment
             train_fold{k}.jsonl    chat-format training data (4/5 of rows)
             eval_fold{k}.jsonl     held-out rows for fold k
             eval_junk.jsonl        the 9 malformed rows (never trained on)

Usage
-----
  python 24_Prepare_Finetune_Data.py
  python 24_Prepare_Finetune_Data.py --folds 5 --seed 42
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path("/scratch/dp23301/Thesis")
EXP = BASE / "Processed Data" / "experiments"
GOLD = EXP / "gold_set_labeled.csv"
ERRORS = EXP / "rq2_outputs" / "gold_disagreements_by_error_class.csv"
OUTDIR = EXP / "finetune"

csv.field_size_limit(sys.maxsize)

# Byte-identical to 02_Extract_Flower_Colour.py so that any measured difference
# is attributable to adaptation rather than to prompt wording.
SYSTEM_MESSAGE = (
    "You are an expert botanist. Your ONLY job is to extract the flower colour "
    "from Flora of India species descriptions. "
    "Return a very short phrase like 'flowers white', 'flowers yellow with red centre', "
    "'flowers blue or purple', etc. If flower colour is not mentioned, return exactly "
    "'no flower colour mentioned'. Do NOT add explanations."
)

# The gold snippets run to ~10k characters; the extractor only ever needed the
# opening morphological text, and long inputs blow up LoRA step time for no gain.
MAX_DESC_CHARS = 3000

# 19 of the 20 UNKNOWN rows carry gold_free_text 'unknown' (one says 'flower
# colour not mentioned.'). Both are human shorthand for the notes column, not
# generation targets: neither categoriser has a rule for them, so both score as
# OTHER, and they contradict the system prompt sitting in the same training
# example. Training on them teaches the model a string it can never be scored
# correct for - the pilot duly produced invented colours on UNKNOWN rows.
# Targets for UNKNOWN rows are therefore normalised to the phrase the prompt
# demands and the scorer recognises.
CANONICAL_UNKNOWN = "no flower colour mentioned"


def user_message(description: str) -> str:
    return f"Species description:\n\n{description}\n\nWhat is the flower colour?"


def load_junk_ids() -> set[str]:
    """species_ids the RQ2 taxonomy flagged as non-species (genus headers, stubs)."""
    if not ERRORS.exists():
        raise SystemExit(f"Missing {ERRORS} - run 13_Error_Taxonomy.py first")
    with ERRORS.open(encoding="utf-8") as f:
        return {
            r["species_id"]
            for r in csv.DictReader(f)
            if r["error_class"] == "JUNK_NON_SPECIES"
        }


def load_gold_rows():
    with GOLD.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    labelled = [
        r for r in rows
        if (r.get("gold_category") or "").strip()
        and (r.get("gold_free_text") or "").strip()
        and (r.get("raw_text_snippet") or "").strip()
    ]
    return rows, labelled


def stratified_folds(rows, n_folds: int, seed: int) -> dict[str, int]:
    """Deterministic stratified assignment: shuffle within class, then deal out.

    Dealing round-robin within each class keeps folds balanced even for classes
    too small to appear in every fold (PINK, n=4).
    """
    import random

    rng = random.Random(seed)
    by_class: dict[str, list] = defaultdict(list)
    for r in rows:
        by_class[r["gold_category"].strip()].append(r["species_id"])

    assignment: dict[str, int] = {}
    # Start each class at a different offset so small classes don't all pile
    # into fold 0.
    offset = 0
    for cls in sorted(by_class):
        ids = sorted(by_class[cls])
        rng.shuffle(ids)
        for i, sid in enumerate(ids):
            assignment[sid] = (i + offset) % n_folds
        offset = (offset + len(ids)) % n_folds
    return assignment


def to_record(row: dict) -> dict:
    desc = (row["raw_text_snippet"] or "").strip()[:MAX_DESC_CHARS]
    category = row["gold_category"].strip()
    free_text = row["gold_free_text"].strip()
    target = CANONICAL_UNKNOWN if category.upper() == "UNKNOWN" else free_text
    return {
        "species_id": row["species_id"],
        "gold_category": category,
        "gold_free_text": free_text,
        "target": target,
        "target_normalised": target != free_text,
        "messages": [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": user_message(desc)},
            {"role": "assistant", "content": target},
        ],
    }


def audit_targets(rows) -> list[tuple[str, str, str, str]]:
    """Find targets the scorer will not map back to their own gold class."""
    spec = importlib.util.spec_from_file_location(
        "c2", BASE / "scripts" / "14_Categorize_v2.py")
    c2 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(c2)
    spec2 = importlib.util.spec_from_file_location(
        "smg", BASE / "scripts" / "12_Score_Models_vs_Gold.py")
    smg = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(smg)

    problems = []
    for row in rows:
        rec = to_record(row)
        gold_cls = smg.to_class(rec["gold_category"])
        got = smg.to_class(c2.categorize_v2(rec["target"]))
        if got != gold_cls:
            problems.append((rec["species_id"], gold_cls, got, rec["target"]))
    return problems


def write_jsonl(path: Path, records) -> int:
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return len(records)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)

    junk_ids = load_junk_ids()
    all_rows, labelled = load_gold_rows()
    genuine = [r for r in labelled if r["species_id"] not in junk_ids]
    junk_rows = [r for r in labelled if r["species_id"] in junk_ids]

    print(f"gold rows            : {len(all_rows)}")
    print(f"human-labelled       : {len(labelled)}")
    print(f"JUNK_NON_SPECIES     : {len(junk_rows)}  (held out, never trained on)")
    print(f"genuine species (eval): {len(genuine)}")

    dist = Counter(r["gold_category"].strip() for r in genuine)
    print(f"class distribution   : {dict(sorted(dist.items()))}")

    folds = stratified_folds(genuine, args.folds, args.seed)

    fold_sizes = Counter(folds.values())
    print(f"\nfold sizes           : {dict(sorted(fold_sizes.items()))}")
    for k in range(args.folds):
        held = [r for r in genuine if folds[r["species_id"]] == k]
        kdist = Counter(r["gold_category"].strip() for r in held)
        print(f"  fold {k}: n={len(held):2d}  {dict(sorted(kdist.items()))}")

    for k in range(args.folds):
        train = [to_record(r) for r in genuine if folds[r["species_id"]] != k]
        held = [to_record(r) for r in genuine if folds[r["species_id"]] == k]
        n_tr = write_jsonl(OUTDIR / f"train_fold{k}.jsonl", train)
        n_ev = write_jsonl(OUTDIR / f"eval_fold{k}.jsonl", held)
        print(f"\nfold {k}: train={n_tr}  eval={n_ev}")

    n_junk = write_jsonl(OUTDIR / "eval_junk.jsonl", [to_record(r) for r in junk_rows])

    # A target the scorer cannot map back to its own gold class can never be
    # rewarded, however well the model reproduces it. Report these instead of
    # letting them quietly cap the achievable accuracy.
    unscoreable = audit_targets(genuine)
    n_normalised = sum(1 for r in genuine if to_record(r)["target_normalised"])
    print(f"\nUNKNOWN targets normalised to {CANONICAL_UNKNOWN!r}: {n_normalised}")
    if unscoreable:
        print(f"Targets that still cannot score as their own gold class: "
              f"{len(unscoreable)}/{len(genuine)}")
        for sid, gold_cls, got, txt in unscoreable:
            print(f"   gold={gold_cls:8s} scores as {got:8s} | {txt[:52]!r}")
        print("   (human-vs-rule disagreements on ambiguous multi-colour text; "
              "an inherent ceiling, not a bug)")

    (OUTDIR / "folds.json").write_text(
        json.dumps(folds, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    protocol = {
        "n_gold_rows": len(all_rows),
        "n_labelled": len(labelled),
        "n_genuine_eval": len(genuine),
        "n_junk_heldout": len(junk_rows),
        "junk_species_ids": sorted(junk_ids),
        "n_folds": args.folds,
        "seed": args.seed,
        "stratify_by": "gold_category",
        "target_field": "gold_free_text",
        "unknown_target_normalised_to": CANONICAL_UNKNOWN,
        "n_targets_normalised": n_normalised,
        "n_targets_unscoreable": len(unscoreable),
        "unscoreable_targets": [
            {"species_id": s, "gold_class": g, "scores_as": p, "target": t}
            for s, g, p, t in unscoreable
        ],
        "max_desc_chars": MAX_DESC_CHARS,
        "class_distribution": dict(sorted(dist.items())),
        "classes_too_small_for_all_folds": sorted(
            c for c, n in dist.items() if n < args.folds
        ),
        "system_message": SYSTEM_MESSAGE,
        "baselines_on_same_89_rows": {
            "qwen7b_zeroshot_v1": 0.8989,
            "qwen7b_zeroshot_v2": 0.9438,
            "qwen7b_rag_v1": 0.8989,
            "qwen7b_rag_v2": 0.9438,
            "note": "from VERIFIED_Numbers_for_Thesis.md section 7b; LoRA must be "
                    "compared against these on exactly these rows",
        },
    }
    (OUTDIR / "protocol.json").write_text(
        json.dumps(protocol, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"\njunk eval set        : {n_junk} rows -> eval_junk.jsonl")
    print(f"protocol frozen      : {OUTDIR / 'protocol.json'}")
    print(f"fold assignment      : {OUTDIR / 'folds.json'}")
    if protocol["classes_too_small_for_all_folds"]:
        print(
            "\nNOTE: "
            f"{protocol['classes_too_small_for_all_folds']} have fewer members than "
            f"{args.folds} folds, so they cannot appear in every held-out fold. "
            "Recorded in protocol.json."
        )


if __name__ == "__main__":
    main()
