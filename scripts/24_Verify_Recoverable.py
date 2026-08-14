#!/usr/bin/env python3
"""
Prove (or disprove) that species were actually lost to parsing.

28_Diagnose_Unknown_Colour.py (now scripts/legacy/) estimated that 758 species were dropped because
their description was mis-parsed rather than because the Flora omits colour.
That was inference from what the pipeline produced. This script tests it
against the source: it goes back to the OCR'd volume text, locates each lost
species' treatment, and checks whether the treatment states a flower colour.

A species only counts as lost if all three hold:
  1. it is currently UNKNOWN and diagnosed as a parsing failure,
  2. its treatment can be located in the raw volume text, and
  3. that treatment names a colour on a flower organ.

Locating the treatment is the same problem that caused the loss, so it is done
carefully. A binomial can appear many times in a volume - in the index, in a
key, in another species' synonymy - and only one of those is the treatment.
Every occurrence is scored on the morphological content of the text following
it, and the best-scoring window wins. Occurrences that look like index runs
are rejected outright.

CONTROL: the same locator is run on species whose colour the pipeline already
found. If it cannot reproduce those known colours it is not trustworthy on the
lost ones, so that agreement rate is reported first and gates the result.

  READS  : raw_data/FLORA OF INDIA VOL.*.txt
           Processed Data/experiments/unknown_diagnosis.csv
                                      clean_color_categories.csv
  WRITES : Processed Data/experiments/recoverable_verified.csv

Usage:  python 24_Verify_Recoverable.py [--limit 400] [--control 150]
"""

from __future__ import annotations

import argparse
import csv
import glob
import random
import re
import sys
from collections import Counter
from pathlib import Path

BASE = Path("/scratch/dp23301/Thesis")
EXP = BASE / "Processed Data" / "experiments"

csv.field_size_limit(sys.maxsize)

WINDOW = 2200          # chars of treatment text to read after a name match
MIN_MORPH_HITS = 3     # morphology terms needed before we call a window a treatment

FLOWER_ORGAN = re.compile(
    r"\b(flowers?|florets?|corollas?|petals?|perianth|calyx|sepals?|tepals?)\b", re.I)
COLOUR = re.compile(
    r"\b(white|yellow|red|pink|purple|blue|greenish|orange|violet|crimson|"
    r"scarlet|lilac|mauve|rose|cream|magenta|maroon|golden|"
    r"whitish|yellowish|reddish|purplish|bluish|pinkish)\b", re.I)
APPENDAGE = re.compile(
    r"\b(hairs?|hairy|pappus|filaments?|margins?|margined|scarious|ciliate|"
    r"pubescen(t|ce)|tomentose|villous|puberulous|stellate|bristles?|"
    r"anthers?|styles?|stigmas?|glands?|scales?|veins?|midribs?)\b", re.I)
MORPH = re.compile(
    r"\b(herbs?|shrubs?|trees?|leaves|leaflets?|stems?|branch(es|lets)?|"
    r"petioles?|lamina|inflorescences?|racemes?|panicles?|spikes?|umbels?|"
    r"cymes?|bracts?|ovary|stamens?|capsules?|seeds?|fruits?|glabrous|"
    r"pubescent|erect|ovate|lanceolate|oblong|elliptic|acute|obtuse)\b", re.I)


def load_volumes() -> dict[str, str]:
    vols = {}
    for path in glob.glob(str(BASE / "raw_data" / "*.txt")):
        m = re.search(r"VOL\.?\s*(\d+)", Path(path).name, re.I)
        if m:
            vols[m.group(1)] = Path(path).read_text(encoding="utf-8", errors="ignore")
    return vols


def looks_like_index(window: str) -> bool:
    """Index runs are dense in digits and sparse in prose."""
    if not window:
        return True
    digits = sum(c.isdigit() for c in window[:400])
    return digits > len(window[:400]) * 0.22


    # A new numbered treatment, or a figure caption, ends the current one. Without
# this the window runs into the next species and picks up its colour - the
# first version of this script scored Myricaria squamosa WHITE from the text of
# Myricaria albiflora sitting directly below it.
BOUNDARY = re.compile(
    r"(\n\s*\d{1,3}\s*\.\s+[A-Z][a-z]{2,}\s+[a-z]{3,})"      # '2. Myricaria davurica'
    r"|(\bFig\s*\.?\s*\d+)"                                    # figure caption
    r"|(\n\s*[A-Z]{4,}(?:\s+[A-Z]{4,})*\s*\n)",                # FAMILY heading
    re.I if False else 0)


def cut_at_boundary(window: str) -> str:
    m = BOUNDARY.search(window)
    return window[:m.start()] if m else window


def locate_treatment(text: str, genus: str, epithet: str) -> str | None:
    """Return the best candidate treatment window for this binomial."""
    if not genus or not epithet:
        return None
    # Genus is often abbreviated to its initial after first mention.
    pattern = re.compile(
        r"\b(?:" + re.escape(genus) + r"|" + re.escape(genus[0]) + r"\.?)\s+"
        + re.escape(epithet) + r"\b", re.I)

    best, best_score = None, 0
    for m in pattern.finditer(text):
        window = cut_at_boundary(text[m.end():m.end() + WINDOW])
        if looks_like_index(window):
            continue
        score = len(set(x.group(0).lower() for x in MORPH.finditer(window)))
        if score > best_score:
            best, best_score = window, score
    return best if best_score >= MIN_MORPH_HITS else None


