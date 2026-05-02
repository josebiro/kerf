# Kerf Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign kerf with auth enforcement, dark precision theme, multi-supplier pricing, searchable material selection, user preferences, and a marketing landing page.

**Architecture:** SvelteKit frontend + FastAPI backend, both using Supabase (Postgres + Auth + Storage). Supplier prices crawled offline and cached in Supabase. All endpoints require authentication. Dark CAD-tool-inspired theme replaces current folksy design.

**Tech Stack:** SvelteKit 2 / Svelte 5, Tailwind CSS 4, TypeScript, FastAPI, Python 3.12, Supabase, BeautifulSoup4

**Spec:** `docs/superpowers/specs/2026-05-02-kerf-redesign-design.md`

---

## File Structure

### Backend — New Files
- `backend/app/suppliers/crawler_base.py` — CrawlerBase ABC and CrawledProduct dataclass
- `backend/app/suppliers/knotty_lumber.py` — Knotty Lumber Co crawler
- `backend/app/suppliers/makerstock.py` — Makerstock crawler
- `backend/app/suppliers/db_supplier.py` — SupplierBase impl that reads from Supabase
- `backend/run_crawl.py` — CLI script to run all crawlers
- `backend/tests/test_auth.py` — Auth enforcement tests
- `backend/tests/test_crawler_base.py` — Crawler infrastructure tests
- `backend/tests/test_preferences.py` — Preferences API tests
- `backend/tests/test_catalog.py` — Catalog API tests

### Backend — Modified Files
- `backend/app/main.py` — Auth on all endpoints, new preference/catalog routes
- `backend/app/auth.py` — Remove get_optional_user
- `backend/app/models.py` — Add UserPreferences, CatalogItem models
- `backend/app/database.py` — Add preferences CRUD, catalog queries
- `backend/app/suppliers/registry.py` — Refactor to use DB supplier
- `backend/app/suppliers/woodworkers_source.py` — Refactor to Crawler subclass

### Frontend — New Files
- `frontend/src/lib/components/ProfileMenu.svelte` — Avatar dropdown
- `frontend/src/lib/components/Combobox.svelte` — Searchable select with prices
- `frontend/src/lib/components/CatalogBrowser.svelte` — Slide-over catalog panel
- `frontend/src/lib/components/StepIndicator.svelte` — Upload→Configure→Results
- `frontend/src/lib/components/LandingPage.svelte` — Marketing landing
- `frontend/src/routes/preferences/+page.svelte` — Preferences page

### Frontend — Modified Files
- `frontend/src/app.css` — Complete theme replacement
- `frontend/src/routes/+layout.svelte` — Navbar, profile menu, route guards
- `frontend/src/routes/+page.svelte` — Split auth/unauth views, step indicator
- `frontend/src/routes/login/+page.svelte` — Dark theme restyle
- `frontend/src/routes/projects/+page.svelte` — Dark theme, post-login home
- `frontend/src/lib/api.ts` — Add catalog, preferences API calls
- `frontend/src/lib/types.ts` — Add CatalogItem, UserPreferences types
- `frontend/src/lib/components/Upload.svelte` — Dark theme restyle
- `frontend/src/lib/components/Configure.svelte` — Replace dropdowns with Combobox
- `frontend/src/lib/components/Results.svelte` — Dark theme restyle
- `frontend/src/lib/components/CutLayout.svelte` — Dark theme restyle
- `frontend/src/lib/components/ModelViewer.svelte` — Dark background/materials
- `frontend/src/lib/components/SheetDiagram.svelte` — Dark canvas colors
- `frontend/src/lib/components/BoardDiagram.svelte` — Dark canvas colors

### Database — New Tables (Supabase SQL)
- `suppliers` — Master supplier list
- `supplier_prices` — Crawled price data
- `crawl_runs` — Crawl run log
- `user_preferences` — Per-user settings

---

### Task 1: Database Schema — Create Supabase Tables

**Files:**
- Create: Supabase SQL migration (run via Supabase dashboard or CLI)

- [ ] **Step 1: Create the SQL migration file**

Create `backend/migrations/001_supplier_tables.sql`:

```sql
-- Master supplier list
CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    base_url TEXT NOT NULL,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Crawled price data
CREATE TABLE IF NOT EXISTS supplier_prices (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    supplier_id TEXT REFERENCES suppliers(supplier_id),
    product_type TEXT NOT NULL CHECK (product_type IN ('solid', 'sheet')),
    species_or_name TEXT NOT NULL,
    thickness TEXT NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    unit TEXT NOT NULL CHECK (unit IN ('board_foot', 'sheet', 'linear_foot')),
    url TEXT,
    crawled_at TIMESTAMPTZ NOT NULL,
    UNIQUE (supplier_id, product_type, species_or_name, thickness)
);

-- Crawl run log
CREATE TABLE IF NOT EXISTS crawl_runs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    supplier_id TEXT REFERENCES suppliers(supplier_id),
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    product_count INTEGER DEFAULT 0,
    errors TEXT[]
);

-- User preferences
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id),
    enabled_suppliers TEXT[] DEFAULT ARRAY['woodworkers_source'],
    default_species TEXT,
    default_sheet_type TEXT,
    default_units TEXT DEFAULT 'in' CHECK (default_units IN ('in', 'mm')),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Seed supplier rows
INSERT INTO suppliers (supplier_id, name, base_url) VALUES
    ('woodworkers_source', 'Woodworkers Source', 'https://www.woodworkerssource.com'),
    ('knotty_lumber', 'The Knotty Lumber Co', 'https://theknottylumberco.ca'),
    ('makerstock', 'Makerstock', 'https://makerstock.com')
ON CONFLICT (supplier_id) DO NOTHING;

-- RLS policies
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own preferences"
    ON user_preferences FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own preferences"
    ON user_preferences FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own preferences"
    ON user_preferences FOR UPDATE
    USING (auth.uid() = user_id);

-- supplier_prices and suppliers are read-only for authenticated users
ALTER TABLE supplier_prices ENABLE ROW LEVEL SECURITY;
ALTER TABLE suppliers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users can read suppliers"
    ON suppliers FOR SELECT
    USING (auth.role() = 'authenticated');

CREATE POLICY "Authenticated users can read prices"
    ON supplier_prices FOR SELECT
    USING (auth.role() = 'authenticated');

-- Service role needs full access for crawlers
CREATE POLICY "Service role full access suppliers"
    ON suppliers FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access prices"
    ON supplier_prices FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access crawl_runs"
    ON crawl_runs FOR ALL
    USING (auth.role() = 'service_role');
```

- [ ] **Step 2: Run the migration against Supabase**

Run via Supabase dashboard SQL editor or CLI:
```bash
# If using supabase CLI:
cd backend && supabase db push
# Or paste the SQL into the Supabase dashboard SQL editor
```

- [ ] **Step 3: Verify tables exist**

```bash
cd /home/josebiro/gt/mayor/backend
source .venv/bin/activate
python3 -c "
from app.supabase_client import get_supabase_client
client = get_supabase_client()
# Check suppliers table has seed data
result = client.table('suppliers').select('*').execute()
print(f'Suppliers: {len(result.data)} rows')
for s in result.data:
    print(f'  {s[\"supplier_id\"]}: {s[\"name\"]}')
"
```

Expected: 3 supplier rows (woodworkers_source, knotty_lumber, makerstock)

- [ ] **Step 4: Commit**

```bash
git add backend/migrations/001_supplier_tables.sql
git commit -m "$(cat <<'EOF'
feat: add supplier, pricing, and preferences database schema

New Supabase tables for multi-supplier pricing architecture:
- suppliers: master supplier list with seed data
- supplier_prices: crawled price cache
- crawl_runs: crawl audit log
- user_preferences: per-user supplier toggles and defaults
EOF
)"
```

---

### Task 2: Backend — Auth Enforcement

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/auth.py`
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: Write failing test for auth enforcement**

Create `backend/tests/test_auth.py`:

```python
"""Test that all API endpoints require authentication."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_upload_requires_auth():
    """POST /api/upload should return 401 without auth."""
    response = client.post("/api/upload", files={"file": ("test.3mf", b"fake", "application/octet-stream")})
    assert response.status_code == 401


def test_analyze_requires_auth():
    """POST /api/analyze should return 401 without auth."""
    response = client.post("/api/analyze", json={"session_id": "x", "solid_species": "Red Oak", "sheet_type": "Baltic Birch"})
    assert response.status_code == 401


def test_optimize_requires_auth():
    """POST /api/optimize should return 401 without auth."""
    response = client.post("/api/optimize", json={"parts": [], "shopping_list": [], "solid_species": "Red Oak", "sheet_type": "Baltic Birch"})
    assert response.status_code == 401


def test_species_requires_auth():
    """GET /api/species should return 401 without auth."""
    response = client.get("/api/species")
    assert response.status_code == 401


def test_sheet_types_requires_auth():
    """GET /api/sheet-types should return 401 without auth."""
    response = client.get("/api/sheet-types")
    assert response.status_code == 401


def test_restore_session_requires_auth():
    """POST /api/restore-session should return 401 without auth."""
    response = client.post("/api/restore-session", json={"file_url": "http://example.com/test.3mf"})
    assert response.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/josebiro/gt/mayor/backend
source .venv/bin/activate
python -m pytest tests/test_auth.py -v
```

Expected: All 6 tests FAIL (currently return 400/422, not 401)

- [ ] **Step 3: Add auth dependency to all public endpoints**

In `backend/app/main.py`, add `user: dict = Depends(require_user)` to every endpoint that currently lacks it:

```python
# Line 37: upload_file
@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...), user: dict = Depends(require_user)):

# Line 53: restore_session
@app.post("/api/restore-session", response_model=UploadResponse)
async def restore_session(request: RestoreSessionRequest, user: dict = Depends(require_user)):

# Line 81: analyze
@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest, user: dict = Depends(require_user)):

# Line 131: serve_file
@app.get("/api/files/{session_id}/{filename}")
async def serve_file(session_id: str, filename: str, user: dict = Depends(require_user)):

# Line 141: get_species
@app.get("/api/species")
async def get_species(user: dict = Depends(require_user)):

# Line 146: get_sheet_types
@app.get("/api/sheet-types")
async def get_sheet_types(user: dict = Depends(require_user)):

# Line 396: optimize_cuts
@app.post("/api/optimize", response_model=OptimizeResponse)
async def optimize_cuts(request: OptimizeRequest, user: dict = Depends(require_user)):
```

- [ ] **Step 4: Remove get_optional_user from auth.py**

In `backend/app/auth.py`, remove the `get_optional_user` function (lines 9-31). Update `require_user` to be standalone:

```python
"""Supabase JWT authentication for FastAPI."""

from fastapi import Header, HTTPException

from app.supabase_client import get_supabase_client as _get_supabase_client


async def require_user(
    authorization: str | None = Header(None),
) -> dict:
    """Require an authenticated user. Raises 401 if not authenticated."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        client = _get_supabase_client()
        response = client.auth.get_user(token)
        return {
            "id": response.user.id,
            "email": response.user.email,
        }
    except Exception:
        raise HTTPException(status_code=401, detail="Authentication required")
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /home/josebiro/gt/mayor/backend
python -m pytest tests/test_auth.py -v
```

Expected: All 6 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/main.py backend/app/auth.py backend/tests/test_auth.py
git commit -m "$(cat <<'EOF'
feat: enforce authentication on all API endpoints

All endpoints now require a valid Supabase JWT. Removes
get_optional_user — no more anonymous access to upload,
analyze, optimize, or species/sheet-type lookups.
EOF
)"
```

