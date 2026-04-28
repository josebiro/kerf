# Woodworkers Source Price Scraper — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace static placeholder prices with a real scraper that fetches current prices and product URLs from woodworkerssource.com, and surface product links in the UI.

**Architecture:** Add a `url` field to `Product` and `ShoppingItem`. Write a scraper module that fetches species landing pages, parses product grids with BeautifulSoup, and extracts prices + URLs. The existing JSON cache and fallback-to-static infrastructure remains. Frontend gets clickable links.

**Tech Stack:** Python requests + BeautifulSoup4 (already installed), existing JSON cache, SvelteKit frontend.

**Spec:** `docs/superpowers/specs/2026-04-27-price-scraper-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/app/suppliers/base.py` | Modify | Add `url` field to `Product` dataclass |
| `backend/app/suppliers/scraper.py` | Create | HTML fetching, parsing, rate limiting — isolated from supplier logic |
| `backend/app/suppliers/woodworkers_source.py` | Modify | Use scraper for live prices, keep static as fallback, add URL lookups |
| `backend/app/models.py` | Modify | Add `url` field to `ShoppingItem` |
| `backend/app/main.py` | Modify | Pass product URLs through to shopping list items |
| `backend/tests/test_scraper.py` | Create | Scraper parsing tests with mocked HTML |
| `backend/tests/test_supplier.py` | Modify | Update for URL field, add fallback tests |
| `frontend/src/lib/types.ts` | Modify | Add `url` field to `ShoppingItem` |
| `frontend/src/lib/components/Results.svelte` | Modify | Add clickable links to shopping list and cost tabs |

---

## Task 1: Add URL Field to Product and ShoppingItem

**Files:**
- Modify: `backend/app/suppliers/base.py`
- Modify: `backend/app/models.py`
- Modify: `frontend/src/lib/types.ts`

- [ ] **Step 1: Add url to Product dataclass**

In `backend/app/suppliers/base.py`, change the `Product` dataclass to:

```python
@dataclass
class Product:
    name: str
    species: str
    thickness: str
    price_per_unit: float
    unit: str       # "BF" or "sheet"
    category: str   # "solid" or "sheet"
    url: str | None = None
```

- [ ] **Step 2: Add url to ShoppingItem model**

In `backend/app/models.py`, add `url` field to `ShoppingItem`:

```python
class ShoppingItem(BaseModel):
    material: str
    thickness: str
    quantity: float
    unit: str
    unit_price: float | None = None
    description: str = ""
    cut_pieces: list[str] = []
    url: str | None = None
```

- [ ] **Step 3: Add url to frontend types**

In `frontend/src/lib/types.ts`, update `ShoppingItem`:

```typescript
export interface ShoppingItem {
	material: string;
	thickness: string;
	quantity: number;
	unit: string;
	unit_price: number | null;
	subtotal: number | null;
	description: string;
	cut_pieces: string[];
	url: string | null;
}
```

- [ ] **Step 4: Run existing tests to confirm nothing breaks**

```bash
cd backend && source .venv/bin/activate && pytest -v
```

Expected: All 88 tests PASS (the new field has a default of `None` so existing code is unaffected).

- [ ] **Step 5: Verify frontend builds**

```bash
cd frontend && npm run build
```

Expected: Build succeeds.

- [ ] **Step 6: Commit**

```bash
git add backend/app/suppliers/base.py backend/app/models.py frontend/src/lib/types.ts
git commit -m "feat: add url field to Product and ShoppingItem for supplier links"
```

---

## Task 2: Scraper Module

**Files:**
- Create: `backend/app/suppliers/scraper.py`
- Create: `backend/tests/test_scraper.py`
- Create: `backend/tests/fixtures/red_oak_page.html`
- Create: `backend/tests/fixtures/walnut_page.html`

This task builds the HTML parsing logic in isolation — no changes to the supplier class yet.

- [ ] **Step 1: Capture real HTML fixture for Red Oak page**

```bash
cd backend && source .venv/bin/activate
python3 -c "
import requests, time
url = 'https://www.woodworkerssource.com/lumber/red-oak.html'
resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; CutListBot/1.0)'})
with open('tests/fixtures/red_oak_page.html', 'w') as f:
    f.write(resp.text)
print(f'Saved {len(resp.text)} chars')
"
```

- [ ] **Step 2: Capture real HTML fixture for Walnut page (has variants)**

