"""Scraper for MGNY Consulting affordable housing listings.

Scrapes https://mgnyconsulting.com/listings/ for affordable housing
opportunities in NYC.
"""
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
import re


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
)

AJAX_URL = "https://mgnyconsulting.com/wp-admin/admin-ajax.php"


def scrape() -> List[Dict]:
    """Scrape MGNY Consulting and return list of listings."""
    base_url = "https://mgnyconsulting.com/listings/"
    headers = {"User-Agent": USER_AGENT}
    data = {
        "action": "listing_filter",
        "page": "1",
        "income_range": "all-income",
        "boroughs[]": "all-boroughs",
    }

    try:
        resp = requests.post(
            AJAX_URL,
            data=data,
            headers={
                **headers,
                "Referer": base_url,
                "X-Requested-With": "XMLHttpRequest",
            },
            timeout=15,
        )
        resp.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results: List[Dict] = []

    for card in soup.select("div.listings__post-item"):
        link = card.find("a", href=True)
        if not link:
            continue
        href = link["href"]
        if "/listing/" not in href:
            continue

        listing_id = href.split("/listing/")[-1].rstrip("/")
        title_tag = card.select_one(".listings__post-item--title")
        addr_tag = card.select_one(".listings__post-item--address")
        income_tag = card.select_one(".listings__post-item--price")
        units_tag = card.select_one(".listings__post-item--units")

        title = title_tag.get_text(strip=True) if title_tag else listing_id
        address = addr_tag.get_text(" ", strip=True) if addr_tag else ""
        income_range = income_tag.get_text(" ", strip=True) if income_tag else ""
        units = units_tag.get_text(" ", strip=True) if units_tag else ""

        borough = None
        addr_lower = address.lower()
        if "brooklyn" in addr_lower:
            borough = "Brooklyn"
        elif "queens" in addr_lower:
            borough = "Queens"
        elif "bronx" in addr_lower:
            borough = "Bronx"
        elif "manhattan" in addr_lower or "new york, ny" in addr_lower:
            borough = "Manhattan"
        elif "staten island" in addr_lower:
            borough = "Staten Island"

        results.append(
            {
                "id": listing_id,
                "canonical_id": f"mgny:{listing_id}",
                "title": title,
                "url": href if href.startswith("http") else f"https://mgnyconsulting.com{href}",
                "source": "MGNY Consulting",
                "city": borough,
                "excerpt": f"{address}. Income: {income_range}. {units}".strip(),
                "price": None,
                "price_value": None,
            }
        )

    return results