---

### Task 3: Backend — Crawler Infrastructure

**Files:**
- Create: `backend/app/suppliers/crawler_base.py`
- Create: `backend/tests/test_crawler_base.py`

- [ ] **Step 1: Write failing test for CrawlerBase**

Create `backend/tests/test_crawler_base.py`:

```python
"""Test the crawler base class and CrawledProduct model."""
import pytest
from datetime import datetime, timezone
from app.suppliers.crawler_base import CrawlerBase, CrawledProduct


class FakeCrawler(CrawlerBase):
    supplier_id = "fake_supplier"
    supplier_name = "Fake Supplier"
    base_url = "https://fake.example.com"

    def crawl(self) -> list[CrawledProduct]:
        return [
            CrawledProduct(
                supplier_id=self.supplier_id,
                product_type="solid",
                species_or_name="Red Oak",
                thickness="4/4",
                price=5.50,
                unit="board_foot",
                url="https://fake.example.com/red-oak",
                crawled_at=datetime.now(timezone.utc),
            )
        ]


def test_crawled_product_fields():
    """CrawledProduct stores all required fields."""
    now = datetime.now(timezone.utc)
    p = CrawledProduct(
        supplier_id="test",
        product_type="solid",
        species_or_name="Walnut",
        thickness="8/4",
        price=16.00,
        unit="board_foot",
        url="https://example.com/walnut",
        crawled_at=now,
    )
    assert p.supplier_id == "test"
    assert p.product_type == "solid"
    assert p.species_or_name == "Walnut"
    assert p.thickness == "8/4"
    assert p.price == 16.00
    assert p.unit == "board_foot"
    assert p.crawled_at == now


def test_crawler_subclass_returns_products():
    """A Crawler subclass returns CrawledProduct instances."""
    crawler = FakeCrawler()
    products = crawler.crawl()
    assert len(products) == 1
    assert products[0].species_or_name == "Red Oak"
    assert products[0].supplier_id == "fake_supplier"


def test_crawled_product_rejects_invalid_product_type():
    """CrawledProduct only accepts 'solid' or 'sheet'."""
    with pytest.raises(ValueError):
        CrawledProduct(
            supplier_id="test",
            product_type="invalid",
            species_or_name="Oak",
            thickness="4/4",
            price=5.0,
            unit="board_foot",
            url=None,
            crawled_at=datetime.now(timezone.utc),
        )


def test_crawled_product_rejects_invalid_unit():
    """CrawledProduct only accepts valid units."""
    with pytest.raises(ValueError):
        CrawledProduct(
            supplier_id="test",
            product_type="solid",
            species_or_name="Oak",
            thickness="4/4",
            price=5.0,
            unit="invalid_unit",
            url=None,
            crawled_at=datetime.now(timezone.utc),
        )
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/josebiro/gt/mayor/backend
python -m pytest tests/test_crawler_base.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.suppliers.crawler_base'`

- [ ] **Step 3: Implement CrawlerBase and CrawledProduct**

Create `backend/app/suppliers/crawler_base.py`:

```python
"""Base class for supplier price crawlers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Literal


_VALID_PRODUCT_TYPES = {"solid", "sheet"}
_VALID_UNITS = {"board_foot", "sheet", "linear_foot"}


@dataclass
class CrawledProduct:
    """A single product scraped from a supplier website."""

    supplier_id: str
    product_type: str  # "solid" or "sheet"
    species_or_name: str
    thickness: str
    price: float
    unit: str  # "board_foot", "sheet", or "linear_foot"
    url: str | None
    crawled_at: datetime

    def __post_init__(self):
        if self.product_type not in _VALID_PRODUCT_TYPES:
            raise ValueError(
                f"product_type must be one of {_VALID_PRODUCT_TYPES}, got {self.product_type!r}"
            )
        if self.unit not in _VALID_UNITS:
            raise ValueError(
                f"unit must be one of {_VALID_UNITS}, got {self.unit!r}"
            )


class CrawlerBase(ABC):
    """Abstract base class for supplier crawlers.

    Subclasses must set class attributes:
        supplier_id:   str — unique identifier (e.g. "woodworkers_source")
        supplier_name: str — human-readable name
        base_url:      str — supplier website URL

    And implement:
        crawl() -> list[CrawledProduct]
    """

    supplier_id: str
    supplier_name: str
    base_url: str

    @abstractmethod
    def crawl(self) -> list[CrawledProduct]:
        """Scrape the supplier site and return normalized products."""
        ...
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/josebiro/gt/mayor/backend
python -m pytest tests/test_crawler_base.py -v
```

Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/suppliers/crawler_base.py backend/tests/test_crawler_base.py
git commit -m "$(cat <<'EOF'
feat: add CrawlerBase ABC and CrawledProduct model

Foundation for multi-supplier crawl-and-cache architecture.
Each supplier implements a Crawler subclass that returns
normalized CrawledProduct instances.
EOF
)"
```

---

### Task 4: Backend — Woodworkers Source Crawler Migration

**Files:**
- Modify: `backend/app/suppliers/woodworkers_source.py` — add WoodworkersSourceCrawler class
- Keep existing WoodworkersSourceSupplier for now (removed in Task 6)

- [ ] **Step 1: Write failing test**

Add to `backend/tests/test_crawler_base.py`:

```python
from app.suppliers.woodworkers_source import WoodworkersSourceCrawler


def test_ws_crawler_has_correct_metadata():
    """WoodworkersSourceCrawler has correct supplier_id and base_url."""
    crawler = WoodworkersSourceCrawler()
    assert crawler.supplier_id == "woodworkers_source"
    assert crawler.supplier_name == "Woodworkers Source"
    assert "woodworkerssource.com" in crawler.base_url


def test_ws_crawler_static_fallback():
    """WoodworkersSourceCrawler.crawl() returns products from static prices when scraping disabled."""
    crawler = WoodworkersSourceCrawler(use_scraper=False)
    products = crawler.crawl()
    assert len(products) > 0
    # Should have both solid and sheet products
    solid = [p for p in products if p.product_type == "solid"]
    sheet = [p for p in products if p.product_type == "sheet"]
    assert len(solid) > 0
    assert len(sheet) > 0
    # Check a known product
    red_oak_4_4 = [p for p in solid if p.species_or_name == "Red Oak" and p.thickness == "4/4"]
    assert len(red_oak_4_4) == 1
    assert red_oak_4_4[0].price == 5.50
    assert red_oak_4_4[0].unit == "board_foot"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/josebiro/gt/mayor/backend
python -m pytest tests/test_crawler_base.py::test_ws_crawler_has_correct_metadata -v
```

Expected: FAIL with `ImportError`

- [ ] **Step 3: Add WoodworkersSourceCrawler to woodworkers_source.py**

Append to the end of `backend/app/suppliers/woodworkers_source.py`:

```python
from app.suppliers.crawler_base import CrawlerBase, CrawledProduct
from datetime import datetime, timezone


class WoodworkersSourceCrawler(CrawlerBase):
    """Crawler for Woodworkers Source — scrapes or uses static fallback."""

    supplier_id = "woodworkers_source"
    supplier_name = "Woodworkers Source"
    base_url = BASE_URL

    def __init__(self, use_scraper: bool = True) -> None:
        self._use_scraper = use_scraper

    def crawl(self) -> list[CrawledProduct]:
        now = datetime.now(timezone.utc)
        products: list[CrawledProduct] = []

        if self._use_scraper:
            raw = self._scrape_live()
            if raw:
                return raw

        # Static fallback
        for species, thicknesses in SOLID_PRICES.items():
            for thickness, price in thicknesses.items():
                url = f"{BASE_URL}{LUMBER_PAGES.get(species, '')}" if species in LUMBER_PAGES else None
                products.append(CrawledProduct(
                    supplier_id=self.supplier_id,
                    product_type="solid",
                    species_or_name=species,
                    thickness=thickness,
                    price=price,
                    unit="board_foot",
                    url=url,
                    crawled_at=now,
                ))

        for product_type, thicknesses in SHEET_PRICES.items():
            for thickness, price in thicknesses.items():
                url = f"{BASE_URL}{PLYWOOD_PAGES.get(product_type, '')}" if product_type in PLYWOOD_PAGES else None
                products.append(CrawledProduct(
                    supplier_id=self.supplier_id,
                    product_type="sheet",
                    species_or_name=product_type,
                    thickness=thickness,
                    price=price,
                    unit="sheet",
                    url=url,
                    crawled_at=now,
                ))

        return products

    def _scrape_live(self) -> list[CrawledProduct]:
        """Attempt live scraping, return empty list on failure."""
        now = datetime.now(timezone.utc)
        urls = [BASE_URL + path for path in LUMBER_PAGES.values()]
        urls += [BASE_URL + path for path in PLYWOOD_PAGES.values()]

        try:
            raw = scrape_pages(urls, BASE_URL)
        except Exception as exc:
            logger.warning("scrape_pages failed: %s", exc)
            return []

        if not raw:
            return []

        products: list[CrawledProduct] = []
        for item in raw:
            name = item.get("name", "")
            price = item.get("price")
            unit = item.get("unit", "BF")
            thickness = item.get("thickness")
            url = item.get("url")

            if price is None or price <= 0:
                continue

            category = "solid" if unit == "BF" else "sheet"
            species = _extract_species(name, category)
            thick = thickness or ""
            if category == "sheet" and thick and not thick.endswith('"'):
                thick = thick + '"'

            products.append(CrawledProduct(
                supplier_id=self.supplier_id,
                product_type=category,
                species_or_name=species,
                thickness=thick,
                price=price,
                unit="board_foot" if unit == "BF" else "sheet",
                url=url,
                crawled_at=now,
            ))

        return products
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/josebiro/gt/mayor/backend
python -m pytest tests/test_crawler_base.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/suppliers/woodworkers_source.py backend/tests/test_crawler_base.py
git commit -m "$(cat <<'EOF'
feat: add WoodworkersSourceCrawler using CrawlerBase interface

Migrates the existing scraping + static fallback logic into a
Crawler subclass. The old WoodworkersSourceSupplier class is
kept temporarily for backward compatibility.
EOF
)"
```

---

### Task 5: Backend — Crawl Runner Script

**Files:**
- Create: `backend/run_crawl.py`

- [ ] **Step 1: Create the crawl runner**

Create `backend/run_crawl.py`:

```python
#!/usr/bin/env python3
"""Run all registered supplier crawlers and upsert results to Supabase.

Usage:
    python run_crawl.py                    # Crawl all active suppliers
    python run_crawl.py woodworkers_source # Crawl specific supplier
    python run_crawl.py --list             # List registered crawlers
"""

import sys
import logging
from datetime import datetime, timezone

from app.supabase_client import get_supabase_client
from app.suppliers.crawler_base import CrawlerBase
from app.suppliers.woodworkers_source import WoodworkersSourceCrawler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Register all crawlers here
CRAWLERS: dict[str, type[CrawlerBase]] = {
    "woodworkers_source": WoodworkersSourceCrawler,
}