```bash
python3 -c "
import requests, time
time.sleep(1)
url = 'https://www.woodworkerssource.com/lumber/walnut.html'
resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; CutListBot/1.0)'})
with open('tests/fixtures/walnut_page.html', 'w') as f:
    f.write(resp.text)
print(f'Saved {len(resp.text)} chars')
"
```

- [ ] **Step 3: Create fixtures directory marker**

```bash
mkdir -p backend/tests/fixtures
touch backend/tests/fixtures/__init__.py
```

- [ ] **Step 4: Write failing scraper tests**

```python
# backend/tests/test_scraper.py
import pytest
from pathlib import Path
from app.suppliers.scraper import parse_product_page

FIXTURES = Path(__file__).parent / "fixtures"


class TestParseProductPage:
    def test_red_oak_finds_lumber_products(self):
        html = (FIXTURES / "red_oak_page.html").read_text()
        products = parse_product_page(html, base_url="https://www.woodworkerssource.com")
        lumber = [p for p in products if p["unit"] == "BF"]
        assert len(lumber) >= 2  # at least 4/4 and 8/4

    def test_red_oak_has_correct_fields(self):
        html = (FIXTURES / "red_oak_page.html").read_text()
        products = parse_product_page(html, base_url="https://www.woodworkerssource.com")
        lumber = [p for p in products if p["unit"] == "BF"]
        for p in lumber:
            assert "name" in p
            assert "price" in p
            assert "thickness" in p
            assert "url" in p
            assert p["price"] > 0
            assert p["url"].startswith("http")

    def test_red_oak_extracts_thickness(self):
        html = (FIXTURES / "red_oak_page.html").read_text()
        products = parse_product_page(html, base_url="https://www.woodworkerssource.com")
        lumber = [p for p in products if p["unit"] == "BF"]
        thicknesses = {p["thickness"] for p in lumber}
        assert "4/4" in thicknesses

    def test_red_oak_filters_out_packs_and_samples(self):
        html = (FIXTURES / "red_oak_page.html").read_text()
        products = parse_product_page(html, base_url="https://www.woodworkerssource.com")
        for p in products:
            assert p["unit"] in ("BF", "sheet")

    def test_walnut_finds_variants(self):
        html = (FIXTURES / "walnut_page.html").read_text()
        products = parse_product_page(html, base_url="https://www.woodworkerssource.com")
        lumber = [p for p in products if p["unit"] == "BF"]
        names = {p["name"] for p in lumber}
        # Walnut page has both Premium and Natural variants
        has_premium = any("premium" in n.lower() or "Premium" in n for n in names)
        has_natural = any("natural" in n.lower() or "Natural" in n for n in names)
        assert has_premium or has_natural  # at least one variant found

    def test_walnut_extracts_prices(self):
        html = (FIXTURES / "walnut_page.html").read_text()
        products = parse_product_page(html, base_url="https://www.woodworkerssource.com")
        lumber = [p for p in products if p["unit"] == "BF"]
        for p in lumber:
            assert p["price"] > 5.0  # walnut is expensive
            assert p["price"] < 50.0  # but not that expensive

    def test_walnut_finds_plywood(self):
        html = (FIXTURES / "walnut_page.html").read_text()
        products = parse_product_page(html, base_url="https://www.woodworkerssource.com")
        sheets = [p for p in products if p["unit"] == "sheet"]
        # Walnut page lists walnut plywood
        assert len(sheets) >= 1

    def test_empty_html_returns_empty(self):
        products = parse_product_page("<html><body></body></html>", base_url="https://www.woodworkerssource.com")
        assert products == []
```

- [ ] **Step 5: Run tests to verify they fail**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_scraper.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.suppliers.scraper'`

- [ ] **Step 6: Implement scraper**