def flower_colour_in(window: str) -> str | None:
    """Colour word sitting on a flower organ, ignoring hairs/margins/etc."""
    if not window:
        return None
    for m in COLOUR.finditer(window):
        ctx = window[max(0, m.start() - 40):m.end() + 40]
        if APPENDAGE.search(ctx):
            continue
        wide = window[max(0, m.start() - 70):m.end() + 70]
        if FLOWER_ORGAN.search(wide):
            return m.group(0).lower()
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=400,
                    help="lost species to test (0 = all)")
    ap.add_argument("--control", type=int, default=150,
                    help="known-colour species used to validate the locator")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    vols = load_volumes()
    print(f"Loaded {len(vols)} volumes, "
          f"{sum(len(v) for v in vols.values()) / 1e6:.1f}M chars\n")

    diag = {r["species_id"]: r["cause"]
            for r in csv.DictReader((EXP / "unknown_diagnosis.csv").open(encoding="utf-8"))}
    with (EXP / "clean_color_categories.csv").open(encoding="utf-8-sig") as f:
        cats = list(csv.DictReader(f))

    PARSE_FAIL = {"EMPTY", "NOT_A_DESCRIPTION", "TRUNCATED_PRE_FLOWER"}
    lost = [r for r in cats if diag.get(r["species_id"]) in PARSE_FAIL]
    known = [r for r in cats
             if r["color_category"].strip().upper() not in ("UNKNOWN", "")]

    rng = random.Random(args.seed)

    # ---- CONTROL: can the locator reproduce colours we already have? ----
    # The real test is not whether a colour is present but whether it is the
    # RIGHT one. A window that has drifted into the next species will still
    # contain a colour, so 'found a colour' proves nothing on its own.
    import importlib.util
    spec = importlib.util.spec_from_file_location("c2", BASE / "scripts" / "14_Categorize_v2.py")
    c2 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(c2)

    ctrl = rng.sample(known, min(args.control, len(known)))
    ctrl_found = ctrl_colour = ctrl_match = 0
    for r in ctrl:
        w = locate_treatment(vols.get(r.get("volume", "").strip(), ""),
                             r.get("genus", "").strip(), r.get("epithet", "").strip())
        if w is None:
            continue
        ctrl_found += 1
        colour = flower_colour_in(w)
        if not colour:
            continue
        ctrl_colour += 1
        if c2.categorize_v2(colour).strip().upper() == r["color_category"].strip().upper():
            ctrl_match += 1

    print("CONTROL - locator run on species whose colour we already know")
    print("=" * 68)
    print(f"  treatment located      : {ctrl_found}/{len(ctrl)} ({ctrl_found / len(ctrl):.1%})")
    if ctrl_found:
        print(f"  a colour found in it   : {ctrl_colour}/{ctrl_found} "
              f"({ctrl_colour / ctrl_found:.1%})")
    if ctrl_colour:
        acc = ctrl_match / ctrl_colour
        print(f"  and it is the RIGHT one: {ctrl_match}/{ctrl_colour} ({acc:.1%})")
        print(f"  -> the locator is {'trustworthy' if acc >= 0.8 else 'NOT reliable enough'}"
              f" for the test below")
        if acc < 0.8:
            print("     Treat the recoverable count as an upper bound, not a result.")
    print()

    # ---- TEST: the species we believe were lost ----
    pool = lost if args.limit == 0 else rng.sample(lost, min(args.limit, len(lost)))
    rows, causes = [], Counter()
    for r in pool:
        sid = r["species_id"]
        w = locate_treatment(vols.get(r.get("volume", "").strip(), ""),
                             r.get("genus", "").strip(), r.get("epithet", "").strip())
        colour = flower_colour_in(w) if w else None
        status = ("RECOVERABLE" if colour else
                  "located_no_colour" if w else "not_located")
        causes[status] += 1
        rows.append({
            "species_id": sid, "volume": r.get("volume", ""),
            "genus": r.get("genus", ""), "epithet": r.get("epithet", ""),
            "diagnosis": diag.get(sid, ""), "status": status,
            "colour_found": colour or "",
            "evidence": (w or "")[:300].replace("\n", " "),
        })

    n = len(pool)
    rec = causes["RECOVERABLE"]
    print(f"TEST - {n} species diagnosed as lost to parsing")
    print("=" * 68)
    for k, c in causes.most_common():
        print(f"  {k:22s} {c:5d}  {c / n:6.1%}")
    print()
    print(f"  => {rec}/{n} ({rec / n:.1%}) have a locatable treatment that "
          f"states a flower colour")
    print(f"     extrapolated to all {len(lost)} parse-failed species: "
          f"~{int(rec / n * len(lost))} genuinely recoverable")
    print()

    print("EVIDENCE - species currently thrown away whose colour is in the source")
    print("=" * 68)
    shown = 0
    for r in rows:
        if r["status"] != "RECOVERABLE" or shown >= 8:
            continue
        shown += 1
        ev = re.sub(r"\s+", " ", r["evidence"])[:190]
        print(f"  {r['genus']} {r['epithet']} (vol {r['volume']}, {r['diagnosis']}) "
              f"-> {r['colour_found'].upper()}")
        print(f"     ...{ev}...")

    out = EXP / "recoverable_verified.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w_ = csv.DictWriter(f, fieldnames=list(rows[0]))
        w_.writeheader()
        w_.writerows(rows)
    print(f"\nwrote {out.name} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