def run_crawler(crawler_cls: type[CrawlerBase]) -> None:
    """Run a single crawler and upsert results to Supabase."""
    crawler = crawler_cls()
    client = get_supabase_client()
    started_at = datetime.now(timezone.utc)

    logger.info("Starting crawl: %s (%s)", crawler.supplier_name, crawler.supplier_id)

    errors: list[str] = []
    try:
        products = crawler.crawl()
    except Exception as e:
        errors.append(str(e))
        products = []
        logger.error("Crawl failed for %s: %s", crawler.supplier_id, e)

    # Upsert products
    upserted = 0
    for product in products:
        try:
            client.table("supplier_prices").upsert(
                {
                    "supplier_id": product.supplier_id,
                    "product_type": product.product_type,
                    "species_or_name": product.species_or_name,
                    "thickness": product.thickness,
                    "price": float(product.price),
                    "unit": product.unit,
                    "url": product.url,
                    "crawled_at": product.crawled_at.isoformat(),
                },
                on_conflict="supplier_id,product_type,species_or_name,thickness",
            ).execute()
            upserted += 1
        except Exception as e:
            errors.append(f"Upsert failed for {product.species_or_name}: {e}")

    # Log the run
    finished_at = datetime.now(timezone.utc)
    client.table("crawl_runs").insert({
        "supplier_id": crawler.supplier_id,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "product_count": upserted,
        "errors": errors if errors else None,
    }).execute()

    logger.info(
        "Finished %s: %d products upserted, %d errors, %.1fs",
        crawler.supplier_id,
        upserted,
        len(errors),
        (finished_at - started_at).total_seconds(),
    )


def main():
    if "--list" in sys.argv:
        print("Registered crawlers:")
        for sid, cls in CRAWLERS.items():
            print(f"  {sid}: {cls.supplier_name} ({cls.base_url})")
        return

    # Filter to specific suppliers if provided
    targets = [a for a in sys.argv[1:] if not a.startswith("-")]
    if targets:
        for sid in targets:
            if sid not in CRAWLERS:
                logger.error("Unknown supplier: %s", sid)
                continue
            run_crawler(CRAWLERS[sid])
    else:
        for crawler_cls in CRAWLERS.values():
            run_crawler(crawler_cls)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test that the script lists crawlers**

```bash
cd /home/josebiro/gt/mayor/backend
source .venv/bin/activate
python run_crawl.py --list
```

Expected: Shows `woodworkers_source: Woodworkers Source (https://www.woodworkerssource.com)`

- [ ] **Step 3: Run the crawl for Woodworkers Source (static fallback)**

```bash
cd /home/josebiro/gt/mayor/backend
python run_crawl.py woodworkers_source
```

Expected: Products upserted to `supplier_prices`, run logged to `crawl_runs`

- [ ] **Step 4: Verify data in Supabase**

```bash
cd /home/josebiro/gt/mayor/backend
python3 -c "
from app.supabase_client import get_supabase_client
client = get_supabase_client()
result = client.table('supplier_prices').select('*').eq('supplier_id', 'woodworkers_source').execute()
print(f'Products: {len(result.data)}')
runs = client.table('crawl_runs').select('*').execute()
print(f'Crawl runs: {len(runs.data)}')
"
```

Expected: ~39 products (8 species × 4 thicknesses + 7 sheet types × 3 thicknesses), 1 crawl run

- [ ] **Step 5: Commit**

```bash
git add backend/run_crawl.py
git commit -m "$(cat <<'EOF'
feat: add crawl runner script for supplier price ingestion

run_crawl.py iterates registered crawlers, upserts products
to supplier_prices table, and logs runs to crawl_runs.
Supports targeting specific suppliers or crawling all.
EOF
)"
```

---

### Task 6: Backend — Database-backed Supplier Read Layer

**Files:**
- Create: `backend/app/suppliers/db_supplier.py`
- Modify: `backend/app/suppliers/registry.py`
- Modify: `backend/app/main.py` — update analyze endpoint to use user's enabled suppliers
- Modify: `backend/app/models.py` — add CatalogItem, UserPreferences models
- Modify: `backend/app/database.py` — add preferences and catalog queries
- Create: `backend/tests/test_catalog.py`

- [ ] **Step 1: Add new models to models.py**

Append to `backend/app/models.py` before the `model_rebuild()` calls:

```python
class CatalogItem(BaseModel):
    supplier_id: str
    supplier_name: str
    product_type: str  # "solid" or "sheet"
    species_or_name: str
    thickness: str
    price: float
    unit: str
    url: str | None = None


class UserPreferencesModel(BaseModel):
    enabled_suppliers: list[str] = ["woodworkers_source"]
    default_species: str | None = None
    default_sheet_type: str | None = None
    default_units: str = "in"
```

- [ ] **Step 2: Add preferences and catalog queries to database.py**

Append to `backend/app/database.py`:

```python
def get_user_preferences(user_id: str) -> dict[str, Any] | None:
    """Get preferences for a user, or None if not yet set."""
    client = get_supabase_client()
    response = (
        client.table("user_preferences")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    if not response.data:
        return None
    return response.data[0]


def upsert_user_preferences(
    user_id: str,
    enabled_suppliers: list[str] | None = None,
    default_species: str | None = None,
    default_sheet_type: str | None = None,
    default_units: str | None = None,
) -> None:
    """Create or update user preferences."""
    client = get_supabase_client()
    data: dict[str, Any] = {"user_id": user_id, "updated_at": "now()"}
    if enabled_suppliers is not None:
        data["enabled_suppliers"] = enabled_suppliers
    if default_species is not None:
        data["default_species"] = default_species
    if default_sheet_type is not None:
        data["default_sheet_type"] = default_sheet_type
    if default_units is not None:
        data["default_units"] = default_units
    client.table("user_preferences").upsert(data, on_conflict="user_id").execute()


def get_catalog(
    product_type: str | None = None,
    search: str | None = None,
    supplier_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Query the supplier_prices table with optional filters.

    Joins with suppliers table to get supplier name.
    """
    client = get_supabase_client()
    query = client.table("supplier_prices").select(
        "*, suppliers(name)"
    )
    if product_type:
        query = query.eq("product_type", product_type)
    if supplier_ids:
        query = query.in_("supplier_id", supplier_ids)
    if search:
        query = query.ilike("species_or_name", f"%{search}%")
    query = query.order("species_or_name").order("thickness")
    response = query.execute()
    return response.data


def get_suppliers() -> list[dict[str, Any]]:
    """Get all suppliers."""
    client = get_supabase_client()
    response = client.table("suppliers").select("*").eq("active", True).execute()
    return response.data
```

- [ ] **Step 3: Add new API endpoints to main.py**

Add imports at the top of `backend/app/main.py`:

```python
from app.models import CatalogItem, UserPreferencesModel
from app.database import (
    create_project, update_project, list_projects, get_project, delete_project,
    get_user_preferences, upsert_user_preferences, get_catalog as db_get_catalog, get_suppliers,
)
```

Then add new endpoints at the end of `backend/app/main.py`:

```python
@app.get("/api/catalog")
async def get_catalog_endpoint(
    type: str | None = None,
    search: str | None = None,
    user: dict = Depends(require_user),
):
    """Get catalog items filtered by user's enabled suppliers."""
    prefs = get_user_preferences(user["id"])
    enabled = prefs["enabled_suppliers"] if prefs else ["woodworkers_source"]
    rows = db_get_catalog(product_type=type, search=search, supplier_ids=enabled)
    items = []
    for row in rows:
        supplier_name = ""
        if row.get("suppliers") and isinstance(row["suppliers"], dict):
            supplier_name = row["suppliers"].get("name", "")
        items.append(CatalogItem(
            supplier_id=row["supplier_id"],
            supplier_name=supplier_name,
            product_type=row["product_type"],
            species_or_name=row["species_or_name"],
            thickness=row["thickness"],
            price=float(row["price"]),
            unit=row["unit"],
            url=row.get("url"),
        ))
    return items


@app.get("/api/preferences")
async def get_preferences(user: dict = Depends(require_user)):
    """Get current user's preferences."""
    prefs = get_user_preferences(user["id"])
    if prefs is None:
        return UserPreferencesModel()
    return UserPreferencesModel(
        enabled_suppliers=prefs.get("enabled_suppliers", ["woodworkers_source"]),
        default_species=prefs.get("default_species"),
        default_sheet_type=prefs.get("default_sheet_type"),
        default_units=prefs.get("default_units", "in"),
    )


@app.put("/api/preferences")
async def update_preferences(
    prefs: UserPreferencesModel,
    user: dict = Depends(require_user),
):
    """Update current user's preferences."""
    upsert_user_preferences(
        user_id=user["id"],
        enabled_suppliers=prefs.enabled_suppliers,
        default_species=prefs.default_species,
        default_sheet_type=prefs.default_sheet_type,
        default_units=prefs.default_units,
    )
    return {"message": "Preferences updated"}


@app.get("/api/suppliers")
async def list_suppliers_endpoint(user: dict = Depends(require_user)):
    """List all active suppliers."""
    return get_suppliers()
```

- [ ] **Step 4: Remove old database import and add new ones**

In `backend/app/main.py`, update the database import line:

```python
from app.database import (
    create_project, update_project, list_projects, get_project, delete_project,
    get_user_preferences, upsert_user_preferences, get_catalog as db_get_catalog, get_suppliers,
)
```

And remove the old separate import:
```python
# Remove this line:
from app.database import create_project, update_project, list_projects, get_project, delete_project
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/models.py backend/app/database.py backend/app/main.py
git commit -m "$(cat <<'EOF'
feat: add catalog, preferences, and suppliers API endpoints

New endpoints:
- GET /api/catalog — filtered by user's enabled suppliers
- GET /api/preferences — read user preferences
- PUT /api/preferences — update user preferences
- GET /api/suppliers — list active suppliers
EOF
)"
```

---

### Task 7: Frontend — Design System (Theme Overhaul)

**Files:**
- Modify: `frontend/src/app.css`

- [ ] **Step 1: Replace the entire app.css**

```css
@import 'tailwindcss';

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
  --color-bg: #0f1219;
  --color-bg-deep: #0a0e17;
  --color-surface: #1a1f2e;
  --color-surface-hover: #252b3d;
  --color-border: #2a3040;
  --color-border-strong: #1e293b;
  --color-primary: #6366f1;
  --color-primary-hover: #818cf8;
  --color-text: #e2e8f0;
  --color-text-secondary: #94a3b8;
  --color-text-muted: #64748b;
  --color-text-dim: #475569;
  --color-destructive: #ef4444;
}

body {
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  color: var(--color-text);
  background: var(--color-bg);
}

/* Remove all serif font usage */
h1, h2, h3 {
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
}

/* Scrollbar styling for dark theme */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
::-webkit-scrollbar-track {
  background: var(--color-bg);
}
::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: var(--color-text-muted);
}

/* Form inputs default dark styling */
input, select, textarea {
  background: var(--color-surface);
  color: var(--color-text);
  border-color: var(--color-border);
}
input::placeholder, textarea::placeholder {
  color: var(--color-text-muted);
}
input:focus, select:focus, textarea:focus {
  border-color: var(--color-primary);
  outline: none;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
}
```

- [ ] **Step 2: Start dev server and visually verify the theme change**

```bash
cd /home/josebiro/gt/mayor/frontend
npm run dev -- --host 0.0.0.0
```

Open in browser — verify dark background, no warm brown colors, no serif fonts.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app.css
git commit -m "$(cat <<'EOF'
feat: replace folksy theme with dark precision design system

