#!/usr/bin/env python3
"""
Diagnose the 2,140 species dropped for UNKNOWN flower colour.

UNKNOWN colour is the largest single loss in the pipeline: 55.5% of parsed
species (2,140 of 3,857) never reach the ecological analysis because of it,
against 233 lost at the GBIF step. Whether that is worth attacking depends
entirely on a question nobody has answered yet - are these treatments that
genuinely omit flower colour, or treatments whose text was mis-parsed before
the extractor ever saw it?

Spot checks say at least some are the latter. One species' entire description
is a herbarium locality citation, another's is the single word DILLENIACEAE
(a family heading from the following section), another's is a run of page
numbers from an index. This script sorts all 2,140 into causes so the
recoverable fraction can be estimated rather than guessed.

Causes, in the order they are tested
------------------------------------
  EMPTY                  no text at all
  NOT_A_DESCRIPTION      text is an index run, family heading, or bare
                         citation - no morphological content whatsoever
  TRUNCATED_PRE_FLOWER   real morphology (leaves, stems) but the text stops
                         before any flower organ is named
  COLOUR_PRESENT_MISSED  a colour word sits near a flower organ, so the text
                         did carry the answer - an extraction or categoriser
                         miss, recoverable with no re-parsing at all
  COLOUR_NON_FLORAL      colour words present but only near fruit/leaf/bark
                         terms, correctly not treated as flower colour
  NO_COLOUR_STATED       reaches the flowers and simply never states a colour

The first three are parsing failures and are recoverable by fixing
segmentation. COLOUR_PRESENT_MISSED is recoverable immediately.
NO_COLOUR_STATED is a genuine ceiling.

  READS  : Processed Data/experiments/clean_color_categories.csv
                                      species_descriptions_genusfixed.csv
  WRITES : Processed Data/experiments/unknown_diagnosis.csv
                                      unknown_diagnosis_sample.csv

Usage:  python 28_Diagnose_Unknown_Colour.py [--sample-per-cause 12]
"""

from __future__ import annotations

import argparse
import csv
import random
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

BASE = Path("/scratch/dp23301/Thesis")
EXP = BASE / "Processed Data" / "experiments"
CATS = EXP / "clean_color_categories.csv"
DESCS = EXP / "species_descriptions_genusfixed.csv"

csv.field_size_limit(sys.maxsize)

FLOWER_ORGAN = re.compile(
    r"\b(flowers?|florets?|corollas?|petals?|perianth|calyx|sepals?|tepals?|"
    r"blossoms?|spathe)\b", re.I)

# Vegetative and structural terms. Presence of these means the text really is a
# botanical description, even when it never reaches the flowers.
MORPHOLOGY = re.compile(
    r"\b(leaves|leaflets?|leaf|stems?|branch(es|lets)?|petioles?|lamina|"
    r"inflorescences?|racemes?|panicles?|spikes?|umbels?|cymes?|bracts?|"
    r"ovary|stamens?|styles?|capsules?|seeds?|fruits?|berry|berries|drupe|"
    r"herbs?|shrubs?|trees?|glabrous|pubescent|hairy|rhizomes?|roots?|"
    r"tendrils?|stipules?|achenes?|follicles?)\b", re.I)

# Only words that name a colour on their own. 'pale' and 'dark' are modifiers,
# and counting them was inflating the recoverable estimate with matches like
# 'dark green leaves'.
COLOUR = re.compile(
    r"\b(white|yellow|red|pink|purple|blue|greenish|orange|violet|crimson|"
    r"scarlet|lilac|mauve|rose|cream|magenta|maroon|golden|"
    r"whitish|yellowish|reddish|purplish|bluish|pinkish)\b", re.I)

# Colour words attached to these are not flower colour.
NON_FLORAL = re.compile(
    r"\b(fruits?|berry|berries|drupes?|capsules?|seeds?|leaves|leaf|stems?|"
    r"bark|roots?|wood|rhizomes?|branch(es|lets)?)\b", re.I)

# Structures that carry their own colour without it being the flower's colour.
# Checking a sample showed most apparent 'misses' were of this kind - 'Pappus
# white', 'filaments white', 'white stellate hairy', 'white-margined' - where
# declining to assign a flower colour was the correct call, not an error.
APPENDAGE = re.compile(
    r"\b(hairs?|hairy|pappus|filaments?|margins?|margined|scarious|ciliate|"
    r"pubescen(t|ce)|tomentose|villous|puberulous|stellate|bristles?|"
    r"anthers?|styles?|stigmas?|glands?|scales?|veins?|midribs?)\b", re.I)

PROXIMITY = 60  # characters between a colour word and an organ word


def near(text: str, colour_match, pattern) -> bool:
    lo = max(0, colour_match.start() - PROXIMITY)
    hi = min(len(text), colour_match.end() + PROXIMITY)
    return bool(pattern.search(text[lo:hi]))


