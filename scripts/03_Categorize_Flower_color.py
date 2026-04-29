import csv
from pathlib import Path

BASE_DIR = Path("/scratch/dp23301/Thesis")
INPUT_CSV = BASE_DIR / "Processed Data" / "flora_of_india_flower_color_qwen.csv"
OUTPUT_CSV = BASE_DIR / "Processed Data" / "flora_of_india_flower_color_categories.csv"

# -----------------------------
# Category lookup logic
# -----------------------------

def categorize_color(text: str) -> str:
    if not text or text.strip() == "":
        return "UNKNOWN"
    
    t = text.lower()

    # Core color groups
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
    
    # If explicit "no flower colour mentioned"
    if "no flower colour" in t:
        return "UNKNOWN"

    # Catch-all for rare/complex cases
    return "OTHER"


def main():
    print("Loading:", INPUT_CSV)

    with INPUT_CSV.open("r", encoding="utf-8") as f_in, \
         OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f_out:

        reader = csv.DictReader(f_in)
        fieldnames = ["species_id", "volume", "flower_color_free_text", "color_category"]
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        count = 0
        for row in reader:
            species_id = row["species_id"].strip()
            volume = row["volume"].strip()
            color_text = row["flower_color_free_text"].strip()

            category = categorize_color(color_text)

            writer.writerow({
                "species_id": species_id,
                "volume": volume,
                "flower_color_free_text": color_text,
                "color_category": category
            })

            count += 1
            if count % 500 == 0:
                print(f"Processed {count} entries...")

    print(f"Done! Saved categorized colors to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
