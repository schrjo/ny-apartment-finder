"""Scraper for Fifth Avenue Committee re-rental availabilities.

Scrapes https://fifthave.org/re-rental-availabilities/ for affordable
housing re-rentals.
"""
from typing import List, Dict
import re
import requests
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
)


def scrape() -> List[Dict]:
    """Scrape Fifth Avenue Committee and return list of listings."""
    url = "https://fifthave.org/re-rental-availabilities/"
    headers = {"User-Agent": USER_AGENT}
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception:
        return []
    
    soup = BeautifulSoup(resp.text, "html.parser")
    lines = [line.strip() for line in soup.get_text("\n", strip=True).splitlines() if line.strip()]
    results: List[Dict] = []

    building_line_re = re.compile(r"^.+\s-\s.+,\s*(Brooklyn|Manhattan|Queens|Bronx)\s+NY$", re.I)
    unit_re = re.compile(r"^Unit\s+[A-Za-z0-9-]+$", re.I)
    key_re = re.compile(r"^(Unit Size|Household Size|AMI|Rent|Min Income|Max Income):$", re.I)

    current_building = ""
    current_address = ""
    index = 0

    while index < len(lines):
        line = lines[index]

        if building_line_re.match(line):
            parts = line.split("-", 1)
            current_building = parts[0].strip()
            current_address = parts[1].strip() if len(parts) > 1 else ""
            index += 1
            continue

        if current_building and unit_re.match(line):
            unit_number = line
            data: Dict[str, str] = {}
            index += 1

            while index < len(lines):
                next_line = lines[index]
                if building_line_re.match(next_line) or unit_re.match(next_line) or next_line.lower().startswith("apply for a re-rental unit"):
                    break

                m = key_re.match(next_line)
                if m and index + 1 < len(lines):
                    key = m.group(1).lower().replace(" ", "_")
                    value = lines[index + 1]

                    if key == "ami" and not value.endswith("%") and index + 2 < len(lines):
                        value2 = lines[index + 2]
                        if value2.endswith("%"):
                            value = f"{value}{value2}"
                            index += 1

                    data[key] = value
                    index += 2
                    continue

                index += 1

            rent_text = data.get("rent")
            if rent_text:
                rent_value = None
                rent_match = re.search(r"\$([0-9,]+(?:\.[0-9]{2})?)", rent_text)
                if rent_match:
                    rent_value = float(rent_match.group(1).replace(",", ""))

                addr_lower = current_address.lower()
                borough = None
                if "brooklyn" in addr_lower:
                    borough = "Brooklyn"
                elif "manhattan" in addr_lower or "new york" in addr_lower:
                    borough = "Manhattan"
                elif "queens" in addr_lower:
                    borough = "Queens"
                elif "bronx" in addr_lower:
                    borough = "Bronx"

                listing_id = re.sub(r"[^a-z0-9]+", "-", f"{current_building}-{unit_number}".lower()).strip("-")
                excerpt_parts = []
                if data.get("unit_size"):
                    excerpt_parts.append(data["unit_size"])
                if data.get("ami"):
                    excerpt_parts.append(f"AMI {data['ami']}")
                if data.get("household_size"):
                    excerpt_parts.append(f"Household: {data['household_size']}")

                results.append(
                    {
                        "id": listing_id,
                        "canonical_id": f"fifthave:{listing_id}",
                        "title": f"{current_building} - {unit_number}",
                        "url": url,
                        "source": "Fifth Avenue Committee",
                        "city": borough,
                        "excerpt": ", ".join(excerpt_parts) if excerpt_parts else current_address,
                        "price": rent_text,
                        "price_value": rent_value,
                    }
                )
            continue

        index += 1

    return results
