#!/usr/bin/env python3
"""
Supervised adaptation - STEP 2: lock the baseline numbers on the frozen 89-row
evaluation set, with per-row correctness saved for paired significance testing.

Why this script exists
----------------------
Adding LoRA only means something if it is compared against the existing methods
on *exactly* the same rows, with the same categoriser, and with some notion of
whether a difference is real. With n=89 and roughly 5 remaining errors, a
one-row change is noise: a naive "94.4% -> 95.5%" claim would be indefensible.

So this script writes, for every existing method:
  * accuracy under categoriser v1 and v2, restricted to the frozen 89 rows
  * a per-row correct/incorrect vector, which lets later scripts run McNemar's
    exact test (the right test for two methods evaluated on the same items)
  * a bootstrap 95% CI on accuracy

It also re-derives the published n=89 figures as a self-check, so if anything
upstream drifts, this script fails loudly instead of silently comparing LoRA
against stale numbers.

  READS  : Processed Data/experiments/finetune/protocol.json  (frozen row set)
           Processed Data/experiments/gold_set_labeled.csv
           Processed Data/experiments/benchmark/gold_pred_*.csv
           Processed Data/experiments/rq3_outputs/gold_pred_qwen7b_rag.csv
  WRITES : Processed Data/experiments/finetune/
             baseline_per_row.csv      one row per (method, species_id) with correctness
             baseline_summary.csv      accuracy + bootstrap CI per method x categoriser

Usage
-----
  python 25_Lock_Baselines.py
"""

from __future__ import annotations

import csv
import importlib.util
import json
import random
import sys
from pathlib import Path

BASE = Path("/scratch/dp23301/Thesis")
EXP = BASE / "Processed Data" / "experiments"
GOLD = EXP / "gold_set_labeled.csv"
FT = EXP / "finetune"

csv.field_size_limit(sys.maxsize)

N_BOOT = 10000
BOOT_SEED = 42

# Published figures to re-derive as a self-check (VERIFIED_Numbers section 7b).
EXPECTED = {
    ("qwen7b_zeroshot", "v1"): 0.8989,
    ("qwen7b_zeroshot", "v2"): 0.9438,
    ("qwen7b_rag", "v1"): 0.8989,
    ("qwen7b_rag", "v2"): 0.9438,
}

PRED_FILES = {
    "rule_baseline": EXP / "benchmark" / "gold_pred_baseline.csv",
    "qwen7b_zeroshot": EXP / "benchmark" / "gold_pred_qwen7b_full.csv",
    "qwen72b_zeroshot": EXP / "benchmark" / "gold_pred_qwen72b.csv",
    "llama70b_zeroshot": EXP / "benchmark" / "gold_pred_llama70b.csv",
    "qwen7b_rag": EXP / "rq3_outputs" / "gold_pred_qwen7b_rag.csv",
}


