import csv
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = Path("/scratch/dp23301/Thesis")
base_url = "https://bsi.gov.in/page/en/flora-of-india"

target_volumes = [
    "Vol. 1", "Vol. 2", "Vol. 3", "Vol. 4", "Vol. 5", "Vol. 12", "Vol. 13", "Vol. 23"
]

output_csv = str(BASE / "raw_data" / "flora_of_india_volumes.csv")

response = requests.get(base_url)
if response.status_code != 200:
    print(f"Failed to fetch page: status code {response.status_code}")
    exit(1)

soup = BeautifulSoup(response.text, "html.parser")
rows = soup.select("table tr")

volume_data = []

for row in rows:
    cells = row.find_all("td")
    if len(cells) < 3:
        continue
    title = cells[1].text.strip()
    link_tag = cells[2].find("a")
    pdf_link = link_tag["href"] if link_tag else None

    if any(vol in title for vol in target_volumes) and pdf_link:
        if not pdf_link.startswith("http"):
            pdf_link = "https://bsi.gov.in" + pdf_link

        volume_data.append([title, pdf_link])
        print(f"Found volume: {title}, PDF link: {pdf_link}")

with open(output_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Volume Title", "PDF URL"])
    writer.writerows(volume_data)

print(f"Scraping complete. Volume links saved to {output_csv}")
