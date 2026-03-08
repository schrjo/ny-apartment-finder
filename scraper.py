"""Orchestrator for apartment scrapers.

Loads scraper modules (in `scrapers/`), runs them, filters new
listings using `storage.py`, and notifies via `notifier.py`.

Designed to be run in CI (GitHub Actions) on a schedule. Configure
webhook URLs as repository secrets and expose them in the workflow
as `SLACK_WEBHOOK_URL` or `DISCORD_WEBHOOK_URL` environment variables.
"""
from typing import List, Dict
import importlib
import pkgutil
import logging
from dotenv import load_dotenv

from storage import load_seen, save_seen
from notifier import notify
import os
import re


load_dotenv()


def _apply_filters(listings):
    """Apply environment-driven filters to a list of listing dicts.

    Supported env vars:
    - FILTER_MIN_BEDS: integer minimum bedrooms
    - FILTER_MAX_PRICE: integer maximum price (USD)
    - FILTER_ALLOW_UNKNOWN_PRICE: if 1/true/yes, keep listings with no price_value
    - FILTER_BOROUGHS: comma-separated boroughs (case-insensitive)
    """
    if not listings:
        return []

    min_beds = os.getenv("FILTER_MIN_BEDS")
    max_price = os.getenv("FILTER_MAX_PRICE")
    allow_unknown_price = os.getenv("FILTER_ALLOW_UNKNOWN_PRICE", "1")
    boroughs = os.getenv("FILTER_BOROUGHS")

    try:
        min_beds = int(min_beds) if min_beds is not None and min_beds != "" else None
    except Exception:
        min_beds = None

    try:
        max_price = int(max_price) if max_price is not None and max_price != "" else None
    except Exception:
        max_price = None

    allow_unknown_price = str(allow_unknown_price).strip().lower() in {"1", "true", "yes", "y", "on"}

    boroughs_set = None
    if boroughs:
        boroughs_set = {b.strip().lower() for b in boroughs.split(",") if b.strip()}

    out = []
    for l in listings:
        # beds filter: require beds to be present and >= min_beds
        if min_beds is not None:
            beds = l.get("beds")
            if beds is None:
                continue
            try:
                if int(beds) < min_beds:
                    continue
            except Exception:
                continue

        # price filter: require <= max_price; optionally allow missing prices
        if max_price is not None:
            pv = l.get("price_value")
            if pv is None:
                if not allow_unknown_price:
                    continue
            else:
                try:
                    if int(pv) > max_price:
                        continue
                except Exception:
                    if not allow_unknown_price:
                        continue

        # borough filter: match against 'city' or 'borough' fields
        if boroughs_set is not None:
            city = (l.get("city") or "").lower()
            # also allow matching in title
            title = (l.get("title") or "").lower()
            matched = False
            for b in boroughs_set:
                if b in city or b in title:
                    matched = True
                    break
            if not matched:
                continue

        out.append(l)

    return out

LOGGER = logging.getLogger("ny-scraper")
logging.basicConfig(level=logging.INFO, format="%(message)s")


def _discover_scrapers():
    """Discover scraper modules in the `scrapers` package.

    For simplicity we import all modules under `scrapers` and call
    their `scrape()` function if present.
    """
    scrapers = []
    for finder, name, ispkg in pkgutil.iter_modules(["./scrapers"]):
        module_name = f"scrapers.{name}"
        try:
            mod = importlib.import_module(module_name)
            if hasattr(mod, "scrape"):
                scrapers.append(mod)
        except Exception as e:
            LOGGER.warning("Failed to import %s: %s", module_name, e)
    return scrapers