def diagnose(text: str) -> tuple[str, str]:
    """Return (cause, evidence)."""
    t = (text or "").strip()
    if not t:
        return "EMPTY", ""

    has_morph = bool(MORPHOLOGY.search(t))
    if not has_morph:
        digits = sum(c.isdigit() for c in t)
        if digits > len(t) * 0.3:
            return "NOT_A_DESCRIPTION", "mostly digits (index run)"
        if t.isupper() and len(t.split()) <= 3:
            return "NOT_A_DESCRIPTION", "family/section heading"
        if t.startswith("(") or len(t) < 120:
            return "NOT_A_DESCRIPTION", "citation or fragment"
        return "NOT_A_DESCRIPTION", "no morphological vocabulary"

    if not FLOWER_ORGAN.search(t):
        return "TRUNCATED_PRE_FLOWER", f"morphology present, stops at {len(t)} chars"

    floral, non_floral, appendage = [], [], []
    for m in COLOUR.finditer(t):
        window = t[max(0, m.start() - 40):m.end() + 40]
        if APPENDAGE.search(window):
            appendage.append(m.group(0))
        elif near(t, m, FLOWER_ORGAN):
            floral.append(m.group(0))
        elif near(t, m, NON_FLORAL):
            non_floral.append(m.group(0))
    if floral:
        return "COLOUR_PRESENT_MISSED", f"colour on flower organ: {sorted(set(floral))[:4]}"
    if appendage:
        return "COLOUR_ON_APPENDAGE", f"colour on hairs/pappus/etc: {sorted(set(appendage))[:4]}"
    if non_floral:
        return "COLOUR_NON_FLORAL", f"colour only near non-floral: {sorted(set(non_floral))[:4]}"
    return "NO_COLOUR_STATED", "reaches flowers, no colour word"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample-per-cause", type=int, default=12,
                    help="rows per cause written out for manual checking")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    with CATS.open(encoding="utf-8-sig") as f:
        cats = list(csv.DictReader(f))
    with DESCS.open(encoding="utf-8-sig") as f:
        texts = {r["species_id"]: (r.get("raw_text") or "") for r in csv.DictReader(f)}

    unknown = [r for r in cats if r["color_category"].strip().upper() == "UNKNOWN"]
    known = [r for r in cats if r["color_category"].strip().upper() not in ("UNKNOWN", "")]
    print(f"Parsed species        : {len(cats)}")
    print(f"  colour found        : {len(known)} ({len(known) / len(cats):.1%})")
    print(f"  UNKNOWN, diagnosing : {len(unknown)} ({len(unknown) / len(cats):.1%})")
    print()

    rows = []
    for r in unknown:
        sid = r["species_id"]
        text = texts.get(sid, "")
        cause, evidence = diagnose(text)
        rows.append({
            "species_id": sid,
            "volume": r.get("volume", ""),
            "cause": cause,
            "evidence": evidence,
            "n_chars": len(text.strip()),
            "text_head": text.strip()[:300].replace("\n", " "),
        })

    counts = Counter(r["cause"] for r in rows)
    n = len(rows)

    RECOVERABLE = {
        "COLOUR_PRESENT_MISSED": "recoverable now (no re-parsing needed)",
        "EMPTY": "recoverable by fixing segmentation",
        "NOT_A_DESCRIPTION": "recoverable by fixing segmentation",
        "TRUNCATED_PRE_FLOWER": "recoverable by fixing segmentation",
        "COLOUR_ON_APPENDAGE": "genuine - extractor was right to decline",
        "COLOUR_NON_FLORAL": "genuine - colour is not floral",
        "NO_COLOUR_STATED": "genuine ceiling - Flora omits colour",
    }

    print("Cause breakdown")
    print("=" * 74)
    for cause, c in counts.most_common():
        med = statistics.median(
            [r["n_chars"] for r in rows if r["cause"] == cause] or [0])
        print(f"  {cause:22s} {c:5d}  {c / n:6.1%}   median {med:5.0f} chars   "
              f"{RECOVERABLE[cause]}")

    now = counts["COLOUR_PRESENT_MISSED"]
    reparse = counts["EMPTY"] + counts["NOT_A_DESCRIPTION"] + counts["TRUNCATED_PRE_FLOWER"]
    genuine = (counts["NO_COLOUR_STATED"] + counts["COLOUR_NON_FLORAL"]
               + counts["COLOUR_ON_APPENDAGE"])

    print()
    print("Recoverability")
    print("=" * 74)
    print(f"  immediately (text already carries the colour) : {now:5d}  {now / n:6.1%}")
    print(f"  by fixing segmentation                       : {reparse:5d}  {reparse / n:6.1%}")
    print(f"  genuine ceiling                              : {genuine:5d}  {genuine / n:6.1%}")
    print()

    # 68% of colour-bearing species survive GBIF and environment joins, so scale
    # any recovery by that to get species actually added to the analysis.
    survival = 1174 / len(known)
    print(f"Species currently in the ecological analysis    : 1174")
    print(f"  (survival rate of colour-bearing species: {survival:.1%})")
    for label, k in (("immediate only", now), ("immediate + re-parse", now + reparse)):
        print(f"  if we recover {label:22s}: +{k * survival:4.0f} species "
              f"-> {1174 + k * survival:.0f} total "
              f"({(1174 + k * survival) / 1174 - 1:+.0%})")
    print()

    out = EXP / "unknown_diagnosis.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out.name} ({len(rows)} rows)")

    rng = random.Random(args.seed)
    sample = []
    for cause in counts:
        pool = [r for r in rows if r["cause"] == cause]
        sample.extend(rng.sample(pool, min(args.sample_per_cause, len(pool))))
    sample_path = EXP / "unknown_diagnosis_sample.csv"
    with sample_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(sample[0]) + ["manual_verdict"])
        w.writeheader()
        for r in sample:
            w.writerow({**r, "manual_verdict": ""})
    print(f"wrote {sample_path.name} ({len(sample)} rows for manual checking)")


if __name__ == "__main__":
    main()
