# Kerf Redesign — Design Spec

## Overview

A comprehensive redesign of the kerf application covering: authentication enforcement, UI modernization (dark precision theme), multi-supplier pricing architecture, searchable material selection, user preferences, and a marketing landing page.

Kerf transforms 3MF CAD files into cutting instructions, shopping lists, and cost estimates for woodworking projects. The current design uses warm browns and serif fonts ("folksy"). The redesign aligns it with modern CAD tool aesthetics (Fusion 360, Onshape) to feel native to its users' workflows.

## 1. Authentication

### Current State

- Supabase Auth with Google OAuth + email/password
- Upload, analyze, and optimize endpoints are public
- Report generation and project CRUD require auth

### Target State

- All endpoints require authentication — no anonymous usage
- Unauthenticated visitors see a marketing landing page
- Sign-in/sign-up methods unchanged: Google OAuth + email/password via Supabase
- Open sign-up (no waitlist or invite gates)

### Backend Changes

- `POST /api/upload` — switch from `get_optional_user()` to `require_user()`
- `POST /api/analyze` — switch to `require_user()`
- `POST /api/optimize` — switch to `require_user()`
- `GET /api/species`, `GET /api/sheet-types` — switch to `require_user()`
- Session-based file uploads tie to authenticated user ID
- All existing protected endpoints remain protected

### Frontend Changes

- App routes (`/`, `/projects`) redirect to `/login` if unauthenticated
- Marketing landing page served at `/` for unauthenticated users (see Section 6)
- Login page reskinned to match dark theme

## 2. Design System

### Theme: Dark Precision

Replaces all warm browns, tans, off-whites, and serif fonts with a dark, CAD-tool-inspired palette.

#### Colors (CSS Custom Properties)

| Token | Value | Usage |
|-------|-------|-------|
| `--color-bg` | `#0f1219` | Page background |
| `--color-bg-deep` | `#0a0e17` | Navbar, inset panels |
| `--color-surface` | `#1a1f2e` | Cards, dropdowns, panels |
| `--color-surface-hover` | `#252b3d` | Hover states, selected rows |
| `--color-border` | `#2a3040` | Default borders |
| `--color-border-strong` | `#1e293b` | Dividers, active borders |
| `--color-primary` | `#6366f1` | Indigo — buttons, accents, logo |
| `--color-primary-hover` | `#818cf8` | Indigo hover |
| `--color-text` | `#e2e8f0` | Primary text |
| `--color-text-secondary` | `#94a3b8` | Labels, secondary info |
| `--color-text-muted` | `#64748b` | Placeholder, tertiary |
| `--color-text-dim` | `#475569` | Disabled, hints |
| `--color-destructive` | `#ef4444` | Sign out, delete actions |

#### Typography

- **Font family**: `Inter` for everything (headings, body, UI labels)
- **Remove**: `DM Serif Display` — no serif fonts anywhere
- **Weights**: 400 (body), 500 (labels, emphasis), 600 (headings, buttons), 700 (logo mark text)
- **Sizes**: Follow existing Tailwind scale, no custom sizes needed

#### Spacing & Layout

- Consistent with current Tailwind utilities
- `max-w-6xl mx-auto` for content width
- Cards/panels: `border-radius: 8px`, `border: 1px solid var(--color-border)`
- Buttons: `border-radius: 6px`, `padding: 8px 16px`

### Logo

- Asset: `kerf-logo.png` (to be converted to SVG for production use)
- Shape: Lightning bolt / saw blade hybrid — large spiky entry at bottom-left curving convex upward to the right, saw teeth along the top edge diminishing in size (1/4 profile perspective), smooth bottom curve
- Color: `--color-primary` (indigo) on dark backgrounds, inverted for light contexts
- Appears in navbar alongside "kerf" wordmark in Inter 600
- Must work at favicon size (16x16, 32x32) and navbar size (~26px height)

## 3. Navigation & Layout

### Navbar

- Background: `--color-bg-deep`
- Bottom border: `1px solid --color-border-strong`
- Left side: Logo mark + "kerf" wordmark + tab navigation (Projects | New Project)
- Right side: Profile avatar (user initials in `--color-primary` circle)
- Active tab: `--color-text` on `--color-border-strong` background
- Inactive tab: `--color-text-secondary`, no background

### Profile Menu

- Trigger: Click profile avatar (initials circle, upper right)
- Dropdown panel: `--color-surface` background, `--color-border` border, 8px radius, shadow
- Items:
  - "Preferences" — navigates to `/preferences`
  - Divider
  - "Sign Out" — `--color-destructive` text, triggers `supabase.auth.signOut()`

### App Flow (Hybrid)