Dark CAD-tool-inspired palette (indigo primary, slate grays,
near-black backgrounds). Removes DM Serif Display — Inter only.
All CSS custom properties updated.
EOF
)"
```

---

### Task 8: Frontend — Layout, Navbar, and Profile Menu

**Files:**
- Create: `frontend/src/lib/components/ProfileMenu.svelte`
- Modify: `frontend/src/routes/+layout.svelte`

- [ ] **Step 1: Create ProfileMenu component**

Create `frontend/src/lib/components/ProfileMenu.svelte`:

```svelte
<script lang="ts">
	import { goto } from '$app/navigation';
	import { supabase } from '$lib/supabase';
	import { user } from '$lib/stores/auth';

	let open = $state(false);

	const initials = $derived(() => {
		const u = $user;
		if (!u?.email) return '?';
		return u.email.substring(0, 2).toUpperCase();
	});

	function handleClickOutside(event: MouseEvent) {
		const target = event.target as HTMLElement;
		if (!target.closest('.profile-menu')) {
			open = false;
		}
	}

	async function handleSignOut() {
		await supabase.auth.signOut();
		open = false;
		goto('/');
	}
</script>

<svelte:window on:click={handleClickOutside} />

<div class="profile-menu relative">
	<button
		onclick={() => (open = !open)}
		class="w-8 h-8 bg-[var(--color-primary)] rounded-full flex items-center justify-center cursor-pointer hover:bg-[var(--color-primary-hover)] transition-colors duration-150"
	>
		<span class="text-white text-xs font-semibold">{initials()}</span>
	</button>

	{#if open}
		<div class="absolute top-10 right-0 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg w-44 py-1 shadow-lg shadow-black/40 z-50">
			<button
				onclick={() => { open = false; goto('/preferences'); }}
				class="w-full text-left px-3 py-2 text-sm text-[var(--color-text)] hover:bg-[var(--color-surface-hover)] transition-colors duration-150"
			>
				Preferences
			</button>
			<div class="border-t border-[var(--color-border)] my-1"></div>
			<button
				onclick={handleSignOut}
				class="w-full text-left px-3 py-2 text-sm text-[var(--color-destructive)] hover:bg-[var(--color-surface-hover)] transition-colors duration-150"
			>
				Sign Out
			</button>
		</div>
	{/if}
</div>
```

- [ ] **Step 2: Rewrite +layout.svelte with new navbar and route guards**

Replace `frontend/src/routes/+layout.svelte`:

```svelte
<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { supabase } from '$lib/supabase';
	import { user, session, authLoading, isAuthenticated } from '$lib/stores/auth';
	import ProfileMenu from '$lib/components/ProfileMenu.svelte';

	let { children } = $props();

	// Public routes that don't require auth
	const publicRoutes = ['/login', '/auth/callback'];
	const isPublicRoute = $derived(publicRoutes.some(r => page.url.pathname.startsWith(r)));

	onMount(() => {
		supabase.auth.getSession().then(({ data }) => {
			session.set(data.session);
			user.set(data.session?.user ?? null);
			authLoading.set(false);
		});

		const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, newSession) => {
			session.set(newSession);
			user.set(newSession?.user ?? null);
		});

		return () => subscription.unsubscribe();
	});

	// Redirect unauthenticated users to login (except public routes and landing)
	$effect(() => {
		if (!$authLoading && !$isAuthenticated && !isPublicRoute && page.url.pathname !== '/') {
			goto(`/login?redirect=${encodeURIComponent(page.url.pathname)}`);
		}
	});
</script>

