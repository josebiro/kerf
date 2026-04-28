# Woodworkers Source Price Scraper — Design Spec

**Date:** 2026-04-27
**Status:** Draft
**Parent:** `docs/superpowers/specs/2026-04-27-3mf-cut-list-generator-design.md`

## Overview

Replace the static placeholder prices in the Woodworkers Source supplier module with a real scraper that fetches current prices and product URLs from woodworkerssource.com. Add product links through the data model so users can click through to buy materials.

## Goals

- Scrape real per-BF lumber prices and per-sheet plywood prices from woodworkerssource.com
- Capture product page URLs for each material
- Surface product links in the shopping list and cost estimate UI
- Show all species variants (e.g., "Premium Black Walnut" and "Natural Walnut" as separate options)
- Graceful fallback: stale cache → static prices → prices unavailable

## Non-Goals

- Cart integration or automated ordering
- Scraping board dimensions/availability (just price + URL)
- Monitoring price changes over time

---

## Site Structure (as of 2026-04-27)

### Lumber

Each species has a landing page listing all products in a grid:

- **URL pattern:** `https://www.woodworkerssource.com/lumber/{species-slug}.html`
- **Examples:**
  - `/lumber/red-oak.html` — Red Oak (4/4 $4.99/BF, 6/4 $5.99/BF, 8/4 $6.49/BF)
  - `/lumber/walnut.html` — Walnut (Natural 4/4 $11.99/BF, Premium 4/4 $17.99/BF, etc.)
  - `/lumber/cherry.html`, `/lumber/hard-white-maple.html`, etc.

**What we scrape from each page:** Product name, thickness (4/4, 5/4, 6/4, 8/4, etc.), price per BF, and product page URL. We filter to items priced "/BF" — ignoring packs, samples, dowels, veneers, and other product types.

### Plywood / Sheet Goods

Sheet goods are organized by type:

- **URL pattern:** `https://www.woodworkerssource.com/plywood-sheet-goods/{product-slug}.html`
- **Examples:**
  - `/plywood-sheet-goods/baltic-birch-plywood.html`

Some sheet goods appear on species pages (e.g., Walnut plywood listed on the walnut page). The scraper should capture these too.

**What we scrape:** Product name, thickness, price per sheet, and product page URL. Filter to items priced "/Sheet".

---

## Scraper Design

### Pages to Scrape

A registry of known species/product landing page URLs:

```python
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
    # Additional pages discovered during implementation
}
```

This list is maintained manually. Adding a new species means adding one URL entry.

### Parsing Strategy

Each landing page has a product grid. For each product card:

1. Extract product name text
2. Extract price text (e.g., "$4.99", "$17.99")
3. Extract price unit text (e.g., "/BF", "/Sheet", "/SF", "/Pack", "ea.")
4. Extract product link (href)
5. Filter: keep only items where unit is "/BF" (lumber) or "/Sheet" (sheet goods)
6. Parse thickness from product name (look for patterns like "4/4", "6/4", "8/4", "3/4\"", "1/2\"")
7. Parse species variant from product name (e.g., "Premium Black Walnut" vs "Natural Walnut")

### Variant Handling

When a species page has multiple variant lines (Premium vs Natural), each variant becomes a separate entry in the species list. The species dropdown shows:

- "Red Oak" (one variant)
- "Premium Black Walnut" (variant 1)
- "Natural Walnut" (variant 2)
- "Hard Maple" (one variant)

The variant name is parsed from the product name by stripping the thickness suffix.

### Rate Limiting

- 1 request per second between page fetches
- ~10-15 pages total → full scrape takes ~15 seconds
- Scraping happens on first request after cache expires, not on server startup

### Caching

Uses the existing JSON cache infrastructure with 24h TTL. The cache now also stores product URLs.

**Fallback chain:**
1. Fresh cache (< 24h) → use it
2. Stale cache (> 24h) → attempt scrape → if fails, use stale cache with a warning
3. No cache + scrape fails → fall back to static prices (current hardcoded tables) with a warning
4. Static prices used → `url` fields are `None`

### Error Handling

- Individual page fetch failure → skip that species, log warning, continue with others
- HTML structure changed (no products found) → skip, log warning
- All pages fail → fall back to static prices
- Never let scraping failure prevent the analyze endpoint from working

---

## Data Model Changes

### Product (backend/app/suppliers/base.py)

Add `url` field:

```python
@dataclass
class Product:
    name: str
    species: str
    thickness: str
    price_per_unit: float
    unit: str       # "BF" or "sheet"
    category: str   # "solid" or "sheet"
    url: str | None = None  # NEW: product page URL
```

### ShoppingItem (backend/app/models.py)

Add `url` field:

```python
class ShoppingItem(BaseModel):
    material: str
    thickness: str
    quantity: float
    unit: str
    unit_price: float | None = None
    description: str = ""
    cut_pieces: list[str] = []
    url: str | None = None  # NEW: link to supplier product page
```

### Frontend types.ts

Add `url` field to `ShoppingItem`:

```typescript
export interface ShoppingItem {
    // ... existing fields ...
    url: string | null;
}
```

---

## Frontend Changes

### Shopping List Tab

Each shopping list card gets a "View on Woodworkers Source" link when `url` is not null. Opens in a new tab.

### Cost Estimate Tab

Material name becomes a clickable link to the product page when `url` is available.

---

## API Changes

### GET /api/species

Now returns the full list of species variants found by the scraper (e.g., "Premium Black Walnut", "Natural Walnut") instead of a hardcoded list.

### GET /api/sheet-types

Same — returns what the scraper found.

### POST /api/analyze response

`shopping_list[].url` field is now populated with the product page URL when available.

---

## Testing

- Mock HTML responses for scraper tests (don't hit the real site in CI)
- Test parsing with representative HTML snapshots from real pages
- Test fallback chain: cache miss → scrape failure → static prices
- Test variant parsing (Premium vs Natural)
- Existing tests continue to pass (static prices still work as fallback)