**Post-login landing: Project Dashboard**
- Grid of saved project cards (1 col mobile, 2 cols tablet, 3 cols desktop)
- Each card: thumbnail, project name, species, part count, cost estimate, date
- "+ New Project" card (dashed border) at the end of the grid
- "New Project" button in header and as a card

**New Project: Linear Flow**
- Step indicator bar: Upload (1) → Configure (2) → Results (3)
- Active step: indigo circle with number, white text
- Inactive steps: `--color-border-strong` circle, muted text
- Steps connected by `--color-border` lines
- Flow is the same as today (upload → configure materials → analyze → view results)
- Results page retains existing tabs: Parts List, Shopping List, Cost Estimate, Cut Layout

## 4. Supplier & Pricing Architecture

### Current State

- Single supplier: Woodworkers Source
- Live web scraping at request time via BeautifulSoup with 24-hour JSON file cache fallback
- `SupplierBase` ABC defines the interface
- Hardcoded static price fallbacks in `woodworkers_source.py`

### Target State: Crawl-and-Cache via Supabase

**Phase 1 — Crawl (offline)**

Each supplier implements a `Crawler` subclass:

```python
class CrawlerBase:
    supplier_id: str          # "woodworkers_source", "knotty_lumber", "makerstock"
    supplier_name: str        # Human-readable display name
    base_url: str             # Supplier website URL

    def crawl(self) -> list[CrawledProduct]:
        """Scrape the supplier site, return normalized products."""
        ...
```

`CrawledProduct` is a flat data class:
- `supplier_id: str`
- `product_type: str` — "solid" or "sheet"
- `species_or_name: str` — e.g. "Red Oak", "Baltic Birch"
- `thickness: str` — e.g. "4/4", "3/4\""
- `price: float`
- `unit: str` — "board_foot", "sheet", "linear_foot"
- `url: str` — product page link
- `crawled_at: datetime`

A single `run_crawl.py` script:
1. Iterates all registered crawlers
2. Calls `crawl()` on each
3. Upserts results into `supplier_prices` table
4. Logs run metadata to `crawl_runs` table
5. Runs via cron or manually

**Phase 2 — Read (app runtime)**

The existing `SupplierBase` interface becomes a thin read layer over Supabase:
- `get_species_list()` → `SELECT DISTINCT species_or_name FROM supplier_prices WHERE supplier_id IN (user's enabled suppliers) AND product_type = 'solid'`
- `get_price()` → query `supplier_prices` by species, thickness, supplier
- `get_product_url()` → query `supplier_prices` for the URL
- No scraping at request time

**Adding a new supplier** = write one `Crawler` subclass, register it in the crawler registry, run `run_crawl.py`. The app discovers it from the database automatically.

### Supabase Schema

