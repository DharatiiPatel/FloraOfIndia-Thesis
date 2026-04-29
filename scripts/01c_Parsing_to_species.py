import re
import csv
from pathlib import Path

# Base paths for Sapelo
BASE_DIR = Path("/scratch/dp23301/Thesis")
RAW_DIR = BASE_DIR / "raw_data"           # <-- your folder with all TXT volumes
PROCESSED_DIR = BASE_DIR / "Processed Data"
OUTPUT_CSV = PROCESSED_DIR / "flora_of_india_species_descriptions.csv"

# Regex to catch numbered headings like "15. Anemone tetrasepala Royle ..."
HEADING_PATTERN = re.compile(r"\n\s*(\d+)\.\s+([A-Z][^\n]+)")


def extract_blocks_from_text(text: str):
    """
    Given the full OCR text of one volume,
    return a list of (species_id, raw_text) blocks.

    species_id example:
        "15. Anemone tetrasepala Royle, Illus. Bot. Himal. 53.1834; Hook. f. & Thomson in"
    raw_text example:
        "H. Brit. India 1:10.1872.\n\nHerbs, up to 60 cm high, hairy or glabrous; ..."
        (up to just before the next numbered heading)
    """
    text_n = text.replace("\r\n", "\n").replace("\r", "\n")

    matches = list(HEADING_PATTERN.finditer(text_n))
    blocks = []

    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text_n)

        species_id = f"{m.group(1)}. {m.group(2).strip()}"
        block = text_n[start:end].strip()

        # Skip totally empty blocks
        if not block:
            continue

        blocks.append((species_id, block))

    return blocks


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    all_records = []

    txt_files = sorted(RAW_DIR.glob("FLORA OF INDIA VOL*.txt"))
    if not txt_files:
        raise FileNotFoundError(f"No volume TXT files found in {RAW_DIR}")

    print("Found TXT volumes:")
    for f in txt_files:
        print("  -", f.name)

    for txt_path in txt_files:
        # Extract volume number from filename, e.g. "FLORA OF INDIA VOL.1.txt"
        m = re.search(r"VOL\.?\s*(\d+)", txt_path.name)
        if m:
            volume = int(m.group(1))
        else:
            volume = None

        print(f"\nProcessing volume file: {txt_path.name} (volume={volume})")

        text = txt_path.read_text(encoding="utf-8", errors="ignore")
        blocks = extract_blocks_from_text(text)

        print(f"  -> Extracted {len(blocks)} blocks from this volume")

        for species_id, raw_text in blocks:
            all_records.append(
                {
                    "species_id": species_id,
                    "volume": volume,
                    "raw_text": " ".join(raw_text.split())
                }
            )

    # Write combined CSV
    print(f"\nWriting {len(all_records)} records to {OUTPUT_CSV}")
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["species_id", "volume", "raw_text"])
        writer.writeheader()
        writer.writerows(all_records)

    print("Done! Example records:")
    for rec in all_records[:5]:
        print("---")
        print("species_id:", rec["species_id"])
        print("volume:", rec["volume"])
        print("raw_text (truncated):", rec["raw_text"][:120] + "...")


if __name__ == "__main__":
    main()