def run_once():
    scrapers = _discover_scrapers()
    all_listings: List[Dict] = []

    for mod in scrapers:
        try:
            listings = mod.scrape()
            if listings:
                LOGGER.info("%s: found %d listings", mod.__name__, len(listings))
                all_listings.extend(listings)
        except Exception as e:
            LOGGER.warning("Error running scraper %s: %s", mod.__name__, e)

    if not all_listings:
        LOGGER.info("No listings found by any scraper.")
        return

    # Deduplicate by a canonical id so Airtable-form and Reside don't double notify.
    def canonicalize(listing: Dict) -> str:
        if listing.get("canonical_id"):
            return str(listing.get("canonical_id"))
        if listing.get("url"):
            return str(listing.get("url"))
        title = (listing.get("title") or "").strip().lower()
        if title:
            return re.sub(r"[^a-z0-9]+", " ", title).strip()
        return str(listing.get("id"))

    canonical_map = {}
    for l in all_listings:
        c = canonicalize(l)
        l["canonical_id"] = c
        # keep the first seen listing for a canonical id
        if c not in canonical_map:
            canonical_map[c] = l

    all_listings = list(canonical_map.values())
    # Determine unseen listings without immediately marking them seen.
    # Backwards-compatible: check both canonical_id and id.
    seen = load_seen()
    unseen = [
        l
        for l in all_listings
        if (str(l.get("canonical_id")) not in seen) and (str(l.get("id")) not in seen)
    ]
    if not unseen:
        LOGGER.info("No new listings since last run.")
        return

    # Apply user filters (if any) before notifying.
    filtered = _apply_filters(unseen)
    if not filtered:
        LOGGER.info("New listings found (%d) but none matched filters.", len(unseen))
        return

    LOGGER.info("Found %d new listings after filtering — notifying...", len(filtered))
    notify(filtered)

    # Mark only the listings we notified as seen so they won't re-notify.
    # Store canonical ids to avoid double notifications across sources.
    seen.update(str(l.get("canonical_id")) for l in filtered)
    save_seen(seen)


if __name__ == "__main__":
    run_once()
{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": 1,
   "id": "7ceab8c2",
   "metadata": {},
   "outputs": [
    {
     "ename": "ModuleNotFoundError",
     "evalue": "No module named 'bs4'",
     "output_type": "error",
     "traceback": [
      "\u001b[31m---------------------------------------------------------------------------\u001b[39m",
      "\u001b[31mModuleNotFoundError\u001b[39m                       Traceback (most recent call last)",
      "\u001b[36mCell\u001b[39m\u001b[36m \u001b[39m\u001b[32mIn[1]\u001b[39m\u001b[32m, line 2\u001b[39m\n\u001b[32m      1\u001b[39m \u001b[38;5;28;01mimport\u001b[39;00m\u001b[38;5;250m \u001b[39m\u001b[34;01mrequests\u001b[39;00m\n\u001b[32m----> \u001b[39m\u001b[32m2\u001b[39m \u001b[38;5;28;01mfrom\u001b[39;00m\u001b[38;5;250m \u001b[39m\u001b[34;01mbs4\u001b[39;00m\u001b[38;5;250m \u001b[39m\u001b[38;5;28;01mimport\u001b[39;00m BeautifulSoup\n\u001b[32m      4\u001b[39m \u001b[38;5;28;01mdef\u001b[39;00m\u001b[38;5;250m \u001b[39m\u001b[34mtest_reside_ny\u001b[39m():\n\u001b[32m      5\u001b[39m     url = \u001b[33m\"\u001b[39m\u001b[33mhttps://residenewyork.com/property-status/open-market/\u001b[39m\u001b[33m\"\u001b[39m\n",
      "\u001b[31mModuleNotFoundError\u001b[39m: No module named 'bs4'"
     ]
    }
   ],
   "source": [
    "import requests\n",
    "from bs4 import BeautifulSoup\n",
    "\n",
    "def test_reside_ny():\n",
    "    url = \"https://residenewyork.com/property-status/open-market/\"\n",
    "    headers = {\n",
    "        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'\n",
    "    }\n",
    "\n",
    "    print(f\"Fetching: {url}...\")\n",
    "    try:\n",
    "        response = requests.get(url, headers=headers)\n",
    "        response.raise_for_status()\n",
    "        \n",
    "        soup = BeautifulSoup(response.text, 'html.parser')\n",
    "        \n",
    "        # ResideNY uses a specific structure for listings. \n",
    "        # We look for the h2 titles inside property item containers.\n",
    "        listings = soup.find_all('h2', class_='property-title')\n",
    "        \n",
    "        if not listings:\n",
    "            print(\"No listings found. The site structure might have changed or requires JavaScript.\")\n",
    "            return\n",
    "\n",
    "        print(f\"Found {len(listings)} listings:\\n\" + \"-\"*30)\n",
    "        for idx, item in enumerate(listings, 1):\n",
    "            title = item.get_text(strip=True)\n",
    "            # The link is usually the parent or a sibling <a> tag\n",
    "            link = item.find('a')['href'] if item.find('a') else \"No link found\"\n",
    "            print(f\"{idx}. {title}\")\n",
    "            print(f\"   Link: {link}\")\n",
    "            \n",
    "    except Exception as e:\n",
    "        print(f\"Error occurred: {e}\")\n",
    "\n",
    "if __name__ == \"__main__\":\n",
    "    test_reside_ny()"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "3.11.13",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.11.13"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