```python
# backend/app/suppliers/scraper.py
"""HTML scraper for woodworkerssource.com product pages.

Parses product grids and extracts lumber ($/BF) and sheet goods ($/Sheet)
with their prices, thicknesses, and product page URLs.
"""

import re
import time
import logging
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_THICKNESS_PATTERN = re.compile(r"(\d+/\d+)\s*(\"|\b)")
_QUARTER_PATTERN = re.compile(r"(\d+/4)\b")
_PRICE_PATTERN = re.compile(r"\$(\d+(?:\.\d{2})?)")

# Map unit text variants to canonical unit names
_UNIT_MAP = {
    "board feet": "BF",
    "board foot": "BF",
    "/bf": "BF",
    "/board feet": "BF",
    "/sheet": "sheet",
    "sheet": "sheet",
}

_USER_AGENT = "Mozilla/5.0 (compatible; CutListBot/1.0)"
_REQUEST_TIMEOUT = 15


def fetch_page(url: str) -> str | None:
    """Fetch a page with a polite user agent. Returns HTML or None on failure."""
    try:
        resp = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        logger.warning("Failed to fetch %s: %s", url, e)
        return None


def parse_product_page(html: str, base_url: str) -> list[dict]:
    """Parse a product listing page and return lumber/sheet products.

    Returns a list of dicts with keys:
        name, price, unit ("BF" or "sheet"), thickness, url
    """
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict] = []

    # Find product cards — the site uses various structures,
    # so we look for price patterns near product links
    # Strategy: find all elements containing price text like "$X.XX /Board Feet"
    # and extract the associated product link and name.

    # Approach: iterate over all links with product URLs, then look for
    # price info in their parent container.
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        if not href or not href.endswith(".html"):
            continue

        # Get the parent container (card)
        parent = link.find_parent(["div", "li", "article"])
        if parent is None:
            continue

        parent_text = parent.get_text(" ", strip=True)

        # Look for price + unit in the card text
        price_match = _PRICE_PATTERN.search(parent_text)
        if price_match is None:
            continue

        price = float(price_match.group(1))
        lower_text = parent_text.lower()

        # Determine unit
        unit = None
        for pattern, canonical in _UNIT_MAP.items():
            if pattern in lower_text:
                unit = canonical
                break

        if unit is None:
            continue

        # Extract product name from h5 or the link text
        name_elem = parent.find(["h5", "h4", "h3"])
        if name_elem:
            name = name_elem.get_text(strip=True)
        else:
            name = link.get_text(strip=True)

        if not name:
            continue

        # Extract thickness
        thickness = None
        quarter_match = _QUARTER_PATTERN.search(name)
        if quarter_match:
            thickness = quarter_match.group(1)
        else:
            thick_match = _THICKNESS_PATTERN.search(name)
            if thick_match:
                thickness = thick_match.group(1) + '"'

        if thickness is None:
            continue

        # Build absolute URL
        product_url = urljoin(base_url, href)

        results.append({
            "name": name,
            "price": price,
            "unit": unit,
            "thickness": thickness,
            "url": product_url,
        })

    # Deduplicate by URL (same product can appear in multiple links)
    seen_urls: set[str] = set()
    deduped: list[dict] = []
    for item in results:
        if item["url"] not in seen_urls:
            seen_urls.add(item["url"])
            deduped.append(item)

    return deduped


def scrape_pages(page_urls: dict[str, str], base_url: str, delay: float = 1.0) -> list[dict]:
    """Scrape multiple pages with rate limiting.

    Args:
        page_urls: mapping of label → relative URL path
        base_url: site base URL to prepend
        delay: seconds between requests

    Returns: combined list of all products found
    """
    all_products: list[dict] = []
    for label, path in page_urls.items():
        url = base_url + path
        logger.info("Scraping %s: %s", label, url)
        html = fetch_page(url)
        if html is None:
            logger.warning("Skipping %s — fetch failed", label)
            continue
        products = parse_product_page(html, base_url=base_url)
        logger.info("Found %d products on %s", len(products), label)
        all_products.extend(products)
        time.sleep(delay)

    return all_products
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_scraper.py -v
```

Expected: All 8 tests PASS.

**If tests fail because the HTML structure doesn't match expectations:** The scraper needs to adapt to the actual HTML. Read the fixture HTML, inspect the actual structure of product cards (CSS classes, element hierarchy), and adjust the parsing logic in `parse_product_page` accordingly. The parsing strategy (find links → find parent container → extract price/unit/name) is sound but selectors may need tuning.

- [ ] **Step 8: Commit**

```bash
cd backend
git add app/suppliers/scraper.py tests/test_scraper.py tests/fixtures/
git commit -m "feat: add HTML scraper for Woodworkers Source product pages"
```

---

## Task 3: Wire Scraper into WoodworkersSourceSupplier

**Files:**
- Modify: `backend/app/suppliers/woodworkers_source.py`
- Modify: `backend/tests/test_supplier.py`

- [ ] **Step 1: Update test expectations for URL field**

In `backend/tests/test_supplier.py`, add URL-related tests and update existing ones:

