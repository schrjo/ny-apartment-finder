"""Example scraper for ResideNY / testing site.

This module exposes a `scrape()` function that returns a list of
listing dicts. Each listing dict should contain at least `id`,
`title`, and `url`. Optional keys: `price`, `posted_at`, `meta`.

Keep this scraper lightweight and safe for running in CI.
"""
from typing import List, Dict
import os
import re
import requests
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
)


def scrape() -> List[Dict]:
    """Scrape example site and return list of listings.

    This implementation is intentionally simple and tolerant of
    missing fields so it works as a test harness for the rest of
    the system.
    """
    url = "https://residenewyork.com/property-status/open-market/"
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    results: List[Dict] = []
    seen_ids = set()

    # Pagination discovery (collect page URLs from the pagination block)
    def discover_pages(first_soup, first_url):
        pag = first_soup.find("div", class_=lambda c: c and "rh_pagination" in c)
        if not pag:
            return [first_url]

        hrefs = [a["href"] for a in pag.find_all("a", href=True)]
        page_map = {}
        for href in hrefs:
            m = re.search(r"/page/(\d+)/", href)
            if m:
                page_map[int(m.group(1))] = href
            else:
                if href.rstrip("/") == first_url.rstrip("/"):
                    page_map[1] = href

        if not page_map:
            return [first_url]

        pages = [page_map[p] for p in sorted(page_map.keys())]
        return pages

    max_pages = int(os.getenv("SCRAPER_MAX_PAGES", "0"))
    pages = discover_pages(soup, url)
    if max_pages and max_pages > 0:
        pages = pages[:max_pages]

    # Iterate pages and extract listings from each
    for page_url in pages:
        try:
            pr = requests.get(page_url, headers=headers, timeout=15)
            pr.raise_for_status()
        except Exception:
            continue
        page_soup = BeautifulSoup(pr.text, "html.parser")

        # Prefer server-rendered listing cards: article.rh_list_card
        for article in page_soup.find_all("article", class_=lambda c: c and "rh_list_card" in c):
            classes = article.get("class") or []
            post_id = None
            for cl in classes:
                m = re.match(r"post-(\d+)", cl)
                if m:
                    post_id = m.group(1)
                    break

            link_tag = article.select_one("figure.rh_list_card__thumbnail a") or article.find("a")
            href = link_tag["href"] if link_tag and link_tag.has_attr("href") else None

            title_tag = article.select_one("h3 a") or article.find("h3")
            title = title_tag.get_text(strip=True) if title_tag else None

            if not title and href:
                title = href

            # try to extract city/borough from article classes like 'property-city-brooklyn'
            city = None
            for cl in classes:
                m = re.match(r"property-city-(\w+)", cl)
                if m:
                    city = m.group(1).replace('-', ' ').title()
                    break

            if title:
                listing_id = f"post:{post_id}" if post_id else (href or f"title:{title}")
                if listing_id not in seen_ids:
                    listing = {"id": listing_id, "title": title, "url": href, "source": "residenewyork"}
                    if city:
                        listing["city"] = city


                    # Extract excerpt from the listing card (fast)
                    excerpt_tag = article.select_one("p.rh_list_card__excerpt")
                    if excerpt_tag:
                        listing["excerpt"] = excerpt_tag.get_text(strip=True)

                    # Try to get price from card text if present (fast). Detail-page fetch
                    # is optional and disabled by default to keep the scraper quick.
                    price_text = None
                    # common card-level price selectors
                    card_price = article.select_one(".price, p.price, .rh_price")
                    if card_price:
                        price_text = card_price.get_text(strip=True)
                    else:
                        # fallback: regex over the article text
                        atxt = article.get_text(separator="\n")
                        m = re.search(r"\$[\d,]+", atxt)
                        if m:
                            price_text = m.group(0)

                    if price_text:
                        listing["price"] = price_text
                        mval = re.search(r"\$([\d,]+)", price_text)
                        if mval:
                            try:
                                listing["price_value"] = int(mval.group(1).replace(",", ""))
                            except Exception:
                                pass

                    # (No per-listing detail fetches here — price and excerpt come
                    # from the listing card itself to keep scraping fast.)

                    results.append(listing)
                    seen_ids.add(listing_id)

    # If we didn't find listings via cards, fall back to h3/h2 and RSS as before
    if not results:
        # scan h3 > a links (older layout)
        for h3 in soup.find_all("h3"):
            a = h3.find("a")
            if not a or not a.has_attr("href"):
                continue
            href = a["href"]
            if "/property/" not in href:
                continue
            title = a.get_text(strip=True)
            if not title:
                continue
            listing_id = href
            results.append({"id": listing_id, "title": title, "url": href})

        if not results:
            for h2 in soup.find_all("h2"):
                title = h2.get_text(strip=True)
                if not title:
                    continue
                link_tag = h2.find("a") or h2.find_previous("a")
                url_link = link_tag["href"] if link_tag and link_tag.has_attr("href") else None
                listing_id = url_link or f"title:{title}"
                results.append({"id": listing_id, "title": title, "url": url_link})

    # If we didn't find listings in the static HTML, try the site's RSS feed
    if not results:
        feed_link = None
        link_tag = soup.find("link", attrs={"type": "application/rss+xml"}) or soup.find(
            "link", attrs={"type": "application/atom+xml"}
        )
        if link_tag and link_tag.has_attr("href"):
            feed_link = link_tag["href"]

        if feed_link:
            try:
                fr = requests.get(feed_link, headers=headers, timeout=12)
                fr.raise_for_status()
                import xml.etree.ElementTree as ET

                root = ET.fromstring(fr.content)
                for item in root.findall('.//item'):
                    t_el = item.find('title')
                    l_el = item.find('link')
                    t = t_el.text.strip() if t_el is not None and t_el.text else None
                    lnk = l_el.text.strip() if l_el is not None and l_el.text else None
                    if t:
                        listing_id = lnk or f"title:{t}"
                        results.append({"id": listing_id, "title": t, "url": lnk})
            except Exception:
                pass

    return results



if __name__ == "__main__":
    for l in scrape():
        print(l)
