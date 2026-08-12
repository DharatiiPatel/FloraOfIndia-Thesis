#!/usr/bin/env python3
"""
Fix abbreviated genus names caused by OCR (e.g. "A. tetrasepala" -> "Anemone tetrasepala").

SAFE BY DESIGN:
  - READS  : Processed Data/flora_of_india_species_descriptions.csv   (never modified)
  - WRITES : Processed Data/experiments/species_descriptions_genusfixed.csv
             Processed Data/experiments/genus_fix_audit.csv
  - Does NOT touch any step04/05/06 outputs or your existing pipeline.

METHOD (genus carry-forward):
  Within each volume, species are printed in taxonomic order. The FULL genus is
  spelled out at the start of a genus section (e.g. "1. Anemone tetrasepala ...")
  and later species reuse the initial ("15. A. rivularis ...").
  We walk the rows in order, remember the last fully-spelled genus, and expand an
  abbreviation "X." to that genus ONLY IF the last full genus starts with "X".
  If the initial does not match, we cannot safely expand -> flagged, not guessed.
"""

import re
import csv
from pathlib import Path

BASE = Path("/scratch/dp23301/Thesis")
IN_CSV  = BASE / "Processed Data" / "flora_of_india_species_descriptions.csv"
OUT_DIR = BASE / "Processed Data" / "experiments"
OUT_CSV = OUT_DIR / "species_descriptions_genusfixed.csv"
AUDIT   = OUT_DIR / "genus_fix_audit.csv"

# leading numbering like "15." or "15 "
NUM_PREFIX = re.compile(r"^\s*\d+\.?\s*")
# abbreviated genus token: single capital letter + period, e.g. "A." or "Ae."
ABBREV = re.compile(r"^([A-Z][a-z]?)\.$")
# a plausible FULL genus token: Capitalised word, >= 3 letters, all alphabetic
FULL_GENUS = re.compile(r"^[A-Z][a-z]{2,}$")


def parse_name(species_id: str):
    """Return (genus_token, epithet_token, rest) from a species_id string."""
    name = NUM_PREFIX.sub("", species_id).strip()
    toks = name.split()
    genus = toks[0] if len(toks) >= 1 else ""
    epithet = toks[1] if len(toks) >= 2 else ""
    return genus, epithet, name


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(IN_CSV.open(encoding="utf-8")))
    print(f"Read {len(rows)} blocks from {IN_CSV.name}")

    last_full_by_volume = {}   # volume -> last fully-spelled genus seen
    out_rows = []

    n_abbrev = 0
    n_expanded = 0
    n_unresolved = 0

    for r in rows:
        vol = r.get("volume", "")
        genus, epithet, name = parse_name(r["species_id"])

        genus_fixed = genus
        was_abbrev = 0
        confident = 1
        note = ""

        m = ABBREV.match(genus)
        if m:
            was_abbrev = 1
            n_abbrev += 1
            initial = m.group(1)[0]  # first letter of the abbreviation
            last_full = last_full_by_volume.get(vol, "")
            if last_full and last_full[0] == initial:
                genus_fixed = last_full
                n_expanded += 1
                note = f"expanded from '{genus}' using last full genus '{last_full}'"
            else:
                confident = 0
                n_unresolved += 1
                note = f"could not expand '{genus}' (last full genus in vol={last_full or 'NONE'})"
        elif FULL_GENUS.match(genus):
            # remember this as the current full genus for the volume
            last_full_by_volume[vol] = genus
        else:
            # odd token (garbled/numeric) - leave as-is, do not update memory
            note = "genus token not recognised as full or abbreviated"

        binomial_fixed = (genus_fixed + " " + epithet).strip()

        out_rows.append({
            **r,
            "genus_original": genus,
            "genus_fixed": genus_fixed,
            "epithet": epithet,
            "binomial_fixed": binomial_fixed,
            "was_abbreviated": was_abbrev,
            "expansion_confident": confident,
            "fix_note": note,
        })

    fieldnames = list(rows[0].keys()) + [
        "genus_original", "genus_fixed", "epithet", "binomial_fixed",
        "was_abbreviated", "expansion_confident", "fix_note",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)

    # audit file = only the abbreviated rows, for manual spot-checking
    with AUDIT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "species_id", "volume", "genus_original", "genus_fixed",
            "binomial_fixed", "expansion_confident", "fix_note",
        ])
        w.writeheader()
        for r in out_rows:
            if r["was_abbreviated"]:
                w.writerow({k: r[k] for k in w.fieldnames})

    print("\n──────── GENUS FIX AUDIT ────────")
    print(f"Total blocks           : {len(rows)}")
    print(f"Abbreviated genus       : {n_abbrev}")
    print(f"  -> expanded (confident): {n_expanded}")
    print(f"  -> UNRESOLVED (flagged): {n_unresolved}")
    print(f"\nWrote fixed dataset : {OUT_CSV}")
    print(f"Wrote audit (abbrev): {AUDIT}")
    print("\nNext: open the audit CSV, eyeball ~50 rows, confirm expansions look right.")


if __name__ == "__main__":
    main()