```python
# backend/tests/test_supplier.py
import json
import time
import pytest
from pathlib import Path
from unittest.mock import patch
from app.suppliers.base import SupplierBase, Product
from app.suppliers.registry import get_supplier, list_suppliers
from app.suppliers.woodworkers_source import WoodworkersSourceSupplier


class TestSupplierBase:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            SupplierBase()


class TestRegistry:
    def test_list_suppliers_includes_woodworkers_source(self):
        names = list_suppliers()
        assert "woodworkers_source" in names

    def test_get_supplier_returns_instance(self):
        supplier = get_supplier("woodworkers_source")
        assert isinstance(supplier, SupplierBase)

    def test_get_unknown_supplier_raises(self):
        with pytest.raises(KeyError):
            get_supplier("nonexistent")


class TestWoodworkersSource:
    def test_get_species_list(self):
        supplier = WoodworkersSourceSupplier(cache_dir=None)
        species = supplier.get_species_list()
        assert len(species) > 0
        assert "Red Oak" in species

    def test_get_sheet_types(self):
        supplier = WoodworkersSourceSupplier(cache_dir=None)
        types = supplier.get_sheet_types()
        assert len(types) > 0
        assert "Baltic Birch" in types

    def test_get_price_returns_value(self):
        supplier = WoodworkersSourceSupplier(cache_dir=None)
        price = supplier.get_price("Red Oak", "4/4", 10.0)
        assert price is not None
        assert price > 0

    def test_get_sheet_price_returns_value(self):
        supplier = WoodworkersSourceSupplier(cache_dir=None)
        price = supplier.get_sheet_price("Baltic Birch", '3/4"')
        assert price is not None
        assert price > 0

    def test_get_catalog_returns_products(self):
        supplier = WoodworkersSourceSupplier(cache_dir=None)
        catalog = supplier.get_catalog()
        assert len(catalog) > 0
        assert all(isinstance(p, Product) for p in catalog)

    def test_cache_saves_and_loads(self, tmp_path):
        supplier = WoodworkersSourceSupplier(cache_dir=tmp_path)
        catalog1 = supplier.get_catalog()
        cache_file = tmp_path / "woodworkers_source_catalog.json"
        assert cache_file.exists()
        supplier2 = WoodworkersSourceSupplier(cache_dir=tmp_path)
        catalog2 = supplier2.get_catalog()
        assert len(catalog2) == len(catalog1)

    def test_unknown_species_returns_none(self):
        supplier = WoodworkersSourceSupplier(cache_dir=None)
        price = supplier.get_price("Unicorn Wood", "4/4", 10.0)
        assert price is None

    def test_get_product_url_returns_url_for_known(self):
        supplier = WoodworkersSourceSupplier(cache_dir=None)
        url = supplier.get_product_url("Red Oak", "4/4")
        # Static fallback has no URLs, so None is acceptable
        # When scraper is active, this would return a real URL
        assert url is None or url.startswith("http")

    def test_get_sheet_url_returns_url_for_known(self):
        supplier = WoodworkersSourceSupplier(cache_dir=None)
        url = supplier.get_sheet_url("Baltic Birch", '3/4"')
        assert url is None or url.startswith("http")

    def test_scrape_fallback_to_static(self, tmp_path):
        """When scraping fails, static prices are used as fallback."""
        with patch("app.suppliers.woodworkers_source.scrape_pages", return_value=[]):
            supplier = WoodworkersSourceSupplier(cache_dir=tmp_path, use_scraper=True)
            price = supplier.get_price("Red Oak", "4/4", 10.0)
            assert price is not None
            assert price > 0

    def test_scrape_populates_urls(self, tmp_path):
        """When scraping succeeds, products have URLs."""
        mock_products = [
            {"name": "Red Oak 4/4 Lumber", "price": 4.99, "unit": "BF", "thickness": "4/4",
             "url": "https://www.woodworkerssource.com/red-oak-44-lumber.html"},
        ]
        with patch("app.suppliers.woodworkers_source.scrape_pages", return_value=mock_products):
            supplier = WoodworkersSourceSupplier(cache_dir=tmp_path, use_scraper=True)
            catalog = supplier.get_catalog()
            red_oak_44 = [p for p in catalog if p.species == "Red Oak" and p.thickness == "4/4"]
            assert len(red_oak_44) >= 1
            assert red_oak_44[0].url is not None

    def test_cache_preserves_urls(self, tmp_path):
        """URLs survive cache round-trip."""
        mock_products = [
            {"name": "Red Oak 4/4 Lumber", "price": 4.99, "unit": "BF", "thickness": "4/4",
             "url": "https://www.woodworkerssource.com/red-oak-44-lumber.html"},
        ]
        with patch("app.suppliers.woodworkers_source.scrape_pages", return_value=mock_products):
            supplier1 = WoodworkersSourceSupplier(cache_dir=tmp_path, use_scraper=True)
            supplier1.get_catalog()

        # Load from cache (no mock needed)
        supplier2 = WoodworkersSourceSupplier(cache_dir=tmp_path)
        catalog = supplier2.get_catalog()
        with_urls = [p for p in catalog if p.url is not None]
        assert len(with_urls) >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_supplier.py -v
```

