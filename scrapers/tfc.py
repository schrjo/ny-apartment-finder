"""Scraper for TF Cornerstone affordable re-rentals.

Scrapes https://tfc.com/about/affordable-re-rentals for rent-stabilized
apartment re-rentals in NYC.
"""
from typing import Dict, List
import re

import requests
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
)

URL = "https://tfc.com/about/affordable-re-rentals"


def _borough_from_title(title: str) -> str | None:
    t = title.lower()
    if "long island city" in t or "queens" in t:
        return "Queens"
    if "brooklyn" in t or "dean" in t:
        return "Brooklyn"
    if "manhattan" in t or "w 37th" in t or "11th avenue" in t:
        return "Manhattan"
    return None


def scrape() -> List[Dict]:
    """Scrape TF Cornerstone and return list of listings."""
    headers = {"User-Agent": USER_AGENT}

    try:
        resp = requests.get(URL, headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results: List[Dict] = []
    seen_ids = set()

    for heading in soup.find_all(["h2", "h3"]):
        heading_text = heading.get_text(strip=True)
        if not heading_text:
            continue

        low = heading_text.lower()
        if any(skip in low for skip in ["amenities", "income requirements", "faq", "join the tfc community", "available re-rentals"]):
            continue

        if not any(tok in heading_text for tok in ["St", "Street", "Ave", "Avenue", "Blvd", "Boulevard"]):
            continue

        listing_id = re.sub(r"[^a-z0-9]+", "-", low).strip("-")
        if not listing_id or listing_id in seen_ids:
            continue
        seen_ids.add(listing_id)

        results.append(
            {
                "id": listing_id,
                "canonical_id": f"tfc:{listing_id}",
                "title": heading_text,
                "url": URL,
                "source": "TF Cornerstone",
                "city": _borough_from_title(heading_text),
                "excerpt": "Rent-stabilized re-rental available",
                "price": None,
                "price_value": None,
            }
        )

    return results
