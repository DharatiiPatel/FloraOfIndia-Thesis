#!/usr/bin/env python3
"""
Supervised adaptation - STEP 4: score LoRA against the locked baselines.

Accuracy alone cannot settle whether fine-tuning helped here. With 89 rows, a
two-point difference is roughly two species, so the honest question is not
"which number is bigger" but "is this difference distinguishable from noise".
Two things address that:

  - a bootstrap 95% CI on each method's accuracy, and
  - McNemar's exact test on each LoRA-vs-baseline pair.

McNemar is the right test because every method is evaluated on the identical
89 rows. It ignores rows both methods get right or both get wrong - those carry
no information about which is better - and asks only whether the disagreements
split evenly. Comparing two independent CIs would instead throw away the
pairing and badly understate the evidence.

Scoring functions are imported from 25_Lock_Baselines.py rather than
reimplemented, so LoRA is scored through byte-identical logic to the published
baselines - including the rule that an abstention counts as UNKNOWN.

  READS  : Processed Data/experiments/finetune/protocol.json
                                              baseline_per_row.csv
                                              lora_predictions.csv
                                              lora_predictions_junk.csv
  WRITES : Processed Data/experiments/finetune/adaptation_summary.csv
                                              adaptation_mcnemar.csv
                                              adaptation_per_row.csv

Usage:  python 27_Score_Adaptation.py
"""

from __future__ import annotations

import csv
import importlib.util
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

BASE = Path("/scratch/dp23301/Thesis")
FT = BASE / "Processed Data" / "experiments" / "finetune"

csv.field_size_limit(sys.maxsize)

spec = importlib.util.spec_from_file_location("lock", BASE / "scripts" / "25_Lock_Baselines.py")
lock = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lock)