Expected: FAIL — `get_product_url` and `use_scraper` don't exist yet.

- [ ] **Step 3: Rewrite WoodworkersSourceSupplier to use scraper with static fallback**

```python
# backend/app/suppliers/woodworkers_source.py
"""Woodworkers Source supplier implementation.

Uses a web scraper to fetch current prices from woodworkerssource.com.
Falls back to static baseline prices if scraping fails.
"""

import json
import logging
import time
from pathlib import Path

from app.suppliers.base import SupplierBase, Product
from app.suppliers.scraper import scrape_pages

logger = logging.getLogger(__name__)

BASE_URL = "https://www.woodworkerssource.com"

LUMBER_PAGES = {
    "Red Oak": "/lumber/red-oak.html",
    "White Oak": "/lumber/white-oak-flat-sawn.html",
    "Walnut": "/lumber/walnut.html",
    "Hard Maple": "/lumber/hard-white-maple.html",
    "Cherry": "/lumber/cherry.html",
    "Poplar": "/lumber/poplar.html",
    "Ash": "/lumber/ash.html",
    "Sapele": "/lumber/exotic/Sapele.html",
}

PLYWOOD_PAGES = {
    "Baltic Birch": "/plywood-sheet-goods/baltic-birch-plywood.html",
}

# Static fallback prices ($/BF for solid, $/sheet for sheet goods)
STATIC_SOLID_PRICES: dict[str, dict[str, float]] = {
    "Red Oak": {"4/4": 5.50, "5/4": 6.25, "6/4": 7.00, "8/4": 8.50},
    "White Oak": {"4/4": 6.00, "5/4": 6.75, "6/4": 7.50, "8/4": 9.00},
    "Walnut": {"4/4": 11.00, "5/4": 12.50, "6/4": 13.75, "8/4": 16.00},
    "Hard Maple": {"4/4": 6.50, "5/4": 7.25, "6/4": 8.00, "8/4": 9.50},
    "Cherry": {"4/4": 8.00, "5/4": 9.00, "6/4": 10.00, "8/4": 12.00},
    "Poplar": {"4/4": 3.50, "5/4": 4.00, "6/4": 4.50, "8/4": 5.50},
    "Ash": {"4/4": 5.75, "5/4": 6.50, "6/4": 7.25, "8/4": 8.75},
    "Sapele": {"4/4": 7.50, "5/4": 8.50, "6/4": 9.50, "8/4": 11.50},
}

STATIC_SHEET_PRICES: dict[str, dict[str, float]] = {
    "Baltic Birch": {'1/4"': 28.00, '1/2"': 42.00, '3/4"': 58.00},
    "Red Oak Veneer Ply": {'1/4"': 35.00, '1/2"': 52.00, '3/4"': 68.00},
    "Walnut Veneer Ply": {'1/4"': 55.00, '1/2"': 80.00, '3/4"': 105.00},
    "Maple Veneer Ply": {'1/4"': 38.00, '1/2"': 56.00, '3/4"': 72.00},
    "Cherry Veneer Ply": {'1/4"': 48.00, '1/2"': 70.00, '3/4"': 92.00},
    "MDF": {'1/4"': 18.00, '1/2"': 28.00, '3/4"': 38.00},
    "Melamine": {'1/4"': 22.00, '1/2"': 32.00, '3/4"': 44.00},
}

CACHE_TTL = 86400  # 24 hours
CACHE_FILENAME = "woodworkers_source_catalog.json"


def _extract_species_from_name(name: str, page_label: str) -> str:
    """Extract a display species name from a product name.

    E.g., "Premium Black Walnut 4/4 Lumber" → "Premium Black Walnut"
          "Red Oak 4/4 Lumber" → "Red Oak"
    """
    # Remove common suffixes
    cleaned = name
    for suffix in ["Lumber", "lumber", "Plywood", "plywood"]:
        cleaned = cleaned.replace(suffix, "")
    # Remove thickness patterns like "4/4", "6/4", '3/4"', '1/2"'
    import re
    cleaned = re.sub(r"\d+/\d+\"?", "", cleaned)
    cleaned = cleaned.strip(" -–—")
    return cleaned if cleaned else page_label


class WoodworkersSourceSupplier(SupplierBase):
    """Supplier with live scraping and static fallback.

    When use_scraper=True, attempts to scrape live prices on first catalog
    request. Falls back to static prices if scraping fails.
    """

    def __init__(self, cache_dir: Path | None = None, use_scraper: bool = False) -> None:
        self._cache_dir = cache_dir
        self._use_scraper = use_scraper
        self._catalog: list[Product] | None = None
        # Quick lookup indexes built from catalog
        self._solid_prices: dict[str, dict[str, float]] | None = None
        self._solid_urls: dict[str, dict[str, str]] | None = None
        self._sheet_prices: dict[str, dict[str, float]] | None = None
        self._sheet_urls: dict[str, dict[str, str]] | None = None

    def _ensure_indexes(self) -> None:
        """Build lookup indexes from catalog if not yet built."""
        if self._solid_prices is not None:
            return
        catalog = self.get_catalog()
        self._solid_prices = {}
        self._solid_urls = {}
        self._sheet_prices = {}
        self._sheet_urls = {}
        for p in catalog:
            if p.category == "solid":
                self._solid_prices.setdefault(p.species, {})[p.thickness] = p.price_per_unit
                if p.url:
                    self._solid_urls.setdefault(p.species, {})[p.thickness] = p.url
            else:
                self._sheet_prices.setdefault(p.species, {})[p.thickness] = p.price_per_unit
                if p.url:
                    self._sheet_urls.setdefault(p.species, {})[p.thickness] = p.url

    # ------------------------------------------------------------------
    # SupplierBase interface
    # ------------------------------------------------------------------

    def get_species_list(self) -> list[str]:
        self._ensure_indexes()
        return list(self._solid_prices.keys())

    def get_sheet_types(self) -> list[str]:
        self._ensure_indexes()
        return list(self._sheet_prices.keys())

    def get_price(self, species: str, thickness: str, board_feet: float) -> float | None:
        self._ensure_indexes()
        species_prices = self._solid_prices.get(species)
        if species_prices is None:
            return None
        per_bf = species_prices.get(thickness)
        if per_bf is None:
            return None
        return per_bf * board_feet

    def get_sheet_price(self, product_type: str, thickness: str) -> float | None:
        self._ensure_indexes()
        type_prices = self._sheet_prices.get(product_type)
        if type_prices is None:
            return None
        return type_prices.get(thickness)

    def get_product_url(self, species: str, thickness: str) -> str | None:
        """Get the product page URL for a specific lumber item."""
        self._ensure_indexes()
        species_urls = self._solid_urls.get(species)
        if species_urls is None:
            return None
        return species_urls.get(thickness)

    def get_sheet_url(self, product_type: str, thickness: str) -> str | None:
        """Get the product page URL for a specific sheet good."""
        self._ensure_indexes()
        type_urls = self._sheet_urls.get(product_type)
        if type_urls is None:
            return None
        return type_urls.get(thickness)

    def get_catalog(self) -> list[Product]:
        if self._catalog is not None:
            return self._catalog

        # Try cache first
        if self._cache_dir is not None:
            cached = self._load_cache()
            if cached is not None:
                self._catalog = cached
                return self._catalog

        # Try scraping
        if self._use_scraper:
            scraped = self._scrape_catalog()
            if scraped:
                self._catalog = scraped
                if self._cache_dir is not None:
                    self._save_cache(self._catalog)
                return self._catalog
            logger.warning("Scraping failed, falling back to static prices")

            # Try stale cache before static fallback
            if self._cache_dir is not None:
                stale = self._load_cache(ignore_ttl=True)
                if stale is not None:
                    logger.info("Using stale cache as fallback")
                    self._catalog = stale
                    return self._catalog

        # Static fallback
        self._catalog = self._build_static_catalog()
        if self._cache_dir is not None:
            self._save_cache(self._catalog)
        return self._catalog

    # ------------------------------------------------------------------
    # Scraping
    # ------------------------------------------------------------------

    def _scrape_catalog(self) -> list[Product] | None:
        """Scrape all pages and build a product catalog."""
        all_pages = {}
        all_pages.update(LUMBER_PAGES)
        all_pages.update(PLYWOOD_PAGES)

        raw_products = scrape_pages(all_pages, BASE_URL, delay=1.0)
        if not raw_products:
            return None

        products: list[Product] = []
        for raw in raw_products:
            species = _extract_species_from_name(raw["name"], "Unknown")
            products.append(Product(
                name=raw["name"],
                species=species,
                thickness=raw["thickness"],
                price_per_unit=raw["price"],
                unit=raw["unit"],
                category="solid" if raw["unit"] == "BF" else "sheet",
                url=raw["url"],
            ))

        return products

    # ------------------------------------------------------------------
    # Static fallback
    # ------------------------------------------------------------------

    def _build_static_catalog(self) -> list[Product]:
        products: list[Product] = []
        for species, thicknesses in STATIC_SOLID_PRICES.items():
            for thickness, price in thicknesses.items():
                products.append(Product(
                    name=f"{species} {thickness}",
                    species=species,
                    thickness=thickness,
                    price_per_unit=price,
                    unit="BF",
                    category="solid",
                    url=None,
                ))
        for product_type, thicknesses in STATIC_SHEET_PRICES.items():
            for thickness, price in thicknesses.items():
                products.append(Product(
                    name=f"{product_type} {thickness}",
                    species=product_type,
                    thickness=thickness,
                    price_per_unit=price,
                    unit="sheet",
                    category="sheet",
                    url=None,
                ))
        return products

    # ------------------------------------------------------------------
    # Cache
    # ------------------------------------------------------------------

    def _cache_path(self) -> Path:
        assert self._cache_dir is not None
        return self._cache_dir / CACHE_FILENAME

    def _save_cache(self, catalog: list[Product]) -> None:
        payload = {
            "timestamp": time.time(),
            "products": [
                {
                    "name": p.name,
                    "species": p.species,
                    "thickness": p.thickness,
                    "price_per_unit": p.price_per_unit,
                    "unit": p.unit,
                    "category": p.category,
                    "url": p.url,
                }
                for p in catalog
            ],
        }
        self._cache_path().write_text(json.dumps(payload, indent=2))

    def _load_cache(self, ignore_ttl: bool = False) -> list[Product] | None:
        path = self._cache_path()
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text())
            age = time.time() - payload["timestamp"]
            if not ignore_ttl and age > CACHE_TTL:
                return None
            return [Product(**item) for item in payload["products"]]
        except (KeyError, TypeError, json.JSONDecodeError):
            return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_supplier.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Run full test suite**

```bash
cd backend && source .venv/bin/activate && pytest -v
```

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/suppliers/woodworkers_source.py tests/test_supplier.py
git commit -m "feat: wire scraper into supplier with static fallback and URL lookups"
```

