import requests
from bs4 import BeautifulSoup
import csv

# BSI Flora of India page URL
base_url = "https://bsi.gov.in/page/en/flora-of-india"

# Target volume titles to include (exact or partial matches)
target_volumes = [
    "Vol. 1", "Vol. 2", "Vol. 3", "Vol. 4", "Vol. 5", "Vol. 12", "Vol. 13", "Vol. 23"
]

# Output CSV path for storing volume titles and PDF URLs
output_csv = "../raw_data/flora_of_india_volumes.csv"

# HTTP request to get the page content
response = requests.get(base_url)
if response.status_code != 200:
    print(f"Failed to fetch page: status code {response.status_code}")
    exit(1)

# Parse HTML content
soup = BeautifulSoup(response.text, "html.parser")

# Find all table rows (each volume entry is in a table row)
rows = soup.select("table tr")

volume_data = []

# Parse rows to get volume titles and PDF download links
for row in rows:
    cells = row.find_all("td")
    if len(cells) < 3:
        continue
    title = cells[1].text.strip()
    link_tag = cells[2].find("a")
    pdf_link = link_tag["href"] if link_tag else None

    # Filter based on target volumes
    if any(vol in title for vol in target_volumes) and pdf_link:
        # Complete url if relative
        if not pdf_link.startswith("http"):
            pdf_link = "https://bsi.gov.in" + pdf_link

        volume_data.append([title, pdf_link])
        print(f"Found volume: {title}, PDF link: {pdf_link}")

# Save results to CSV
with open(output_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Volume Title", "PDF URL"])
    writer.writerows(volume_data)

print(f"Scraping complete. Volume links saved to {output_csv}")