def _load_module(name: str, filename: str):
    """Scripts start with digits, so they can't be imported normally."""
    spec = importlib.util.spec_from_file_location(name, BASE / "scripts" / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


c2 = _load_module("c2", "14_Categorize_v2.py")
smg = _load_module("smg", "12_Score_Models_vs_Gold.py")

CATEGORISERS = {"v1": c2.categorize_v1, "v2": c2.categorize_v2}


def is_abstention(text: str) -> bool:
    return "uncertain" in (text or "").lower()


def to_pred_class(text: str, categorise) -> str:
    """Abstentions score as UNKNOWN, per the RAG protocol in 15_RAG_Extract_Gold.py.

    Neither categoriser has a rule for 'uncertain', so without this it falls
    through to OTHER and every abstention is counted wrong - which is what made
    the published RAG figures fail to reproduce.
    """
    if is_abstention(text):
        return "UNKNOWN"
    return smg.to_class(categorise(text))


def load_protocol() -> dict:
    path = FT / "protocol.json"
    if not path.exists():
        raise SystemExit(f"Missing {path} - run 24_Prepare_Finetune_Data.py first")
    return json.loads(path.read_text(encoding="utf-8"))


def load_gold_classes() -> dict[str, str]:
    with GOLD.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return {
        r["species_id"]: smg.to_class(r["gold_category"].strip())
        for r in rows
        if (r.get("gold_category") or "").strip()
    }


def load_pred_text(path: Path) -> dict[str, str]:
    if not path.exists():
        print(f"  WARNING: missing {path.name} - skipping")
        return {}
    with path.open(encoding="utf-8-sig") as f:
        return {
            r["species_id"]: (r.get("flower_color_free_text") or "")
            for r in csv.DictReader(f)
        }


def bootstrap_ci(correct: list[int], n_boot: int = N_BOOT, seed: int = BOOT_SEED):
    rng = random.Random(seed)
    n = len(correct)
    if n == 0:
        return (float("nan"), float("nan"))
    means = []
    for _ in range(n_boot):
        means.append(sum(correct[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    return means[int(0.025 * n_boot)], means[int(0.975 * n_boot)]


def main():
    protocol = load_protocol()
    junk = set(protocol["junk_species_ids"])
    gold = load_gold_classes()

    eval_ids = sorted(sid for sid in gold if sid not in junk)
    n_eval = len(eval_ids)
    print(f"Frozen evaluation set: {n_eval} genuine species rows")
    if n_eval != protocol["n_genuine_eval"]:
        raise SystemExit(
            f"Row-set drift: protocol says {protocol['n_genuine_eval']}, got {n_eval}"
        )

    FT.mkdir(parents=True, exist_ok=True)
    per_row_path = FT / "baseline_per_row.csv"
    summary_path = FT / "baseline_summary.csv"

    per_rows = []
    summary = []
    mismatches = []

    for method, path in PRED_FILES.items():
        preds = load_pred_text(path)
        if not preds:
            continue
        for tag, fn in CATEGORISERS.items():
            correct, covered, abstained = [], 0, 0
            for sid in eval_ids:
                raw = preds.get(sid)
                if raw is None:
                    # no prediction for this row -> counts as wrong, but tracked
                    per_rows.append({
                        "method": method, "categoriser": tag, "species_id": sid,
                        "gold_class": gold[sid], "pred_class": "MISSING",
                        "pred_free_text": "", "abstained": 0, "correct": 0,
                    })
                    correct.append(0)
                    continue
                covered += 1
                abst = is_abstention(raw)
                abstained += int(abst)
                pred_class = to_pred_class(raw, fn)
                is_ok = int(pred_class == gold[sid])
                correct.append(is_ok)
                per_rows.append({
                    "method": method, "categoriser": tag, "species_id": sid,
                    "gold_class": gold[sid], "pred_class": pred_class,
                    "pred_free_text": raw.strip()[:200],
                    "abstained": int(abst), "correct": is_ok,
                })

            acc = sum(correct) / len(correct)
            lo, hi = bootstrap_ci(correct)
            summary.append({
                "method": method, "categoriser": tag, "n": len(correct),
                "n_predicted": covered, "n_abstained": abstained,
                "n_correct": sum(correct),
                "accuracy": round(acc, 4),
                "ci95_low": round(lo, 4), "ci95_high": round(hi, 4),
            })

            exp = EXPECTED.get((method, tag))
            flag = ""
            if exp is not None:
                if abs(acc - exp) > 0.0005:
                    flag = f"  <-- MISMATCH vs published {exp}"
                    mismatches.append((method, tag, acc, exp))
                else:
                    flag = f"  (matches published {exp})"
            abst_note = f"  abstained={abstained}" if abstained else ""
            print(f"  {method:20s} {tag}: acc={acc:.4f} "
                  f"[{lo:.4f}, {hi:.4f}]  correct={sum(correct)}/{len(correct)}"
                  f"{abst_note}{flag}")

    with per_row_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "method", "categoriser", "species_id", "gold_class",
            "pred_class", "pred_free_text", "abstained", "correct",
        ])
        w.writeheader()
        w.writerows(per_rows)

    with summary_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "method", "categoriser", "n", "n_predicted", "n_abstained",
            "n_correct", "accuracy", "ci95_low", "ci95_high",
        ])
        w.writeheader()
        w.writerows(summary)

    print(f"\nper-row correctness -> {per_row_path}")
    print(f"summary             -> {summary_path}")

    best = max(summary, key=lambda r: r["accuracy"])
    print(f"\nBar for LoRA to beat: {best['method']} + {best['categoriser']} = "
          f"{best['accuracy']:.4f} ({best['n_correct']}/{best['n']})")
    print(f"Its 95% CI is [{best['ci95_low']:.4f}, {best['ci95_high']:.4f}] - with "
          f"only {best['n'] - best['n_correct']} errors left, expect to need "
          f"McNemar's test rather than raw accuracy to claim any improvement.")

    if mismatches:
        raise SystemExit(
            f"\nFAILED self-check: {len(mismatches)} published figure(s) did not "
            f"reproduce: {mismatches}"
        )
    print("\nSelf-check passed: all published n=89 figures reproduced exactly.")


if __name__ == "__main__":
    main()