CATEGORISERS = lock.CATEGORISERS


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value.

    b and c are the counts of rows where exactly one of the two methods is
    correct. Under the null those b+c disagreements are a fair coin, so the
    p-value is the two-sided binomial tail. The exact form is used rather than
    the chi-square approximation because b+c here is small enough that the
    approximation is not trustworthy.
    """
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def load_lora_preds() -> dict[str, str]:
    path = FT / "lora_predictions.csv"
    if not path.exists():
        raise SystemExit(f"Missing {path} - run 26_LoRA_Finetune.py first")
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    preds, folds = {}, {}
    for r in rows:
        sid = r["species_id"]
        if sid in preds:
            raise SystemExit(f"Duplicate out-of-fold prediction for {sid}")
        preds[sid] = r.get("flower_color_free_text") or ""
        folds[sid] = int(r["fold"])
    return preds, folds


def load_baseline_rows() -> dict[tuple[str, str], dict[str, int]]:
    path = FT / "baseline_per_row.csv"
    if not path.exists():
        raise SystemExit(f"Missing {path} - run 25_Lock_Baselines.py first")
    out: dict[tuple[str, str], dict[str, int]] = defaultdict(dict)
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[(r["method"], r["categoriser"])][r["species_id"]] = int(r["correct"])
    return out


def main():
    protocol = lock.load_protocol()
    gold = lock.load_gold_classes()
    junk = set(protocol["junk_species_ids"])
    eval_ids = sorted(sid for sid in gold if sid not in junk)

    lora_text, folds = load_lora_preds()
    missing = [s for s in eval_ids if s not in lora_text]
    if missing:
        raise SystemExit(
            f"LoRA predictions cover {len(lora_text)}/{len(eval_ids)} rows; "
            f"{len(missing)} missing. Are all 5 folds finished?")

    n_folds = len(set(folds.values()))
    print(f"Evaluation set : {len(eval_ids)} genuine rows")
    print(f"LoRA coverage  : {len(lora_text)} out-of-fold predictions "
          f"from {n_folds} folds")
    unscoreable = {u["species_id"] for u in protocol.get("unscoreable_targets", [])}
    if unscoreable:
        print(f"Ceiling        : {len(unscoreable)} rows have targets the "
              f"categoriser cannot score as their gold class")
    print()

    baselines = load_baseline_rows()
    summary_rows, mcnemar_rows, per_row = [], [], []

    for cat_name, categorise in CATEGORISERS.items():
        lora_correct = {
            sid: int(lock.to_pred_class(lora_text[sid], categorise) == gold[sid])
            for sid in eval_ids
        }
        vec = [lora_correct[s] for s in eval_ids]
        acc = sum(vec) / len(vec)
        lo, hi = lock.bootstrap_ci(vec)
        print(f"--- categoriser {cat_name} ---")
        print(f"  {'lora_qwen7b':<20s} acc={acc:.4f}  "
              f"95% CI [{lo:.4f}, {hi:.4f}]  ({sum(vec)}/{len(vec)})")
        summary_rows.append({
            "method": "lora_qwen7b", "categoriser": cat_name,
            "n": len(vec), "n_correct": sum(vec), "accuracy": round(acc, 4),
            "ci_lo": round(lo, 4), "ci_hi": round(hi, 4),
        })

        for sid in eval_ids:
            per_row.append({
                "species_id": sid, "categoriser": cat_name, "fold": folds[sid],
                "gold_class": gold[sid],
                "pred_class": lock.to_pred_class(lora_text[sid], categorise),
                "pred_text": lora_text[sid],
                "correct": lora_correct[sid],
            })

        for method, ref in sorted(baselines.items()):
            if method[1] != cat_name or method[0] == "lora_qwen7b":
                continue
            name = method[0]
            base_vec = [ref.get(s, 0) for s in eval_ids]
            base_acc = sum(base_vec) / len(base_vec)
            # b: LoRA right, baseline wrong. c: the reverse.
            b = sum(1 for i, s in enumerate(eval_ids)
                    if lora_correct[s] == 1 and base_vec[i] == 0)
            c = sum(1 for i, s in enumerate(eval_ids)
                    if lora_correct[s] == 0 and base_vec[i] == 1)
            p = mcnemar_exact(b, c)
            verdict = "n.s." if p >= 0.05 else ("LoRA better" if b > c else "baseline better")
            print(f"    vs {name:<18s} base_acc={base_acc:.4f}  "
                  f"delta={acc - base_acc:+.4f}  b={b} c={c}  p={p:.4f}  {verdict}")
            mcnemar_rows.append({
                "categoriser": cat_name, "baseline": name,
                "lora_acc": round(acc, 4), "baseline_acc": round(base_acc, 4),
                "delta": round(acc - base_acc, 4),
                "lora_only_correct": b, "baseline_only_correct": c,
                "n_discordant": b + c, "p_mcnemar_exact": round(p, 4),
                "verdict": verdict,
            })
        print()

    junk_path = FT / "lora_predictions_junk.csv"
    if junk_path.exists():
        with junk_path.open(encoding="utf-8") as f:
            jrows = list(csv.DictReader(f))
        by_fold = defaultdict(list)
        for r in jrows:
            by_fold[r["fold"]].append(r)
        rates = []
        for fold, rs in sorted(by_fold.items()):
            n_abstain = sum(
                1 for r in rs
                if lock.to_pred_class(r["flower_color_free_text"],
                                      CATEGORISERS["v2"]) == "UNKNOWN")
            rates.append(n_abstain / len(rs))
        mean_rate = sum(rates) / len(rates)
        print(f"Malformed rows (n={len(by_fold[list(by_fold)[0]])}, never trained on):")
        print(f"  LoRA abstains on {mean_rate:.1%} of them, averaged over "
              f"{len(rates)} folds")
        print(f"  per-fold: {', '.join(f'{r:.0%}' for r in rates)}")
        print()

    # How much room was there to improve in the first place? Without this, a
    # negative fine-tuning result reads as a failed method rather than what it
    # is: a task with almost nothing left to win.
    v2 = CATEGORISERS["v2"]
    all_methods = {m: rows_ for (m, cat), rows_ in baselines.items() if cat == "v2"}
    all_methods["lora_qwen7b"] = {
        sid: int(lock.to_pred_class(lora_text[sid], v2) == gold[sid])
        for sid in eval_ids
    }
    zs = all_methods.get("qwen7b_zeroshot", {})
    zs_errors = [s for s in eval_ids if zs.get(s, 0) == 0]
    never = [s for s in eval_ids if all(m.get(s, 0) == 0 for m in all_methods.values())]
    solved = len(eval_ids) - len(never)
    n = len(eval_ids)

    print("Headroom (categoriser v2):")
    print(f"  best single method reaches {max(sum(m.get(s, 0) for s in eval_ids) for m in all_methods.values())}/{n}")
    print(f"  zero-shot's {len(zs_errors)} errors include "
          f"{len(set(zs_errors) & unscoreable)} whose gold target the categoriser "
          f"cannot score at all,")
    print(f"    leaving {len(zs_errors) - len(set(zs_errors) & unscoreable)} rows "
          f"genuinely winnable")
    print(f"  practical ceiling {n - len(unscoreable)}/{n} = "
          f"{(n - len(unscoreable)) / n:.4f}")
    print(f"  union over every method (oracle) {solved}/{n} = {solved / n:.4f} - "
          f"even a perfect ensemble of everything built here")
    print()

    def write(path: Path, rows: list[dict]):
        if not rows:
            return
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"  wrote {path.name} ({len(rows)} rows)")

    write(FT / "adaptation_summary.csv", summary_rows)
    write(FT / "adaptation_mcnemar.csv", mcnemar_rows)
    write(FT / "adaptation_per_row.csv", per_row)


if __name__ == "__main__":
    main()
