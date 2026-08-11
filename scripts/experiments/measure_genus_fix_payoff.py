#!/usr/bin/env python3
"""
Estimate how many EXTRA species the genus fix could recover for analysis.

SAFE BY DESIGN (read-only on pipeline; writes only to experiments/):
  READS:
    Processed Data/experiments/species_descriptions_genusfixed.csv   (genus fix)
    Processed Data/step04_outputs/flora_india_color_clean_species_only.csv (colours)
    Processed Data/step05_outputs/gbif_failed_species.txt            (GBIF failures)
    Processed Data/step05_outputs/species_color_environment_final.csv (already-in-analysis)
  WRITES:
    Processed Data/experiments/genus_fix_payoff_candidates.csv
    (prints a summary table)

We can't KNOW GBIF will match without querying it, so this gives an
UPPER-BOUND / candidate list, split by how clean the epithet looks.
"""

import csv
import re
from pathlib import Path

BASE = Path("/scratch/dp23301/Thesis")
FIXED = BASE / "Processed Data" / "experiments" / "species_descriptions_genusfixed.csv"
CLEAN = BASE / "Processed Data" / "step04_outputs" / "flora_india_color_clean_species_only.csv"
FAILED = BASE / "Processed Data" / "step05_outputs" / "gbif_failed_species.txt"
FINAL = BASE / "Processed Data" / "step05_outputs" / "species_color_environment_final.csv"
OUT = BASE / "Processed Data" / "experiments" / "genus_fix_payoff_candidates.csv"

KNOWN = {"WHITE", "YELLOW", "RED", "PINK", "PURPLE/BLUE"}
# a "clean" epithet: all lowercase letters, 3+ chars, no mid-word capitals/digits
CLEAN_EPITHET = re.compile(r"^[a-z]{3,}$")


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip()).lower()


def main():
    # 1) colours by species_id
    colour_by_id = {}
    for r in csv.DictReader(CLEAN.open(encoding="utf-8")):
        colour_by_id[r["species_id"].strip()] = r["color_category"].strip().upper()

    # 2) which binomials are ALREADY in the final analysis (Genus species)
    already = set()
    for r in csv.DictReader(FINAL.open(encoding="utf-8")):
        # final file stores the query name; try common column names
        name = r.get("query_name") or r.get("binomial") or r.get("species") or ""
        if name:
            already.add(norm(name))

    # 3) genus-fixed rows, joined to colour
    tier1 = []  # known colour + confident genus + clean epithet  (best bet)
    tier2 = []  # known colour + confident genus + garbled epithet (fuzzy maybe)
    n_known_abbrev = 0

    for r in csv.DictReader(FIXED.open(encoding="utf-8")):
        sid = r["species_id"].strip()
        colour = colour_by_id.get(sid, "")
        was_abbrev = r["was_abbreviated"] == "1"
        confident = r["expansion_confident"] == "1"
        epithet = r["epithet"].strip()
        binom = norm(r["binomial_fixed"])

        if colour not in KNOWN:
            continue
        if not was_abbrev:
            continue  # only care about abbreviated ones (the fix target)
        n_known_abbrev += 1
        if not confident:
            continue
        if binom in already:
            continue  # already recovered somehow, no new gain

        row = {
            "species_id": sid,
            "volume": r["volume"],
            "colour": colour,
            "genus_fixed": r["genus_fixed"],
            "epithet": epithet,
            "binomial_fixed": r["binomial_fixed"],
        }
        if CLEAN_EPITHET.match(epithet):
            tier1.append(row)
        else:
            tier2.append(row)

    # write candidate list (tier1 first)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "tier", "species_id", "volume", "colour",
            "genus_fixed", "epithet", "binomial_fixed",
        ])
        w.writeheader()
        for row in tier1:
            w.writerow({"tier": "1_clean_epithet", **row})
        for row in tier2:
            w.writerow({"tier": "2_garbled_epithet", **row})

    print("──────── GENUS-FIX PAYOFF ESTIMATE ────────")
    print(f"Already in final analysis (n)          : {len(already)}")
    print(f"Known-colour + abbreviated genus rows  : {n_known_abbrev}")
    print(f"  Tier 1 (clean epithet, best GBIF bet): {len(tier1)}")
    print(f"  Tier 2 (garbled epithet, fuzzy maybe): {len(tier2)}")
    print(f"  Candidate total (upper bound)        : {len(tier1) + len(tier2)}")
    print()
    print("Reality check: not all candidates will match GBIF or have >=6 records,")
    print("so realistic recovered species < candidate total.")
    print(f"\nWrote candidate list: {OUT}")


if __name__ == "__main__":
    main()
