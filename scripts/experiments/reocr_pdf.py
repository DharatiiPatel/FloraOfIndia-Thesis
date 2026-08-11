#!/usr/bin/env python3
"""
Re-OCR a Flora of India PDF with Tesseract 5 at high DPI + light preprocessing.

SAFE BY DESIGN:
  READS  : a PDF you place in raw_data/pdfs/
  WRITES : Processed Data/experiments/reocr_text/<name>.txt   (new text only)
  Never touches your existing raw_data/*.txt or the pipeline.

Usage (run inside SLURM job after loading modules):
  python reocr_pdf.py --pdf "raw_data/pdfs/FLORA OF INDIA VOL.1.pdf" \
                      --out "Processed Data/experiments/reocr_text/VOL.1.txt" \
                      --dpi 400 --psm 6
  Add --max-pages 30 to pilot on the first 30 pages only.
"""

import argparse
import sys
from pathlib import Path

from pdf2image import convert_from_path
from PIL import Image, ImageOps, ImageFilter
import pytesseract


def preprocess(img: Image.Image) -> Image.Image:
    """Light, safe enhancement: grayscale -> autocontrast -> mild sharpen.
    Tesseract 5 does its own binarization (Otsu/Sauvola), so we keep this gentle."""
    g = ImageOps.grayscale(img)
    g = ImageOps.autocontrast(g, cutoff=1)
    g = g.filter(ImageFilter.SHARPEN)
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dpi", type=int, default=400)
    ap.add_argument("--psm", type=int, default=6, help="tesseract page segmentation mode")
    ap.add_argument("--oem", type=int, default=1, help="1 = LSTM engine")
    ap.add_argument("--max-pages", type=int, default=0, help="0 = all pages")
    ap.add_argument("--batch", type=int, default=20, help="pages to render per batch (RAM control)")
    args = ap.parse_args()

    pdf = Path(args.pdf)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not pdf.exists():
        sys.exit(f"PDF not found: {pdf}")

    cfg = f"--oem {args.oem} --psm {args.psm}"
    print(f"Re-OCR: {pdf.name}")
    print(f"  dpi={args.dpi}  psm={args.psm}  oem={args.oem}  max_pages={args.max_pages or 'all'}")

    # find out how many pages to do
    from pdf2image.pdf2image import pdfinfo_from_path
    info = pdfinfo_from_path(str(pdf))
    total = int(info.get("Pages", 0))
    n_do = total if args.max_pages == 0 else min(args.max_pages, total)
    print(f"  total pages in PDF: {total}; processing: {n_do}")

    all_text = []
    done = 0
    first = 1
    while first <= n_do:
        last = min(first + args.batch - 1, n_do)
        pages = convert_from_path(str(pdf), dpi=args.dpi, first_page=first,
                                  last_page=last, fmt="png", grayscale=True)
        for i, page in enumerate(pages):
            img = preprocess(page)
            txt = pytesseract.image_to_string(img, lang="eng", config=cfg)
            all_text.append(txt)
            done += 1
            if done % 10 == 0:
                print(f"    ...{done}/{n_do} pages", flush=True)
        first = last + 1

    out.write_text("\n".join(all_text), encoding="utf-8")
    n_chars = sum(len(t) for t in all_text)
    print(f"Done. Wrote {done} pages, {n_chars:,} chars -> {out}")


if __name__ == "__main__":
    main()