```sql
-- Master supplier list
CREATE TABLE suppliers (
    supplier_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    base_url TEXT NOT NULL,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Crawled price data
CREATE TABLE supplier_prices (
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
CREATE TABLE crawl_runs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    supplier_id TEXT REFERENCES suppliers(supplier_id),
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    product_count INTEGER DEFAULT 0,
    errors TEXT[]
);

-- User preferences
CREATE TABLE user_preferences (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id),
    enabled_suppliers TEXT[] DEFAULT ARRAY['woodworkers_source'],
    default_species TEXT,
    default_sheet_type TEXT,
    default_units TEXT DEFAULT 'in' CHECK (default_units IN ('in', 'mm')),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

RLS policies on `user_preferences`: users can only read/write their own row. `supplier_prices` and `suppliers` are read-only for authenticated users.

### Suppliers

| ID | Name | URL | Status |
|----|------|-----|--------|
| `woodworkers_source` | Woodworkers Source | woodworkerssource.com | Existing — migrate scraper to Crawler |
| `knotty_lumber` | The Knotty Lumber Co | theknottylumberco.ca | New — write crawler |
| `makerstock` | Makerstock | makerstock.com | New — write crawler |

## 5. Material Selection UI

### Combobox (Default Interaction)

The species and sheet type dropdowns become searchable comboboxes:

- Text input with placeholder "Search species..." / "Search sheets..."
- Type to filter — matches against species/product name
- Dropdown shows matching results with inline price (e.g. "$12.50/bf")
- Supplier badge shown per result (WS, KL, MS)
- Keyboard navigable (arrow keys, enter to select)
- "Browse Catalog" link at bottom of dropdown opens the full catalog

### Catalog Browser (Full View)

Opens as a slide-over panel from the right edge:

- Tabs: Solid | Sheet
- Table columns: Species/Name, price by thickness (4/4, 6/4, 8/4 for solid; 1/4", 1/2", 3/4" for sheets), Supplier badge
- Filterable by supplier (dropdown filter)
- Searchable (text filter at top)
- Click a row to select that species/sheet and close the catalog
- Shows prices from all enabled suppliers — same species may appear multiple times with different supplier badges
- Selected row highlighted with `--color-surface-hover`

## 6. Marketing Landing Page

Served at `/` for unauthenticated visitors.

- Dark theme, consistent with app design
- Hero section: headline explaining what kerf does, subline with value prop
- Visual: screenshot or animated demo of the upload → 3D view → results workflow
- Two CTAs: "Get Started" (→ sign up) and "Sign In" (→ login)
- Feature callouts section: multi-supplier pricing, cut optimization, PDF reports
- Minimal footer
- No pricing page or plan tiers (free product, auth required)

## 7. Preferences Page

Route: `/preferences` (authenticated only)

### Supplier Management Section

- List of all suppliers from `suppliers` table
- Each row: toggle switch, supplier name, base URL, last crawl timestamp, product count
- Toggle enables/disables the supplier for the current user
- Changes saved to `user_preferences.enabled_suppliers`

### Defaults Section

- Default species: combobox (same component as main app)
- Default sheet type: combobox (same component as main app)
- Display units: toggle buttons (in / mm)
- These values pre-populate the Configure step when starting a new project
- Changes saved to `user_preferences` row

## 8. Components Changed

| Component | Change |
|-----------|--------|
| `app.css` | Complete theme replacement — new color tokens, remove DM Serif Display, Inter only |
| `+layout.svelte` | New navbar with tab nav, profile avatar menu, route guards |
| `+page.svelte` | Split into dashboard (authenticated home) and marketing landing (unauthenticated) |
| `login/+page.svelte` | Restyle to dark theme |
| `projects/+page.svelte` | Restyle project cards to dark theme, becomes the post-login home |
| `Upload.svelte` | Restyle upload zone, dark theme |
| `Configure.svelte` | Replace dropdowns with searchable comboboxes + catalog browser |
| `Results.svelte` | Restyle tabs, tables, badges to dark theme, supplier badges on prices |
| `CutLayout.svelte` | Restyle to dark theme |
| `SheetDiagram.svelte` | Update canvas colors for dark background |
| `BoardDiagram.svelte` | Update canvas colors for dark background |
| `ModelViewer.svelte` | Update scene background, grid, material colors for dark theme |
| **New**: `ProfileMenu.svelte` | Avatar dropdown with Preferences / Sign Out |
| **New**: `Combobox.svelte` | Searchable select component with inline prices |
| **New**: `CatalogBrowser.svelte` | Modal/slide-over full catalog view |
| **New**: `StepIndicator.svelte` | Upload → Configure → Results progress bar |
| **New**: `preferences/+page.svelte` | Preferences page with supplier toggles and defaults |
| **New**: `LandingPage.svelte` | Marketing landing for unauthenticated visitors |

## 9. Backend Changes

| File | Change |
|------|--------|
| `main.py` | All endpoints switch to `require_user()` |
| `auth.py` | Remove `get_optional_user()` (no longer needed) |
| `suppliers/base.py` | `SupplierBase` reads from Supabase instead of scraping |
| `suppliers/registry.py` | Registry reads from `suppliers` table |
| `suppliers/scraper.py` | Refactored into crawler base class |
| `suppliers/woodworkers_source.py` | Refactored to `Crawler` subclass |
| **New**: `suppliers/crawler_base.py` | `CrawlerBase` ABC and `CrawledProduct` model |
| **New**: `suppliers/knotty_lumber.py` | Knotty Lumber Co crawler |
| **New**: `suppliers/makerstock.py` | Makerstock crawler |
| **New**: `run_crawl.py` | CLI script to run all crawlers and upsert to Supabase |
| `database.py` | Add user_preferences CRUD |
| **New API**: `GET /api/preferences` | Read user preferences |
| **New API**: `PUT /api/preferences` | Update user preferences |
| **New API**: `GET /api/catalog` | Full catalog — accepts `?type=solid\|sheet` and `?search=<term>` query params, returns prices from user's enabled suppliers |
| **Deprecated**: `GET /api/species`, `GET /api/sheet-types` | Replaced by `/api/catalog` — remove after frontend migration |

## 10. Out of Scope

- Logo vector refinement (asset provided as PNG, SVG conversion handled separately)
- Mobile-specific responsive breakpoints beyond current Tailwind defaults
- Dark/light theme toggle (dark only)
- Payment / subscription tiers
- Email notifications
- Crawler scheduling infrastructure (cron setup is operational, not app code)
