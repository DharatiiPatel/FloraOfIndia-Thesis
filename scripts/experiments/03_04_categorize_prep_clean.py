#!/usr/bin/env python3
"""
Steps 03 + 04 for the CLEAN (treatment-parser) pipeline, combined.

Because the treatment parser already produced clean genus/epithet, we categorise
the Qwen colour output AND emit a step04-style "species_only" file in one pass.

SAFE BY DESIGN:
  READS  : Processed Data/experiments/flower_color_qwen_clean.csv
  WRITES : Processed Data/experiments/clean_color_categories.csv   (all rows)
           Processed Data/experiments/clean_species_only.csv       (input for 05a)
  Pipeline untouched.

The categorize_color() logic is IDENTICAL to scripts/03_Categorize_Flower_color.py
so results are comparable to the original run.
"""

import csv
from pathlib import Path

BASE = Path("/scratch/dp23301/Thesis")
IN = BASE / "Processed Data" / "experiments" / "flower_color_qwen_clean.csv"
OUT_ALL = BASE / "Processed Data" / "experiments" / "clean_color_categories.csv"
OUT_SPP = BASE / "Processed Data" / "experiments" / "clean_species_only.csv"


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


def main():
    rows = list(csv.DictReader(IN.open(encoding="utf-8")))
    print(f"Read {len(rows)} species from {IN.name}")

    from collections import Counter
    cats = Counter()

    with OUT_ALL.open("w", newline="", encoding="utf-8") as fa, \
         OUT_SPP.open("w", newline="", encoding="utf-8") as fs:
        wa = csv.DictWriter(fa, fieldnames=[
            "species_id", "volume", "flower_color_free_text", "color_category",
            "genus", "epithet", "binomial", "has_description"])
        wa.writeheader()
        # species_only mirrors step04 schema expected by 05a
        ws = csv.DictWriter(fs, fieldnames=[
            "species_id", "volume", "flower_color_free_text", "color_category",
            "genus", "epithet", "is_species_level"])
        ws.writeheader()

        for r in rows:
            free = (r.get("flower_color_free_text") or "").strip()
            cat = categorize_color(free)
            cats[cat] += 1
            wa.writerow({
                "species_id": r["species_id"], "volume": r["volume"],
                "flower_color_free_text": free, "color_category": cat,
                "genus": r["genus"], "epithet": r["epithet"],
                "binomial": r["binomial"], "has_description": r.get("has_description", ""),
            })
            ws.writerow({
                "species_id": r["species_id"], "volume": r["volume"],
                "flower_color_free_text": free, "color_category": cat,
                "genus": r["genus"], "epithet": r["epithet"],
                "is_species_level": "TRUE",
            })

    print("\nColour category counts (CLEAN pipeline):")
    for c, n in cats.most_common():
        print(f"  {c:12s}: {n}")
    known = sum(n for c, n in cats.items() if c in {"WHITE", "YELLOW", "RED", "PINK", "PURPLE/BLUE"})
    print(f"\nKnown-colour species (go to GBIF): {known}")
    print(f"Wrote: {OUT_ALL}")
    print(f"Wrote: {OUT_SPP}")


if __name__ == "__main__":
    main()
