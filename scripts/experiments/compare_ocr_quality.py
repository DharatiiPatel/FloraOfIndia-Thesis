#!/usr/bin/env python3
"""
Compare OLD vs NEW OCR text quality for the SAME volume.

Applies the same species-heading regex used by 01c_Parsing_to_species.py and
reports objective quality metrics so you can decide if re-OCR is worth it.

Usage:
  python compare_ocr_quality.py \
    --old "raw_data/FLORA OF INDIA VOL.1.txt" \
    --new "Processed Data/experiments/reocr_text/VOL.1.txt"

NOTE: if you ran the pilot on only the first N pages, the NEW file covers fewer
pages than OLD, so compare RATES (%), not raw counts.
"""

import argparse
import re

HEADING = re.compile(r"\n\s*(\d+)\.\s+([A-Z][^\n]+)")
ABBREV_GENUS = re.compile(r"^[A-Z]\.$")
CLEAN_EPITHET = re.compile(r"^[a-z]{3,}$")
# a "garble" signal in a word: a capital letter INSIDE a word, or a digit inside letters
MIDWORD_CAP = re.compile(r"[a-z][A-Z]")
DIGIT_IN_WORD = re.compile(r"[A-Za-z]\d|\d[A-Za-z]")


def analyse(text: str, label: str):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    heads = HEADING.findall(text)
    n = len(heads)
    if n == 0:
        print(f"[{label}] no species headings found (regex mismatch?)")
        return

    n_abbrev = 0
    n_clean_epi = 0
    n_garbled_name = 0
    for _num, name in heads:
        toks = name.split()
        genus = toks[0] if toks else ""
        epithet = toks[1] if len(toks) > 1 else ""
        if ABBREV_GENUS.match(genus):
            n_abbrev += 1
        if CLEAN_EPITHET.match(epithet):
            n_clean_epi += 1
        head_str = " ".join(toks[:2])
        if MIDWORD_CAP.search(head_str) or DIGIT_IN_WORD.search(head_str):
            n_garbled_name += 1

    print(f"── {label} ───────────────────────────────")
    print(f"  species headings parsed        : {n}")
    print(f"  abbreviated genus              : {n_abbrev:5d}  ({100*n_abbrev/n:.1f}%)")
    print(f"  clean epithet (^[a-z]{{3,}}$)    : {n_clean_epi:5d}  ({100*n_clean_epi/n:.1f}%)")
    print(f"  garbled name (midcap/digit)    : {n_garbled_name:5d}  ({100*n_garbled_name/n:.1f}%)")
    print()
    return dict(n=n, abbrev=n_abbrev, clean=n_clean_epi, garbled=n_garbled_name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    args = ap.parse_args()

    old = open(args.old, encoding="utf-8", errors="ignore").read()
    new = open(args.new, encoding="utf-8", errors="ignore").read()

    print("\n========== OCR QUALITY COMPARISON ==========\n")
    a = analyse(old, "OLD (current pipeline text)")
    b = analyse(new, "NEW (re-OCR text)")

    if a and b:
        print("── VERDICT (lower garble% and abbrev% = better) ──")
        d_garble = 100*a["garbled"]/a["n"] - 100*b["garbled"]/b["n"]
        d_clean = 100*b["clean"]/b["n"] - 100*a["clean"]/a["n"]
        print(f"  garbled-name rate change : {d_garble:+.1f} pts (positive = NEW better)")
        print(f"  clean-epithet rate change: {d_clean:+.1f} pts (positive = NEW better)")
        if d_garble > 3 or d_clean > 3:
            print("  -> NEW OCR looks meaningfully better. Worth doing all 8 volumes.")
        else:
            print("  -> Little improvement. Re-OCR may not be worth it; consider GBIF fuzzy match instead.")


if __name__ == "__main__":
    main()
