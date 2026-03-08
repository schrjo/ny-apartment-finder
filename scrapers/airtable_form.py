"""Scraper for Airtable form dropdown snapshot.

This expects a JSON snapshot file written by the local
`scripts/airtable_form_receiver.py` or equivalent userscript.

Env vars:
- AIRTABLE_FORM_SNAPSHOT_PATH (default: data/airtable_form_snapshot.json)
"""
from __future__ import annotations

from typing import Dict, List
import json
import os
import re
from pathlib import Path


def _canonicalize(text: str) -> str:
    if not text:
        return ""
    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    return normalized


def scrape() -> List[Dict]:
    snapshot_path = os.getenv("AIRTABLE_FORM_SNAPSHOT_PATH", "data/airtable_form_snapshot.json")
    path = Path(snapshot_path)
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    # expected formats: {items:[...]} or raw list
    if isinstance(data, dict):
        items = data.get("items") or data.get("apartments") or []
    else:
        items = data

    results: List[Dict] = []
    for item in items:
        title = str(item).strip()
        if not title:
            continue
        canonical = _canonicalize(title)
        listing = {
            "id": f"airtable_form:{canonical or title}",
            "title": title,
            "url": None,
            "source": "airtable_form",
            "canonical_id": canonical or title,
        }
        results.append(listing)

    return results


if __name__ == "__main__":
    for l in scrape():
        print(l)
