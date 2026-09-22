#!/usr/bin/env python3
"""
Build one SLURM array task per (variant x colour x chain).

Reads  : Processed Data/experiments/wp4_label_variants/species_color_environment_<variant>.csv
Writes : Processed Data/experiments/wp4_label_variants/mcmc_manifest.csv

Usage:
  python 18_Make_MCMC_Manifest.py --variant baseline --variant qwen7b
"""

import argparse
import csv
from pathlib import Path

BASE = Path("/scratch/dp23301/Thesis")
VARDIR = BASE / "Processed Data" / "experiments" / "wp4_label_variants"
MANIFEST = VARDIR / "mcmc_manifest.csv"

COLORS = [("WHITE", "is_white"), ("YELLOW", "is_yellow"), ("REDTYPE", "is_redtype")]
# 3 chains per (variant,colour) for Gelman-Rubin; distinct seeds
CHAIN_SEEDS = {1: 42, 2: 123, 3: 456}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", action="append", required=True)
    args = ap.parse_args()

    rows = []
    tid = 0
    for variant in args.variant:
        ds = VARDIR / f"species_color_environment_{variant}.csv"
        if not ds.exists():
            raise FileNotFoundError(
                f"variant dataset missing: {ds}\n"
                f"run 17_Build_Label_Variant.py --variant {variant} first")
        for color_label, response_col in COLORS:
            for chain, seed in CHAIN_SEEDS.items():
                rows.append(dict(
                    task_id=tid, variant=variant, dataset_path=str(ds),
                    color_label=color_label, response_col=response_col,
                    chain=chain, seed=seed))
                tid += 1

    with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote manifest with {len(rows)} tasks -> {MANIFEST}")
    print(f"Submit with:  sbatch --array=0-{len(rows)-1} "
          f"scripts/slurm/run_19_array.slurm")

if __name__ == "__main__":
    main()