{#if $authLoading}
	<div class="min-h-screen bg-[var(--color-bg)] flex items-center justify-center">
		<div class="text-[var(--color-text-muted)]">Loading...</div>
	</div>
{:else if $isAuthenticated}
	<!-- Authenticated layout with navbar -->
	<div class="min-h-screen bg-[var(--color-bg)]">
		<header class="bg-[var(--color-bg-deep)] border-b border-[var(--color-border-strong)] px-6 py-2.5">
			<div class="max-w-6xl mx-auto flex items-center justify-between">
				<div class="flex items-center gap-5">
					<a href="/projects" class="flex items-center gap-2">
						<img src="/kerf-logo.png" alt="Kerf" class="h-5 brightness-0 invert" style="filter: brightness(0) saturate(100%) invert(42%) sepia(93%) saturate(1352%) hue-rotate(215deg) brightness(101%) contrast(93%);" />
						<span class="text-[var(--color-text)] font-semibold text-[15px] tracking-tight">kerf</span>
					</a>
					<nav class="flex gap-0.5">
						<a
							href="/projects"
							class="px-3 py-1.5 text-xs rounded transition-colors duration-150
								{page.url.pathname === '/projects'
									? 'bg-[var(--color-border-strong)] text-[var(--color-text)]'
									: 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'}"
						>Projects</a>
						<a
							href="/"
							class="px-3 py-1.5 text-xs rounded transition-colors duration-150
								{page.url.pathname === '/'
									? 'bg-[var(--color-border-strong)] text-[var(--color-text)]'
									: 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'}"
						>New Project</a>
					</nav>
				</div>
				<ProfileMenu />
			</div>
		</header>

		<main class="max-w-6xl mx-auto px-6 py-8">
			{@render children()}
		</main>
	</div>
{:else}
	<!-- Unauthenticated — render page directly (landing or login) -->
	{@render children()}
{/if}
```

- [ ] **Step 3: Copy logo to static directory**

```bash
cp /home/josebiro/gt/mayor/kerf-logo.png /home/josebiro/gt/mayor/frontend/static/kerf-logo.png
```

- [ ] **Step 4: Verify in browser**

Start dev server, check:
- Authenticated: dark navbar with logo, Projects/New Project tabs, profile avatar menu
- Unauthenticated: no navbar (bare page rendered)
- Profile menu: click avatar → dropdown with Preferences and Sign Out
- Sign Out: redirects to landing

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/components/ProfileMenu.svelte frontend/src/routes/+layout.svelte frontend/static/kerf-logo.png
git commit -m "$(cat <<'EOF'
feat: add dark navbar with tab navigation and profile menu

Navbar shows logo + tabs (Projects / New Project) on left,
profile avatar with Preferences/SignOut dropdown on right.
Route guards redirect unauthenticated users to login.
EOF
)"
```

---

### Task 9: Frontend — Landing Page (Marketing)

**Files:**
- Create: `frontend/src/lib/components/LandingPage.svelte`
- Modify: `frontend/src/routes/+page.svelte`

- [ ] **Step 1: Create LandingPage component**

Create `frontend/src/lib/components/LandingPage.svelte`:

```svelte
<script lang="ts">
	import { goto } from '$app/navigation';
</script>

<div class="min-h-screen bg-[var(--color-bg)]">
	<!-- Hero -->
	<header class="bg-[var(--color-bg-deep)] border-b border-[var(--color-border-strong)] px-6 py-4">
		<div class="max-w-5xl mx-auto flex items-center justify-between">
			<div class="flex items-center gap-2">
				<img src="/kerf-logo.png" alt="Kerf" class="h-5 brightness-0 invert" style="filter: brightness(0) saturate(100%) invert(42%) sepia(93%) saturate(1352%) hue-rotate(215deg) brightness(101%) contrast(93%);" />
				<span class="text-[var(--color-text)] font-semibold text-[15px] tracking-tight">kerf</span>
			</div>
			<a href="/login" class="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition-colors duration-150">Sign In</a>
		</div>
	</header>

	<div class="max-w-5xl mx-auto px-6">
		<!-- Hero content -->
		<div class="py-24 text-center">
			<h1 class="text-4xl font-bold text-[var(--color-text)] tracking-tight mb-4">
				From CAD model to cut list in seconds
			</h1>
			<p class="text-lg text-[var(--color-text-secondary)] max-w-2xl mx-auto mb-8">
				Upload a 3MF file from Fusion 360, Onshape, or any CAD tool. Kerf analyzes your parts, optimizes cuts, and generates shopping lists with real lumber prices.
			</p>
			<div class="flex gap-3 justify-center">
				<button
					onclick={() => goto('/login?signup=true')}
					class="bg-[var(--color-primary)] text-white px-6 py-2.5 rounded-md text-sm font-semibold hover:bg-[var(--color-primary-hover)] transition-colors duration-150"
				>
					Get Started
				</button>
				<button
					onclick={() => goto('/login')}
					class="bg-[var(--color-surface)] text-[var(--color-text)] border border-[var(--color-border)] px-6 py-2.5 rounded-md text-sm font-medium hover:bg-[var(--color-surface-hover)] transition-colors duration-150"
				>
					Sign In
				</button>
			</div>
		</div>

		<!-- Features -->
		<div class="grid grid-cols-1 md:grid-cols-3 gap-6 pb-24">
			<div class="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-6">
				<div class="w-10 h-10 bg-[var(--color-bg-deep)] rounded-lg flex items-center justify-center mb-4">
					<span class="text-[var(--color-primary)] text-lg">$</span>
				</div>
				<h3 class="text-sm font-semibold text-[var(--color-text)] mb-2">Multi-Supplier Pricing</h3>
				<p class="text-sm text-[var(--color-text-secondary)]">Compare lumber prices across suppliers. Real prices from Woodworkers Source, Knotty Lumber, and Makerstock.</p>
			</div>
			<div class="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-6">
				<div class="w-10 h-10 bg-[var(--color-bg-deep)] rounded-lg flex items-center justify-center mb-4">
					<span class="text-[var(--color-primary)] text-lg">&#9638;</span>
				</div>
				<h3 class="text-sm font-semibold text-[var(--color-text)] mb-2">Cut Optimization</h3>
				<p class="text-sm text-[var(--color-text-secondary)]">Minimize waste with optimized cutting layouts for both sheet goods and solid lumber boards.</p>
			</div>
			<div class="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-6">
				<div class="w-10 h-10 bg-[var(--color-bg-deep)] rounded-lg flex items-center justify-center mb-4">
					<span class="text-[var(--color-primary)] text-lg">&#8595;</span>
				</div>
				<h3 class="text-sm font-semibold text-[var(--color-text)] mb-2">PDF Reports</h3>
				<p class="text-sm text-[var(--color-text-secondary)]">Download detailed cut list reports with 3D thumbnails, parts lists, shopping lists, and cost breakdowns.</p>
			</div>
		</div>
	</div>

	<!-- Footer -->
	<footer class="border-t border-[var(--color-border-strong)] px-6 py-6">
		<div class="max-w-5xl mx-auto text-center text-xs text-[var(--color-text-dim)]">
			&copy; 2026 Kerf
		</div>
	</footer>
</div>
```

- [ ] **Step 2: Update +page.svelte to show landing for unauthenticated users**

In `frontend/src/routes/+page.svelte`, add the import and conditional at the top of the template. The `<script>` block stays the same, but add the import:

```svelte
<script lang="ts">
	// ... existing imports ...
	import LandingPage from '$lib/components/LandingPage.svelte';
	import { isAuthenticated } from '$lib/stores/auth';
	// ... rest of existing script ...
</script>

{#if !$isAuthenticated}
	<LandingPage />
{:else}
	<!-- existing authenticated content (the upload/analyze flow) -->
	<!-- Remove the outer min-h-screen/header wrapper since layout.svelte handles it now -->
	{#if !uploadResult}
		<!-- ... existing upload section ... -->
```

The key change: remove the `<header>` navbar and outer `<div class="min-h-screen">` wrapper from `+page.svelte` since `+layout.svelte` now provides those for authenticated users. Keep the main content (upload, model viewer, configure, results).

- [ ] **Step 3: Restyle the authenticated content in +page.svelte for dark theme**

Update all color references from old tokens to new ones:
- `var(--color-foreground)` → `var(--color-text)`
- `var(--color-foreground-muted)` → `var(--color-text-secondary)`
- `var(--color-surface)` → keep (already exists in new theme)
- `var(--color-accent)` → `var(--color-primary)`
- `var(--color-accent-hover)` → `var(--color-primary-hover)`
- `bg-red-50 border-red-200` → `bg-red-900/20 border-red-800/30`
- Remove `font-['DM_Serif_Display',serif]`

- [ ] **Step 4: Verify in browser**

- Unauthenticated at `/`: Marketing landing page with hero, features, Get Started / Sign In
- Authenticated at `/`: Upload flow (no duplicate navbar)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/components/LandingPage.svelte frontend/src/routes/+page.svelte
git commit -m "$(cat <<'EOF'
feat: add marketing landing page for unauthenticated visitors

Shows hero section with value prop, three feature cards,
Get Started and Sign In CTAs. Authenticated users see the
project workflow directly.
EOF
)"
```

---

### Task 10: Frontend — Login Page Restyle

**Files:**
- Modify: `frontend/src/routes/login/+page.svelte`

- [ ] **Step 1: Update login page colors**

Replace all old color token references in `frontend/src/routes/login/+page.svelte`:

- `var(--color-bg)` → keep (remapped in CSS)
- `var(--color-primary)` / `font-['DM_Serif_Display',serif]` → `var(--color-text) font-semibold`
- `var(--color-foreground-muted)` → `var(--color-text-secondary)`
- `var(--color-foreground)` → `var(--color-text)`
- `var(--color-surface)` → keep
- `var(--color-surface-muted)` → `var(--color-surface-hover)`
- `var(--color-border)` → keep
- `var(--color-accent)` → `var(--color-primary)`
- `var(--color-accent-hover)` → `var(--color-primary-hover)`
- `var(--color-destructive)` → keep
- `focus:ring-[var(--color-accent)]` → `focus:ring-[var(--color-primary)]`

Update the header to use the logo mark:

```svelte
<div class="text-center mb-8">
	<div class="flex items-center justify-center gap-2 mb-2">
		<img src="/kerf-logo.png" alt="Kerf" class="h-6 brightness-0 invert" style="filter: brightness(0) saturate(100%) invert(42%) sepia(93%) saturate(1352%) hue-rotate(215deg) brightness(101%) contrast(93%);" />
		<span class="text-2xl text-[var(--color-text)] font-semibold">kerf</span>
	</div>
	<p class="text-sm text-[var(--color-text-secondary)] mt-1">Sign in to get started</p>
</div>
```

- [ ] **Step 2: Verify in browser**

Navigate to `/login` — should be dark theme, indigo accents, no serif fonts, logo mark.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/login/+page.svelte
git commit -m "feat: restyle login page for dark precision theme"
```

---

### Task 11: Frontend — Projects Dashboard Restyle

**Files:**
- Modify: `frontend/src/routes/projects/+page.svelte`

- [ ] **Step 1: Restyle projects page for dark theme**

Remove the `<header>` navbar (layout handles it now). Remove the outer `<div class="min-h-screen">` wrapper. Update all color tokens:

```svelte
<script lang="ts">
	// ... existing script unchanged ...
</script>

<div>
	<div class="flex items-center justify-between mb-6">
		<h2 class="text-lg font-semibold text-[var(--color-text)]">Projects</h2>
		<a href="/" class="bg-[var(--color-primary)] text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-[var(--color-primary-hover)] transition-colors duration-150">
			+ New Project
		</a>
	</div>

	{#if loading}
		<p class="text-[var(--color-text-secondary)]">Loading projects...</p>
	{:else if error}
		<p class="text-[var(--color-destructive)]">{error}</p>
	{:else if projects.length === 0}
		<div class="text-center py-16 text-[var(--color-text-secondary)]">
			<p class="text-lg mb-2">No saved projects yet</p>
			<p class="text-sm">Upload a 3MF file and click "Save Project" to get started.</p>
			<a href="/" class="inline-block mt-4 text-[var(--color-primary)] hover:text-[var(--color-primary-hover)] text-sm transition-colors duration-150">Upload a file</a>
		</div>
	{:else}
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
			{#each projects as project}
				<div class="bg-[var(--color-surface)] rounded-lg border border-[var(--color-border)] overflow-hidden hover:border-[var(--color-primary)]/30 transition-all duration-150">
					<button onclick={() => goto(`/?project=${project.id}`)} class="w-full text-left">
						{#if project.thumbnail_url}
							<img src={project.thumbnail_url} alt={project.name} class="w-full h-40 object-cover bg-[var(--color-bg-deep)]" />
						{:else}
							<div class="w-full h-40 bg-[var(--color-bg-deep)] flex items-center justify-center text-[var(--color-text-dim)] text-sm">No preview</div>
						{/if}
						<div class="p-4">
							<h3 class="font-medium text-[var(--color-text)] truncate">{project.name}</h3>
							<p class="text-xs text-[var(--color-text-muted)] mt-1">{formatDate(project.created_at)}</p>
							<div class="flex gap-3 mt-2 text-xs text-[var(--color-text-secondary)]">
								<span>{project.part_count} parts</span>
								<span>{project.solid_species}</span>
								<span>{formatCost(project.estimated_cost)}</span>
							</div>
						</div>
					</button>
					<div class="px-4 pb-3">
						<button onclick={() => handleDelete(project.id, project.name)} class="text-xs text-[var(--color-destructive)] hover:opacity-80 transition-colors duration-150">Delete</button>
					</div>
				</div>
			{/each}
			<!-- New Project card -->
			<a href="/" class="bg-[var(--color-surface)] rounded-lg border border-dashed border-[var(--color-border)] flex items-center justify-center min-h-[240px] hover:border-[var(--color-primary)]/50 transition-all duration-150">
				<div class="text-center">
					<div class="text-[var(--color-primary)] text-2xl mb-1">+</div>
					<div class="text-sm text-[var(--color-text-muted)]">New Project</div>
				</div>
			</a>
		</div>
	{/if}
</div>
```

- [ ] **Step 2: Verify in browser**

Navigate to `/projects` — dark theme cards, no duplicate navbar, "+ New Project" dashed card at end.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/projects/+page.svelte
git commit -m "feat: restyle projects dashboard for dark theme with new project card"
```

---

### Task 12: Frontend — API Client Updates (Catalog + Preferences)

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Add new types**

Append to `frontend/src/lib/types.ts`:

```typescript
export interface CatalogItem {
	supplier_id: string;
	supplier_name: string;
	product_type: 'solid' | 'sheet';
	species_or_name: string;
	thickness: string;
	price: number;
	unit: string;
	url: string | null;
}

export interface UserPreferences {
	enabled_suppliers: string[];
	default_species: string | null;
	default_sheet_type: string | null;
	default_units: DisplayUnits;
}

export interface Supplier {
	supplier_id: string;
	name: string;
	base_url: string;
	active: boolean;
}
```

- [ ] **Step 2: Add new API functions**

Append to `frontend/src/lib/api.ts`:

```typescript
import type { CatalogItem, UserPreferences, Supplier } from './types';

export async function getCatalog(params?: { type?: string; search?: string }): Promise<CatalogItem[]> {
	const searchParams = new URLSearchParams();
	if (params?.type) searchParams.set('type', params.type);
	if (params?.search) searchParams.set('search', params.search);
	const qs = searchParams.toString();
	const response = await fetch(`${BASE}/catalog${qs ? '?' + qs : ''}`, { headers: authHeaders() });
	if (!response.ok) throw new Error('Failed to fetch catalog');
	return response.json();
}

export async function getPreferences(): Promise<UserPreferences> {
	const response = await fetch(`${BASE}/preferences`, { headers: authHeaders() });
	if (!response.ok) throw new Error('Failed to fetch preferences');
	return response.json();
}

export async function updatePreferences(prefs: UserPreferences): Promise<void> {
	const response = await fetch(`${BASE}/preferences`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json', ...authHeaders() },
		body: JSON.stringify(prefs),
	});
	if (!response.ok) throw new Error('Failed to update preferences');
}

export async function getSuppliers(): Promise<Supplier[]> {
	const response = await fetch(`${BASE}/suppliers`, { headers: authHeaders() });
	if (!response.ok) throw new Error('Failed to fetch suppliers');
	return response.json();
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts
git commit -m "$(cat <<'EOF'
feat: add catalog, preferences, and suppliers API client functions

New TypeScript types and fetch wrappers for the catalog browser,
user preferences, and supplier management endpoints.
EOF
)"
```

---

### Task 13: Frontend — Combobox Component

**Files:**
- Create: `frontend/src/lib/components/Combobox.svelte`

- [ ] **Step 1: Create the searchable combobox**

Create `frontend/src/lib/components/Combobox.svelte`:

```svelte
<script lang="ts">
	import type { CatalogItem } from '$lib/types';

	interface Props {
		label: string;
		placeholder?: string;
		items: CatalogItem[];
		value: string;
		onSelect: (value: string) => void;
		onBrowseCatalog?: () => void;
		disabled?: boolean;
	}

	let { label, placeholder = 'Search...', items, value, onSelect, onBrowseCatalog, disabled = false }: Props = $props();

	let query = $state('');
	let open = $state(false);
	let highlightIndex = $state(-1);
	let inputEl: HTMLInputElement;

	const filtered = $derived(() => {
		if (!query) return items;
		const q = query.toLowerCase();
		return items.filter(item =>
			item.species_or_name.toLowerCase().includes(q)
		);
	});

	const displayValue = $derived(() => {
		if (open) return query;
		return value || '';
	});

	function handleFocus() {
		open = true;
		query = '';
		highlightIndex = -1;
	}

	function handleBlur() {
		// Delay to allow click on dropdown item
		setTimeout(() => { open = false; }, 150);
	}

	function handleInput(e: Event) {
		query = (e.target as HTMLInputElement).value;
		open = true;
		highlightIndex = -1;
	}

	function handleKeydown(e: KeyboardEvent) {
		const list = filtered();
		if (e.key === 'ArrowDown') {
			e.preventDefault();
			highlightIndex = Math.min(highlightIndex + 1, list.length - 1);
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			highlightIndex = Math.max(highlightIndex - 1, 0);
		} else if (e.key === 'Enter' && highlightIndex >= 0 && highlightIndex < list.length) {
			e.preventDefault();
			selectItem(list[highlightIndex]);
		} else if (e.key === 'Escape') {
			open = false;
			inputEl?.blur();
		}
	}

	function selectItem(item: CatalogItem) {
		onSelect(item.species_or_name);
		open = false;
		query = '';
	}

	// Supplier abbreviation
	function supplierBadge(supplierId: string): string {
		const map: Record<string, string> = {
			woodworkers_source: 'WS',
			knotty_lumber: 'KL',
			makerstock: 'MS',
		};
		return map[supplierId] || supplierId.substring(0, 2).toUpperCase();
	}

	function formatPrice(item: CatalogItem): string {
		const unitLabel = item.unit === 'board_foot' ? '/bf' : '/sheet';
		return `$${item.price.toFixed(2)}${unitLabel}`;
	}
</script>

<div class="relative">
	<label class="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider mb-1.5">{label}</label>
	<input
		bind:this={inputEl}
		type="text"
		value={displayValue()}
		{placeholder}
		{disabled}
		onfocus={handleFocus}
		onblur={handleBlur}
		oninput={handleInput}
		onkeydown={handleKeydown}
		class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-md px-3 py-2 text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20 focus:outline-none transition-colors duration-150 disabled:opacity-50"
	/>

	{#if open && !disabled}
		<div class="absolute top-full left-0 right-0 mt-1 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-md shadow-lg shadow-black/40 z-40 max-h-60 overflow-y-auto">
			{#each filtered() as item, i}
				<button
					onmousedown={() => selectItem(item)}
					class="w-full text-left px-3 py-2 text-sm flex items-center justify-between transition-colors duration-75
						{i === highlightIndex ? 'bg-[var(--color-surface-hover)]' : 'hover:bg-[var(--color-surface-hover)]'}"
				>
					<span class="text-[var(--color-text)]">{item.species_or_name}</span>
					<span class="flex items-center gap-2">
						<span class="text-[var(--color-text-muted)] text-xs">{formatPrice(item)}</span>
						<span class="text-[10px] bg-[var(--color-border-strong)] text-[var(--color-text-muted)] px-1.5 py-0.5 rounded">{supplierBadge(item.supplier_id)}</span>
					</span>
				</button>
			{/each}
			{#if filtered().length === 0}
				<div class="px-3 py-2 text-sm text-[var(--color-text-muted)]">No matches</div>
			{/if}
			{#if onBrowseCatalog}
				<div class="border-t border-[var(--color-border)]">
					<button
						onmousedown={onBrowseCatalog}
						class="w-full text-left px-3 py-2 text-xs text-[var(--color-primary)] hover:bg-[var(--color-surface-hover)] transition-colors duration-75"
					>
						Browse Full Catalog
					</button>
				</div>
			{/if}
		</div>
	{/if}
</div>
```

- [ ] **Step 2: Verify in browser with Configure component**

This component will be wired in during Task 15 (Configure update). For now, verify it renders correctly by temporarily importing it in the page.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/components/Combobox.svelte
git commit -m "$(cat <<'EOF'
feat: add Combobox component with autocomplete and supplier badges

Searchable select with inline prices and supplier abbreviations.
Supports keyboard navigation, blur-to-close, and a Browse Catalog
link to open the full catalog browser.
EOF
)"
```

---

### Task 14: Frontend — Catalog Browser Component

**Files:**
- Create: `frontend/src/lib/components/CatalogBrowser.svelte`

- [ ] **Step 1: Create the slide-over catalog browser**

Create `frontend/src/lib/components/CatalogBrowser.svelte`:

```svelte
<script lang="ts">
	import type { CatalogItem } from '$lib/types';

	interface Props {
		items: CatalogItem[];
		open: boolean;
		onClose: () => void;
		onSelect: (species: string) => void;
		initialTab?: 'solid' | 'sheet';
	}

	let { items, open, onClose, onSelect, initialTab = 'solid' }: Props = $props();

	let activeTab = $state<'solid' | 'sheet'>(initialTab);
	let search = $state('');
	let supplierFilter = $state<string | ''>('');

	const filteredItems = $derived(() => {
		let result = items.filter(i => i.product_type === activeTab);
		if (supplierFilter) {
			result = result.filter(i => i.supplier_id === supplierFilter);
		}
		if (search) {
			const q = search.toLowerCase();
			result = result.filter(i => i.species_or_name.toLowerCase().includes(q));
		}
		return result;
	});

	// Group items by species for the table view
	const groupedBySpecies = $derived(() => {
		const groups: Record<string, CatalogItem[]> = {};
		for (const item of filteredItems()) {
			const key = `${item.species_or_name}|${item.supplier_id}`;
			if (!groups[key]) groups[key] = [];
			groups[key].push(item);
		}
		return Object.values(groups);
	});

	const uniqueSuppliers = $derived(() => {
		const seen = new Map<string, string>();
		for (const item of items) {
			if (!seen.has(item.supplier_id)) {
				seen.set(item.supplier_id, item.supplier_name);
			}
		}
		return Array.from(seen.entries()).map(([id, name]) => ({ id, name }));
	});

	function supplierBadge(supplierId: string): string {
		const map: Record<string, string> = {
			woodworkers_source: 'WS',
			knotty_lumber: 'KL',
			makerstock: 'MS',
		};
		return map[supplierId] || supplierId.substring(0, 2).toUpperCase();
	}

	function handleSelect(species: string) {
		onSelect(species);
		onClose();
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') onClose();
	}
</script>

<svelte:window on:keydown={handleKeydown} />

{#if open}
	<!-- Backdrop -->
	<div class="fixed inset-0 bg-black/50 z-40" onclick={onClose}></div>

	<!-- Slide-over panel -->
	<div class="fixed inset-y-0 right-0 w-full max-w-lg bg-[var(--color-bg)] border-l border-[var(--color-border-strong)] shadow-2xl z-50 flex flex-col">
		<!-- Header -->
		<div class="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border-strong)]">
			<h2 class="text-sm font-semibold text-[var(--color-text)]">Material Catalog</h2>
			<button onclick={onClose} class="text-[var(--color-text-muted)] hover:text-[var(--color-text)] text-lg">&times;</button>
		</div>

		<!-- Filters -->
		<div class="px-4 py-3 border-b border-[var(--color-border-strong)] flex items-center gap-3">
			<div class="flex gap-1">
				<button
					onclick={() => (activeTab = 'solid')}
					class="px-3 py-1 text-xs font-medium rounded transition-colors duration-150
						{activeTab === 'solid' ? 'bg-[var(--color-primary)] text-white' : 'bg-[var(--color-border-strong)] text-[var(--color-text-secondary)]'}"
				>Solid</button>
				<button
					onclick={() => (activeTab = 'sheet')}
					class="px-3 py-1 text-xs font-medium rounded transition-colors duration-150
						{activeTab === 'sheet' ? 'bg-[var(--color-primary)] text-white' : 'bg-[var(--color-border-strong)] text-[var(--color-text-secondary)]'}"
				>Sheet</button>
			</div>
			<input
				type="text"
				bind:value={search}
				placeholder="Filter..."
				class="flex-1 bg-[var(--color-surface)] border border-[var(--color-border)] rounded px-2 py-1 text-xs text-[var(--color-text)] placeholder:text-[var(--color-text-muted)]"
			/>
			<select
				bind:value={supplierFilter}
				class="bg-[var(--color-surface)] border border-[var(--color-border)] rounded px-2 py-1 text-xs text-[var(--color-text)]"
			>
				<option value="">All suppliers</option>
				{#each uniqueSuppliers() as s}
					<option value={s.id}>{s.name}</option>
				{/each}
			</select>
		</div>

		<!-- Table -->
		<div class="flex-1 overflow-y-auto">
			<table class="w-full text-xs">
				<thead class="sticky top-0 bg-[var(--color-bg-deep)]">
					<tr class="border-b border-[var(--color-border-strong)]">
						<th class="text-left px-4 py-2 text-[var(--color-text-muted)] uppercase tracking-wider font-medium">Species</th>
						<th class="text-left px-2 py-2 text-[var(--color-text-muted)] uppercase tracking-wider font-medium">Price</th>
						<th class="text-left px-2 py-2 text-[var(--color-text-muted)] uppercase tracking-wider font-medium">Thickness</th>
						<th class="text-left px-2 py-2 text-[var(--color-text-muted)] uppercase tracking-wider font-medium">Supplier</th>
					</tr>
				</thead>
				<tbody>
					{#each filteredItems() as item}
						<tr
							onclick={() => handleSelect(item.species_or_name)}
							class="border-b border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-surface-hover)] transition-colors duration-75"
						>
							<td class="px-4 py-2.5 text-[var(--color-text)] font-medium">{item.species_or_name}</td>
							<td class="px-2 py-2.5 text-[var(--color-text-secondary)]">${item.price.toFixed(2)}</td>
							<td class="px-2 py-2.5 text-[var(--color-text-secondary)]">{item.thickness}</td>
							<td class="px-2 py-2.5">
								<span class="text-[10px] bg-[var(--color-border-strong)] text-[var(--color-text-muted)] px-1.5 py-0.5 rounded">{supplierBadge(item.supplier_id)}</span>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
			{#if filteredItems().length === 0}
				<div class="text-center py-8 text-[var(--color-text-muted)] text-sm">No materials found</div>
			{/if}
		</div>
	</div>
{/if}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/components/CatalogBrowser.svelte
git commit -m "$(cat <<'EOF'
feat: add CatalogBrowser slide-over panel

Full-catalog view with Solid/Sheet tabs, search filter,
supplier filter dropdown, and price table. Slides in from
the right. Click a row to select material and close.
EOF
)"
```

---

### Task 15: Frontend — Update Configure Component

**Files:**
- Modify: `frontend/src/lib/components/Configure.svelte`

- [ ] **Step 1: Replace Configure with Combobox + Catalog integration**

Rewrite `frontend/src/lib/components/Configure.svelte`:

```svelte
<script lang="ts">
	import { onMount } from 'svelte';
	import { getCatalog } from '$lib/api';
	import Combobox from './Combobox.svelte';
	import CatalogBrowser from './CatalogBrowser.svelte';
	import type { DisplayUnits, CatalogItem } from '$lib/types';

	interface Props {
		onAnalyze: (config: { solid_species: string; sheet_type: string; all_solid: boolean; display_units: DisplayUnits; }) => void;
		analyzing: boolean;
		initialConfig?: { solid_species: string; sheet_type: string; all_solid: boolean; display_units: DisplayUnits } | null;
	}

	let { onAnalyze, analyzing, initialConfig = null }: Props = $props();

	let allItems = $state<CatalogItem[]>([]);
	let solidSpecies = $state(initialConfig?.solid_species || '');
	let sheetType = $state(initialConfig?.sheet_type || '');
	let allSolid = $state(initialConfig?.all_solid || false);
	let displayUnits = $state<DisplayUnits>(initialConfig?.display_units || 'in');
	let loading = $state(true);
	let catalogOpen = $state(false);
	let catalogTab = $state<'solid' | 'sheet'>('solid');

	const solidItems = $derived(allItems.filter(i => i.product_type === 'solid'));
	const sheetItems = $derived(allItems.filter(i => i.product_type === 'sheet'));

	// Deduplicate species names for the combobox (show cheapest per species)
	const uniqueSolidItems = $derived(() => {
		const seen = new Map<string, CatalogItem>();
		for (const item of solidItems) {
			if (!seen.has(item.species_or_name) || item.price < seen.get(item.species_or_name)!.price) {
				seen.set(item.species_or_name, item);
			}
		}
		return Array.from(seen.values());
	});

	const uniqueSheetItems = $derived(() => {
		const seen = new Map<string, CatalogItem>();
		for (const item of sheetItems) {
			if (!seen.has(item.species_or_name) || item.price < seen.get(item.species_or_name)!.price) {
				seen.set(item.species_or_name, item);
			}
		}
		return Array.from(seen.values());
	});

	onMount(async () => {
		try {
			allItems = await getCatalog();
			if (!solidSpecies && solidItems.length > 0) {
				solidSpecies = solidItems[0].species_or_name;
			}
			if (!sheetType && sheetItems.length > 0) {
				sheetType = sheetItems[0].species_or_name;
			}
		} catch (e) {
			// Fallback to empty
		} finally {
			loading = false;
		}
	});

	function handleSubmit() {
		onAnalyze({ solid_species: solidSpecies, sheet_type: sheetType, all_solid: allSolid, display_units: displayUnits });
	}

	function openCatalog(tab: 'solid' | 'sheet') {
		catalogTab = tab;
		catalogOpen = true;
	}
</script>

<div class="space-y-4">
	{#if loading}
		<p class="text-[var(--color-text-secondary)] text-sm">Loading materials...</p>
	{:else}
		<Combobox
			label="Solid Lumber Species"
			placeholder="Search species..."
			items={uniqueSolidItems()}
			value={solidSpecies}
			onSelect={(v) => (solidSpecies = v)}
			onBrowseCatalog={() => openCatalog('solid')}
		/>

		<Combobox
			label="Sheet Goods"
			placeholder="Search sheets..."
			items={uniqueSheetItems()}
			value={sheetType}
			onSelect={(v) => (sheetType = v)}
			onBrowseCatalog={() => openCatalog('sheet')}
			disabled={allSolid}
		/>

		<div class="flex items-center gap-3">
			<label class="relative inline-flex items-center cursor-pointer">
				<input type="checkbox" bind:checked={allSolid} class="sr-only peer" />
				<div class="w-9 h-5 bg-[var(--color-border)] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[var(--color-primary)]"></div>
			</label>
			<span class="text-sm text-[var(--color-text)]">All solid lumber (no sheet goods)</span>
		</div>

		<div class="flex items-center gap-3">
			<span class="text-sm text-[var(--color-text)]">Display Units</span>
			<div class="flex gap-1">
				<button class="px-3 py-1 text-sm rounded transition-colors duration-150 {displayUnits === 'in' ? 'bg-[var(--color-primary)] text-white' : 'bg-[var(--color-border-strong)] text-[var(--color-text-secondary)]'}" onclick={() => (displayUnits = 'in')}>in</button>
				<button class="px-3 py-1 text-sm rounded transition-colors duration-150 {displayUnits === 'mm' ? 'bg-[var(--color-primary)] text-white' : 'bg-[var(--color-border-strong)] text-[var(--color-text-secondary)]'}" onclick={() => (displayUnits = 'mm')}>mm</button>
			</div>
		</div>

		<button onclick={handleSubmit} disabled={analyzing}
			class="w-full bg-[var(--color-primary)] text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-[var(--color-primary-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150">
			{analyzing ? 'Analyzing...' : 'Analyze'}
		</button>
	{/if}
</div>

<CatalogBrowser
	items={allItems}
	open={catalogOpen}
	onClose={() => (catalogOpen = false)}
	onSelect={(v) => {
		if (catalogTab === 'solid') solidSpecies = v;
		else sheetType = v;
	}}
	initialTab={catalogTab}
/>
```

- [ ] **Step 2: Verify in browser**

- Species dropdown: type to filter, shows prices and supplier badges
- Sheet dropdown: same behavior, disabled when "All solid" is checked
- "Browse Full Catalog" link: opens slide-over panel
- Catalog panel: Solid/Sheet tabs, search, supplier filter, click to select

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/components/Configure.svelte
git commit -m "$(cat <<'EOF'
feat: replace material dropdowns with searchable comboboxes

Species and sheet type selectors now use autocomplete with
inline prices and supplier badges. Browse Catalog link opens
the full catalog slide-over panel.
EOF
)"
```

---

### Task 16: Frontend — Preferences Page

**Files:**
- Create: `frontend/src/routes/preferences/+page.svelte`

- [ ] **Step 1: Create the preferences page**

Create `frontend/src/routes/preferences/+page.svelte`:

```svelte
<script lang="ts">
	import { onMount } from 'svelte';
	import { getPreferences, updatePreferences, getSuppliers, getCatalog } from '$lib/api';
	import Combobox from '$lib/components/Combobox.svelte';
	import type { UserPreferences, Supplier, CatalogItem, DisplayUnits } from '$lib/types';

	let suppliers = $state<Supplier[]>([]);
	let prefs = $state<UserPreferences>({
		enabled_suppliers: ['woodworkers_source'],
		default_species: null,
		default_sheet_type: null,
		default_units: 'in',
	});
	let catalogItems = $state<CatalogItem[]>([]);
	let loading = $state(true);
	let saving = $state(false);
	let saved = $state(false);

	const solidItems = $derived(() => {
		const seen = new Map<string, CatalogItem>();
		for (const item of catalogItems.filter(i => i.product_type === 'solid')) {
			if (!seen.has(item.species_or_name)) seen.set(item.species_or_name, item);
		}
		return Array.from(seen.values());
	});

	const sheetItems = $derived(() => {
		const seen = new Map<string, CatalogItem>();
		for (const item of catalogItems.filter(i => i.product_type === 'sheet')) {
			if (!seen.has(item.species_or_name)) seen.set(item.species_or_name, item);
		}
		return Array.from(seen.values());
	});

	onMount(async () => {
		try {
			const [p, s, c] = await Promise.all([getPreferences(), getSuppliers(), getCatalog()]);
			prefs = p;
			suppliers = s;
			catalogItems = c;
		} catch (e) {
			// Use defaults
		} finally {
			loading = false;
		}
	});

	function toggleSupplier(supplierId: string) {
		if (prefs.enabled_suppliers.includes(supplierId)) {
			prefs.enabled_suppliers = prefs.enabled_suppliers.filter(s => s !== supplierId);
		} else {
			prefs.enabled_suppliers = [...prefs.enabled_suppliers, supplierId];
		}
		saved = false;
	}

	async function handleSave() {
		saving = true;
		try {
			await updatePreferences(prefs);
			saved = true;
			setTimeout(() => (saved = false), 2000);
		} catch (e) {
			// Handle error
		} finally {
			saving = false;
		}
	}
</script>

<div class="max-w-2xl">
	<h2 class="text-lg font-semibold text-[var(--color-text)] mb-6">Preferences</h2>

	{#if loading}
		<p class="text-[var(--color-text-secondary)]">Loading...</p>
	{:else}
		<!-- Suppliers -->
		<div class="mb-8">
			<h3 class="text-sm font-semibold text-[var(--color-text)] mb-3">Lumber Suppliers</h3>
			<div class="space-y-2">
				{#each suppliers as supplier}
					<div class="flex items-center justify-between bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-4 py-3">
						<div>
							<div class="text-sm font-medium text-[var(--color-text)]">{supplier.name}</div>
							<div class="text-xs text-[var(--color-text-muted)]">{supplier.base_url}</div>
						</div>
						<label class="relative inline-flex items-center cursor-pointer">
							<input
								type="checkbox"
								checked={prefs.enabled_suppliers.includes(supplier.supplier_id)}
								onchange={() => toggleSupplier(supplier.supplier_id)}
								class="sr-only peer"
							/>
							<div class="w-9 h-5 bg-[var(--color-border)] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[var(--color-primary)]"></div>
						</label>
					</div>
				{/each}
			</div>
		</div>

		<!-- Defaults -->
		<div class="mb-8">
			<h3 class="text-sm font-semibold text-[var(--color-text)] mb-3">Default Materials</h3>
			<div class="space-y-4">
				<Combobox
					label="Default Species"
					placeholder="Select default species..."
					items={solidItems()}
					value={prefs.default_species || ''}
					onSelect={(v) => { prefs.default_species = v; saved = false; }}
				/>
				<Combobox
					label="Default Sheet Type"
					placeholder="Select default sheet type..."
					items={sheetItems()}
					value={prefs.default_sheet_type || ''}
					onSelect={(v) => { prefs.default_sheet_type = v; saved = false; }}
				/>
				<div>
					<label class="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider mb-1.5">Display Units</label>
					<div class="flex gap-1">
						<button
							class="px-3 py-1 text-sm rounded transition-colors duration-150 {prefs.default_units === 'in' ? 'bg-[var(--color-primary)] text-white' : 'bg-[var(--color-border-strong)] text-[var(--color-text-secondary)]'}"
							onclick={() => { prefs.default_units = 'in'; saved = false; }}
						>in</button>
						<button
							class="px-3 py-1 text-sm rounded transition-colors duration-150 {prefs.default_units === 'mm' ? 'bg-[var(--color-primary)] text-white' : 'bg-[var(--color-border-strong)] text-[var(--color-text-secondary)]'}"
							onclick={() => { prefs.default_units = 'mm'; saved = false; }}
						>mm</button>
					</div>
				</div>
			</div>
		</div>

		<!-- Save -->
		<button
			onclick={handleSave}
			disabled={saving}
			class="bg-[var(--color-primary)] text-white px-6 py-2 rounded-md text-sm font-medium hover:bg-[var(--color-primary-hover)] disabled:opacity-50 transition-colors duration-150"
		>
			{#if saving}
				Saving...
			{:else if saved}
				Saved
			{:else}
				Save Preferences
			{/if}
		</button>
	{/if}
</div>
```

- [ ] **Step 2: Verify in browser**

Navigate to `/preferences`:
- Supplier toggles for all three suppliers
- Default species and sheet type comboboxes
- Display units toggle
- Save button with feedback

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/preferences/+page.svelte
git commit -m "$(cat <<'EOF'
feat: add preferences page with supplier toggles and defaults

Users can enable/disable lumber suppliers and set default
species, sheet type, and display units. Settings persist
to Supabase user_preferences table.
EOF
)"
```

---

### Task 17: Frontend — Restyle Remaining Components

**Files:**
- Modify: `frontend/src/lib/components/Upload.svelte`
- Modify: `frontend/src/lib/components/Results.svelte`
- Modify: `frontend/src/lib/components/ModelViewer.svelte`

- [ ] **Step 1: Restyle Upload.svelte**

Update color tokens in `frontend/src/lib/components/Upload.svelte`:
- `var(--color-accent)` → `var(--color-primary)`
- `var(--color-surface-muted)` → `var(--color-surface-hover)`
- `var(--color-foreground-muted)` → `var(--color-text-secondary)`
- `var(--color-border-strong)` → keep (exists in new theme)
- `var(--color-destructive)` → keep

- [ ] **Step 2: Restyle Results.svelte**

Update all color tokens:
- `var(--color-primary)` → keep (remapped to indigo)
- `var(--color-foreground-muted)` → `var(--color-text-secondary)`
- `var(--color-foreground)` → `var(--color-text)`
- `var(--color-border)` → keep
- `var(--color-accent)` → `var(--color-primary)`
- `var(--color-accent-hover)` → `var(--color-primary-hover)`
- `bg-emerald-50` badges → `bg-emerald-900/20 text-emerald-400`
- `bg-amber-50` badges → `bg-amber-900/20 text-amber-400`
- `bg-purple-50` badges → `bg-purple-900/20 text-purple-400`
- `bg-gray-200` → `bg-[var(--color-border-strong)]`

- [ ] **Step 3: Update ModelViewer.svelte dark theme**

Update the Three.js scene colors:
- Scene background: `0x0f1219` (matches --color-bg)
- Grid helper color: `0x1e293b` (subtle grid on dark background)
- Material color: `0x6366f1` (indigo) or keep wood-tone `0xb88c5a` — up to user preference
- Ambient light: slightly brighter for dark scene

- [ ] **Step 4: Verify all components in browser**

Upload a .3mf file and check the full flow:
- Upload area: dark themed
- Model viewer: dark background
- Configure: comboboxes working
- Results tabs: all dark themed, badges visible
- Save/Download buttons: indigo primary color

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/components/Upload.svelte frontend/src/lib/components/Results.svelte frontend/src/lib/components/ModelViewer.svelte
git commit -m "feat: restyle Upload, Results, and ModelViewer for dark theme"
```

---

### Task 18: Frontend — Step Indicator Component

**Files:**
- Create: `frontend/src/lib/components/StepIndicator.svelte`
- Modify: `frontend/src/routes/+page.svelte`

- [ ] **Step 1: Create StepIndicator**

Create `frontend/src/lib/components/StepIndicator.svelte`:

```svelte
<script lang="ts">
	interface Props {
		currentStep: 1 | 2 | 3;
	}

	let { currentStep }: Props = $props();

	const steps = [
		{ number: 1, label: 'Upload' },
		{ number: 2, label: 'Configure' },
		{ number: 3, label: 'Results' },
	];
</script>

<div class="flex items-center gap-0 py-3">
	{#each steps as step, i}
		{#if i > 0}
			<div class="w-8 h-px {currentStep > step.number - 1 ? 'bg-[var(--color-primary)]' : 'bg-[var(--color-border)]'} mx-2"></div>
		{/if}
		<div class="flex items-center gap-1.5">
			<div class="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-semibold
				{currentStep >= step.number
					? 'bg-[var(--color-primary)] text-white'
					: 'bg-[var(--color-border-strong)] text-[var(--color-text-muted)]'}"
			>
				{step.number}
			</div>
			<span class="text-xs {currentStep >= step.number ? 'text-[var(--color-text)] font-medium' : 'text-[var(--color-text-muted)]'}">{step.label}</span>
		</div>
	{/each}
</div>
```

- [ ] **Step 2: Wire StepIndicator into +page.svelte**

In the authenticated section of `frontend/src/routes/+page.svelte`, add the step indicator above the main content:

```svelte
import StepIndicator from '$lib/components/StepIndicator.svelte';

<!-- Derive current step -->
const currentStep = $derived<1 | 2 | 3>(() => {
	if (analyzeResult) return 3;
	if (uploadResult) return 2;
	return 1;
});
```

Add `<StepIndicator currentStep={currentStep()} />` above the main content area.

- [ ] **Step 3: Verify in browser**

Progress through the flow: Upload (step 1 active) → Configure (step 2 active) → Results (step 3 active). Steps should visually indicate progress with indigo fills.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/components/StepIndicator.svelte frontend/src/routes/+page.svelte
git commit -m "feat: add step indicator for Upload → Configure → Results flow"
```

---

### Task 19: Frontend — Restyle Cut Layout and Diagram Components

**Files:**
- Modify: `frontend/src/lib/components/CutLayout.svelte`
- Modify: `frontend/src/lib/components/SheetDiagram.svelte`
- Modify: `frontend/src/lib/components/BoardDiagram.svelte`

- [ ] **Step 1: Update CutLayout.svelte colors**

Replace all old color tokens:
- `var(--color-foreground)` → `var(--color-text)`
- `var(--color-foreground-muted)` → `var(--color-text-secondary)`
- `var(--color-accent)` → `var(--color-primary)`
- `var(--color-accent-hover)` → `var(--color-primary-hover)`
- `var(--color-primary)` → already remapped
- `bg-gray-200` → `bg-[var(--color-border-strong)]`
- `bg-gray-100` → `bg-[var(--color-surface)]`

- [ ] **Step 2: Update SheetDiagram.svelte canvas colors**

Update the canvas drawing code:
- Background fill: `#0f1219` (dark)
- Sheet outline: `#2a3040` (border color)
- Part fill: `#6366f1` with 0.3 alpha (indigo translucent)
- Part stroke: `#6366f1` (indigo)
- Spare part fill: `#818cf8` with 0.2 alpha
- Text color: `#e2e8f0` (light text)
- Waste area: `#1e293b` (subtle)

- [ ] **Step 3: Update BoardDiagram.svelte canvas colors**

Same color mapping as SheetDiagram:
- Background: `#0f1219`
- Board outline: `#2a3040`
- Part fill: `#6366f1` alpha 0.3
- Part stroke: `#6366f1`
- Text: `#e2e8f0`

- [ ] **Step 4: Verify cut layouts look good on dark background**

Run a full analysis with cut optimization, check Sheet and Board diagrams render cleanly.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/components/CutLayout.svelte frontend/src/lib/components/SheetDiagram.svelte frontend/src/lib/components/BoardDiagram.svelte
git commit -m "feat: restyle cut layout and diagram components for dark theme"
```

---

### Task 20: Backend — Knotty Lumber and Makerstock Crawlers

**Files:**
- Create: `backend/app/suppliers/knotty_lumber.py`
- Create: `backend/app/suppliers/makerstock.py`
- Modify: `backend/run_crawl.py` — register new crawlers

- [ ] **Step 1: Research Knotty Lumber website structure**

Visit https://theknottylumberco.ca/ and inspect the product pages to understand HTML structure for scraping. Note the species, thicknesses, pricing format, and URL patterns.

- [ ] **Step 2: Create Knotty Lumber crawler**

Create `backend/app/suppliers/knotty_lumber.py`:

```python
"""Crawler for The Knotty Lumber Co (theknottylumberco.ca)."""

import logging
from datetime import datetime, timezone

from app.suppliers.crawler_base import CrawlerBase, CrawledProduct

logger = logging.getLogger(__name__)


# Static price table as initial fallback — replace with scraping once
# the site structure is analyzed
KNOTTY_SOLID_PRICES: dict[str, dict[str, float]] = {
    # Populate after researching theknottylumberco.ca
    # Example structure:
    # "Red Oak": {"4/4": 6.00, "8/4": 9.50},
}

KNOTTY_SHEET_PRICES: dict[str, dict[str, float]] = {
    # Populate after researching theknottylumberco.ca
}


class KnottyLumberCrawler(CrawlerBase):
    """Crawler for The Knotty Lumber Co."""

    supplier_id = "knotty_lumber"
    supplier_name = "The Knotty Lumber Co"
    base_url = "https://theknottylumberco.ca"

    def crawl(self) -> list[CrawledProduct]:
        now = datetime.now(timezone.utc)
        products: list[CrawledProduct] = []

        # TODO: Implement live scraping once site structure is analyzed.
        # For now, return static fallback data.

        for species, thicknesses in KNOTTY_SOLID_PRICES.items():
            for thickness, price in thicknesses.items():
                products.append(CrawledProduct(
                    supplier_id=self.supplier_id,
                    product_type="solid",
                    species_or_name=species,
                    thickness=thickness,
                    price=price,
                    unit="board_foot",
                    url=None,
                    crawled_at=now,
                ))

        for product_type, thicknesses in KNOTTY_SHEET_PRICES.items():
            for thickness, price in thicknesses.items():
                products.append(CrawledProduct(
                    supplier_id=self.supplier_id,
                    product_type="sheet",
                    species_or_name=product_type,
                    thickness=thickness,
                    price=price,
                    unit="sheet",
                    url=None,
                    crawled_at=now,
                ))

        return products
```

- [ ] **Step 3: Create Makerstock crawler (same pattern)**

Create `backend/app/suppliers/makerstock.py`:

```python
"""Crawler for Makerstock (makerstock.com)."""

import logging
from datetime import datetime, timezone

from app.suppliers.crawler_base import CrawlerBase, CrawledProduct

logger = logging.getLogger(__name__)


MAKERSTOCK_SOLID_PRICES: dict[str, dict[str, float]] = {
    # Populate after researching makerstock.com
}

MAKERSTOCK_SHEET_PRICES: dict[str, dict[str, float]] = {
    # Populate after researching makerstock.com
}


class MakerstockCrawler(CrawlerBase):
    """Crawler for Makerstock."""

    supplier_id = "makerstock"
    supplier_name = "Makerstock"
    base_url = "https://makerstock.com"

    def crawl(self) -> list[CrawledProduct]:
        now = datetime.now(timezone.utc)
        products: list[CrawledProduct] = []

        for species, thicknesses in MAKERSTOCK_SOLID_PRICES.items():
            for thickness, price in thicknesses.items():
                products.append(CrawledProduct(
                    supplier_id=self.supplier_id,
                    product_type="solid",
                    species_or_name=species,
                    thickness=thickness,
                    price=price,
                    unit="board_foot",
                    url=None,
                    crawled_at=now,
                ))

        for product_type, thicknesses in MAKERSTOCK_SHEET_PRICES.items():
            for thickness, price in thicknesses.items():
                products.append(CrawledProduct(
                    supplier_id=self.supplier_id,
                    product_type="sheet",
                    species_or_name=product_type,
                    thickness=thickness,
                    price=price,
                    unit="sheet",
                    url=None,
                    crawled_at=now,
                ))

        return products
```

- [ ] **Step 4: Register new crawlers in run_crawl.py**

In `backend/run_crawl.py`, add imports and registrations:

```python
from app.suppliers.knotty_lumber import KnottyLumberCrawler
from app.suppliers.makerstock import MakerstockCrawler

CRAWLERS: dict[str, type[CrawlerBase]] = {
    "woodworkers_source": WoodworkersSourceCrawler,
    "knotty_lumber": KnottyLumberCrawler,
    "makerstock": MakerstockCrawler,
}
```

- [ ] **Step 5: Verify listing**

```bash
cd /home/josebiro/gt/mayor/backend
python run_crawl.py --list
```

Expected: All 3 crawlers listed

- [ ] **Step 6: Commit**

```bash
git add backend/app/suppliers/knotty_lumber.py backend/app/suppliers/makerstock.py backend/run_crawl.py
git commit -m "$(cat <<'EOF'
feat: add Knotty Lumber and Makerstock crawler stubs

Crawler infrastructure ready for both suppliers. Static price
tables need to be populated after researching their websites.
Live scraping to be implemented once HTML structure is analyzed.
EOF
)"
```

---

### Task 21: Integration Test — Full Flow Verification

- [ ] **Step 1: Start the backend**

```bash
cd /home/josebiro/gt/mayor/backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

- [ ] **Step 2: Start the frontend**

```bash
cd /home/josebiro/gt/mayor/frontend
npm run dev -- --host 0.0.0.0
```

- [ ] **Step 3: Test the complete user journey**

1. Visit `/` unauthenticated → marketing landing page
2. Click "Get Started" → login page (dark theme)
3. Sign in → redirected to projects dashboard
4. Click "New Project" → upload flow with step indicator
5. Upload a .3mf file → model viewer (dark background)
6. Configure materials using combobox → "Browse Catalog" opens slide-over
7. Analyze → results tabs (dark theme, all badges visible)
8. Check cut layout diagrams → render on dark background
9. Save project → appears in projects dashboard
10. Click profile avatar → Preferences / Sign Out menu
11. Navigate to Preferences → toggle suppliers, set defaults, save
12. Sign out → back to marketing landing page

- [ ] **Step 4: Fix any integration issues found**

Address any styling inconsistencies, broken flows, or missing dark theme updates.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
chore: integration fixes for kerf redesign

Final polish after full-flow testing — fix any remaining
color token references, layout issues, or broken interactions.
EOF
)"
```