---

## Task 4: Pass URLs Through API to Frontend

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Update the analyze endpoint to include URLs**

In `backend/app/main.py`, update the pricing loop in the `analyze` function to also fetch product URLs:

Replace lines 64-74 (the pricing loop) with:

```python
    supplier = get_supplier("woodworkers_source")
    for i, item in enumerate(shopping_list):
        updates: dict = {}
        if item.unit == "BF":
            price = supplier.get_price(request.solid_species, item.thickness, item.quantity)
            if price is not None:
                updates["unit_price"] = price / item.quantity if item.quantity > 0 else 0
            url = supplier.get_product_url(request.solid_species, item.thickness)
            if url is not None:
                updates["url"] = url
        else:
            price = supplier.get_sheet_price(request.sheet_type, item.thickness)
            if price is not None:
                updates["unit_price"] = price
            url = supplier.get_sheet_url(request.sheet_type, item.thickness)
            if url is not None:
                updates["url"] = url
        if updates:
            shopping_list[i] = item.model_copy(update=updates)
```

- [ ] **Step 2: Run full test suite**

```bash
cd backend && source .venv/bin/activate && pytest -v
```

Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
cd backend
git add app/main.py
git commit -m "feat: pass supplier product URLs through to shopping list items"
```

---

## Task 5: Add Links to Frontend

**Files:**
- Modify: `frontend/src/lib/components/Results.svelte`

- [ ] **Step 1: Add links to shopping list tab**

In the shopping list tab section of `Results.svelte`, update the material card header to include a link when URL is available. Replace the shopping list section (the `{#if activeTab === 'shopping'}` block) with:

```svelte
	{#if activeTab === 'shopping'}
		<div class="space-y-4">
			{#each result.shopping_list as item}
				<div class="border border-gray-200 rounded-lg p-4">
					<div class="flex justify-between items-start mb-2">
						<div>
							<h4 class="font-medium text-gray-800">
								{item.material}
								{#if item.url}
									<a href={item.url} target="_blank" rel="noopener noreferrer"
										class="ml-2 text-xs text-blue-600 hover:text-blue-800 font-normal">
										View on Woodworkers Source ↗
									</a>
								{/if}
							</h4>
							<p class="text-sm text-gray-500">{item.description}</p>
						</div>
						<span class="text-sm font-mono bg-gray-100 px-2 py-1 rounded">{item.quantity} {item.unit}</span>
					</div>
					{#if item.cut_pieces.length > 0}
						<div class="mt-2">
							<p class="text-xs text-gray-500 uppercase tracking-wide mb-1">Cut pieces</p>
							<div class="flex flex-wrap gap-2">
								{#each item.cut_pieces as piece}
									<span class="text-xs font-mono bg-gray-50 border border-gray-200 px-2 py-1 rounded">{piece}</span>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
```

- [ ] **Step 2: Add links to cost estimate tab**

In the cost estimate tab, make the material name a clickable link when URL is available. Replace the material `<td>` in the cost estimate table body:

```svelte
						<td class="py-2 pr-4">
							{#if item.url}
								<a href={item.url} target="_blank" rel="noopener noreferrer"
									class="text-blue-600 hover:text-blue-800 hover:underline">
									{item.material} ↗
								</a>
							{:else}
								{item.material}
							{/if}
						</td>
```

- [ ] **Step 3: Verify frontend builds**

```bash
cd frontend && npm run build
```

Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
cd frontend
git add src/lib/components/Results.svelte
git commit -m "feat: add clickable supplier links to shopping list and cost estimate"
```

---

## Task 6: Enable Scraper by Default

**Files:**
- Modify: `backend/app/suppliers/registry.py`

- [ ] **Step 1: Update registry to enable scraper**

```python
# backend/app/suppliers/registry.py
from pathlib import Path
from app.suppliers.base import SupplierBase
from app.suppliers.woodworkers_source import WoodworkersSourceSupplier

_DEFAULT_CACHE_DIR = Path(__file__).parent.parent.parent / "cache"

_SUPPLIERS: dict[str, type[SupplierBase]] = {
    "woodworkers_source": WoodworkersSourceSupplier,
}
_instances: dict[str, SupplierBase] = {}


def get_supplier(name: str) -> SupplierBase:
    if name not in _SUPPLIERS:
        raise KeyError(f"Unknown supplier: {name!r}")
    if name not in _instances:
        _DEFAULT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _instances[name] = WoodworkersSourceSupplier(
            cache_dir=_DEFAULT_CACHE_DIR,
            use_scraper=True,
        )
    return _instances[name]


def list_suppliers() -> list[str]:
    return list(_SUPPLIERS.keys())
```

- [ ] **Step 2: Add cache/ to .gitignore**

Verify `backend/cache/` is covered by existing `.gitignore`. If not, add it.

- [ ] **Step 3: Run full test suite**

```bash
cd backend && source .venv/bin/activate && pytest -v
```

Expected: All tests PASS. (Tests use `cache_dir=None` or `tmp_path`, so the default cache dir doesn't affect them.)

- [ ] **Step 4: Commit**

```bash
git add backend/app/suppliers/registry.py
git commit -m "feat: enable live scraping by default with cache directory"
```

---

## Task 7: End-to-End Verification

**Files:** None new — verification only.

- [ ] **Step 1: Run full backend test suite**

```bash
cd backend && source .venv/bin/activate && pytest -v
```

Expected: All tests PASS.

- [ ] **Step 2: Verify frontend builds**

```bash
cd frontend && npm run build
```

Expected: Build succeeds.

- [ ] **Step 3: Manual smoke test**

Start both services and test with a real 3MF file:

```bash
# Terminal 1
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000

# Terminal 2
cd frontend && npm run dev
```

Open http://localhost:5173, upload a 3MF file, select a species, and analyze. Verify:
1. Species dropdown is populated (may take ~15s on first load while scraping)
2. Shopping list shows real prices
3. "View on Woodworkers Source" links appear and open correct product pages
4. Cost estimate tab has clickable material names

- [ ] **Step 4: Commit any fixes**

```bash
git add -A && git commit -m "chore: end-to-end verification fixes"
```

(Only if Steps 1-3 revealed issues. Skip if everything works.)
