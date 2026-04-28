"""
HTML scraper for Woodworkers Source product listing pages.

Parses category pages and extracts lumber ($/BF) and sheet good ($/Sheet)
products with their prices, URLs, and thickness details.
"""

import re
import time
import logging
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Units to keep → canonical label
_KEEP_UNITS = {
    "/Board Feet": "BF",
    "Board Feet": "BF",
    "/Sheet": "sheet",
}

# Thickness patterns to extract from product names
_THICKNESS_RE = re.compile(
    r"""
    (?:
        (\d+/\d+)       # fraction like 4/4, 8/4, 3/4
        |
        (\d+(?:\.\d+)?") # decimal with inch mark like 3/4", 1/2"
    )
    """,
    re.VERBOSE,
)

# Dollar amount pattern
_PRICE_RE = re.compile(r"\$\s*([\d,]+(?:\.\d{1,2})?)")


def _extract_thickness(name: str) -> Optional[str]:
    """Pull the first thickness indicator from a product name."""
    m = _THICKNESS_RE.search(name)
    if not m:
        return None
    return m.group(1) or m.group(2)


def _parse_price(text: str) -> Optional[float]:
    """Extract a dollar amount from a string like '$4.99'."""
    m = _PRICE_RE.search(text)
    if not m:
        return None
    return float(m.group(1).replace(",", ""))


def _unit_label(qty_label_text: str) -> Optional[str]:
    """Map a raw qtyLabel text to a canonical unit or None to skip."""
    text = qty_label_text.strip()
    return _KEEP_UNITS.get(text)


def parse_product_page(html: str, base_url: str = "https://www.woodworkerssource.com") -> list[dict]:
    """
    Parse a Woodworkers Source category HTML page.

    Returns a list of product dicts with keys:
        name      - product name string
        price     - float price per unit
        unit      - "BF" or "sheet"
        thickness - thickness string like "4/4" or '3/4"', or None
        url       - absolute product URL

    Products with units other than BF or sheet are filtered out.
    Products are deduplicated by URL.
    """
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("div", class_="category-item")

    seen_urls: set[str] = set()
    products: list[dict] = []

    for card in cards:
        # --- unit label ---
        qty_label_el = card.find("span", class_="qtyLabel")
        if not qty_label_el:
            continue
        unit = _unit_label(qty_label_el.get_text())
        if unit is None:
            continue

        # --- price ---
        price_div = card.find("div", class_="item-price")
        if not price_div:
            continue
        price = _parse_price(price_div.get_text())
        if price is None or price <= 0:
            continue

        # --- name & URL from h5 > a ---
        h5 = card.find("h5")
        if not h5:
            continue
        link_el = h5.find("a")
        if not link_el:
            continue
        name = link_el.get_text(strip=True)
        href = link_el.get("href", "")
        url = href if href.startswith("http") else urljoin(base_url, href)

        # Deduplicate by URL
        if url in seen_urls:
            continue
        seen_urls.add(url)

        thickness = _extract_thickness(name)

        products.append(
            {
                "name": name,
                "price": price,
                "unit": unit,
                "thickness": thickness,
                "url": url,
            }
        )

    return products


def fetch_page(url: str, headers: Optional[dict] = None, timeout: int = 15) -> str:
    """
    Fetch a single page and return its HTML text.

    Raises requests.HTTPError on non-2xx responses.
    """
    default_headers = {
        "User-Agent": "Mozilla/5.0 (compatible; CutListBot/1.0)",
    }
    if headers:
        default_headers.update(headers)

    resp = requests.get(url, headers=default_headers, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def scrape_pages(
    page_urls: list[str],
    base_url: str = "https://www.woodworkerssource.com",
    delay: float = 1.0,
) -> list[dict]:
    """
    Fetch and parse multiple category pages, returning a combined product list.

    Applies a polite delay between requests. Deduplication happens within each
    page; products with identical URLs across pages are also de-duplicated.

    Args:
        page_urls: List of category page URLs to scrape.
        base_url:  Base URL for resolving relative hrefs.
        delay:     Seconds to wait between requests.

    Returns:
        Combined list of product dicts (de-duplicated by URL).
    """
    all_products: list[dict] = []
    seen_urls: set[str] = set()

    for i, url in enumerate(page_urls):
        if i > 0:
            time.sleep(delay)
        try:
            html = fetch_page(url)
            products = parse_product_page(html, base_url=base_url)
            for p in products:
                if p["url"] not in seen_urls:
                    seen_urls.add(p["url"])
                    all_products.append(p)
            logger.debug("Scraped %d products from %s", len(products), url)
        except Exception as exc:
            logger.warning("Failed to scrape %s: %s", url, exc)

    return all_products
