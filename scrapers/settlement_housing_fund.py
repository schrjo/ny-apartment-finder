"""Scraper for Settlement Housing Fund waiting list/re-rentals."""
from __future__ import annotations

from typing import Dict, List
import re

import requests
from bs4 import BeautifulSoup, Tag


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
)

URL = "https://www.settlementhousingfund.org/find-housing/"


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


def _text_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _is_waiting_list_heading(text: str) -> bool:
    key = _text_key(text)
    return "waiting list" in key and "re rentals" in key


def _extract_waiting_list_items(soup: BeautifulSoup) -> List[Tag]:
    for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "strong"]):
        heading_text = heading.get_text(" ", strip=True)
        if not heading_text or not _is_waiting_list_heading(heading_text):
            continue

        cursor = heading
        while cursor:
            cursor = cursor.find_next()
            if cursor is None:
                break
            if cursor.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                break
            if cursor.name == "ul":
                return cursor.find_all("li")

    return []


def _parse_listing(li: Tag) -> Dict | None:
    text = li.get_text(" ", strip=True)
    if not text:
        return None

    url_tag = li.find("a", href=True)
    application_url = url_tag["href"].strip() if url_tag else URL

    core_text = text.split("|", 1)[0].strip()
    # Keep the full listing text in title so notifications include all context.
    title = core_text
    excerpt = None

    raw_key = f"{core_text}|{application_url}"
    listing_id = _normalize(raw_key) or _normalize(text) or _normalize(application_url)
    if not listing_id:
        return None

    return {
        "id": listing_id,
        "canonical_id": f"shf:{listing_id}",
        "title": title,
        "url": application_url,
        "website_url": URL,
        "source": "Settlement Housing Fund",
        "city": None,
        "excerpt": excerpt,
        "price": None,
        "price_value": None,
    }


def scrape() -> List[Dict]:
    soups: List[BeautifulSoup] = []
    request_variants = (
        {"User-Agent": USER_AGENT},
        None,
    )
    for headers in request_variants:
        try:
            resp = requests.get(URL, headers=headers, timeout=20)
            resp.raise_for_status()
        except Exception:
            continue
        soups.append(BeautifulSoup(resp.text, "html.parser"))

    if not soups:
        return []

    items: List[Tag] = []
    for soup in soups:
        items = _extract_waiting_list_items(soup)
        if items:
            break

    results: List[Dict] = []
    seen = set()
    for li in items:
        listing = _parse_listing(li)
        if not listing:
            continue
        canonical_id = listing["canonical_id"]
        if canonical_id in seen:
            continue
        seen.add(canonical_id)
        results.append(listing)

    return results
