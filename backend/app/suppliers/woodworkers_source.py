import json
import logging
import re
import time
from pathlib import Path

from app.suppliers.base import SupplierBase, Product
from app.suppliers.scraper import scrape_pages

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static price tables (used as fallback when scraping is unavailable)
# ---------------------------------------------------------------------------

# Prices in $/BF by species and thickness
SOLID_PRICES: dict[str, dict[str, float]] = {
    "Red Oak": {
        "4/4": 5.50,
        "5/4": 6.25,
        "6/4": 7.00,
        "8/4": 8.50,
    },
    "White Oak": {
        "4/4": 6.00,
        "5/4": 6.75,
        "6/4": 7.50,
        "8/4": 9.00,
    },
    "Walnut": {
        "4/4": 11.00,
        "5/4": 12.50,
        "6/4": 13.75,
        "8/4": 16.00,
    },
    "Hard Maple": {
        "4/4": 6.50,
        "5/4": 7.25,
        "6/4": 8.00,
        "8/4": 9.50,
    },
    "Cherry": {
        "4/4": 8.00,
        "5/4": 9.00,
        "6/4": 10.00,
        "8/4": 12.00,
    },
    "Poplar": {
        "4/4": 3.50,
        "5/4": 4.00,
        "6/4": 4.50,
        "8/4": 5.50,
    },
    "Ash": {
        "4/4": 5.75,
        "5/4": 6.50,
        "6/4": 7.25,
        "8/4": 8.75,
    },
    "Sapele": {
        "4/4": 7.50,
        "5/4": 8.50,
        "6/4": 9.50,
        "8/4": 11.50,
    },
}

# Prices in $/sheet by product type and thickness
SHEET_PRICES: dict[str, dict[str, float]] = {
    "Baltic Birch": {
        '1/4"': 28.00,
        '1/2"': 42.00,
        '3/4"': 58.00,
    },
    "Red Oak Veneer Ply": {
        '1/4"': 35.00,
        '1/2"': 52.00,
        '3/4"': 68.00,
    },
    "Walnut Veneer Ply": {
        '1/4"': 55.00,
        '1/2"': 80.00,
        '3/4"': 105.00,
    },
    "Maple Veneer Ply": {
        '1/4"': 38.00,
        '1/2"': 56.00,
        '3/4"': 72.00,
    },
    "Cherry Veneer Ply": {
        '1/4"': 48.00,
        '1/2"': 70.00,
        '3/4"': 92.00,
    },
    "MDF": {
        '1/4"': 18.00,
        '1/2"': 28.00,
        '3/4"': 38.00,
    },
    "Melamine": {
        '1/4"': 22.00,
        '1/2"': 32.00,
        '3/4"': 44.00,
    },
}

# ---------------------------------------------------------------------------
# Page URL registry
# ---------------------------------------------------------------------------

BASE_URL = "https://www.woodworkerssource.com"

LUMBER_PAGES: dict[str, str] = {
    "Red Oak": "/lumber/red-oak.html",
    "White Oak": "/lumber/white-oak-flat-sawn.html",
    "Walnut": "/lumber/walnut.html",
    "Hard Maple": "/lumber/hard-white-maple.html",
    "Cherry": "/lumber/cherry.html",
    "Poplar": "/lumber/poplar.html",
    "Ash": "/lumber/ash.html",
    "Sapele": "/lumber/exotic/Sapele.html",
}

PLYWOOD_PAGES: dict[str, str] = {
    "Baltic Birch": "/plywood-sheet-goods/baltic-birch-plywood.html",
}

CACHE_TTL = 86400  # 24 hours in seconds
CACHE_FILENAME = "woodworkers_source_catalog.json"

# Patterns for cleaning product names into species display names
_PLYWOOD_NAME_RE = re.compile(
    r'^[\d/]+"?\s*(?:\([^)]*\)\s*)?'  # leading thickness like '3/4" (18mm) '
)
_LUMBER_THICKNESS_RE = re.compile(r'\s*\d+/\d+\s*')  # ' 4/4 ', ' 8/4 '
_SUFFIX_RE = re.compile(
    r'\b(Lumber|Plywood|on\s+\w+\s+Core|Full\s+Size|Store\s+Pickup|Board|Sheet)\b.*$',
    re.IGNORECASE,
)
_CLEANUP_RE = re.compile(r'[—–\-]+\s*$')


def _extract_species(name: str, category: str = "solid") -> str:
    """Extract a clean species display name from a product name.

    Lumber:  "Red Oak 4/4 Lumber"           → "Red Oak"
    Plywood: "3/4\" (18mm) Premium Walnut Plywood on Combi Core..." → "Premium Walnut Ply"
    """
    s = name
    if category == "sheet":
        # Strip leading thickness + metric: '3/4" (18mm) '
        s = _PLYWOOD_NAME_RE.sub("", s)
    else:
        # Strip thickness like ' 4/4 '
        s = _LUMBER_THICKNESS_RE.sub(" ", s)

    # Strip trailing suffixes
    s = _SUFFIX_RE.sub("", s)
    s = _CLEANUP_RE.sub("", s)
    s = s.strip()

    # Add "Ply" suffix for sheet goods so "Premium Walnut" lumber vs ply are distinct
    if category == "sheet" and s and not s.endswith("Ply"):
        s += " Ply"

    return s


class WoodworkersSourceSupplier(SupplierBase):
    """Woodworkers Source supplier with optional live scraping.

    When ``use_scraper=True`` the supplier fetches live prices from the
    Woodworkers Source website.  Static prices are used as a fallback when
    scraping is unavailable or returns nothing.

    Fallback chain in ``get_catalog()``:
    1. Return in-memory catalog if already loaded.
    2. Try fresh cache (< 24h TTL).
    3. If use_scraper: try scraping → save to cache if successful.
    4. If scraping failed + cache_dir exists: try stale cache (ignore TTL).
    5. Final fallback: build from static prices (no URLs).
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        use_scraper: bool = False,
    ) -> None:
        self._cache_dir = cache_dir
        self._use_scraper = use_scraper
        self._catalog: list[Product] | None = None

        # Lookup indexes — populated lazily by _build_indexes()
        # (species, thickness) -> price_per_unit
        self._solid_prices: dict[tuple[str, str], float] = {}
        # (species, thickness) -> url | None
        self._solid_urls: dict[tuple[str, str], str | None] = {}
        # (product_type, thickness) -> price_per_unit
        self._sheet_prices: dict[tuple[str, str], float] = {}
        # (product_type, thickness) -> url | None
        self._sheet_urls: dict[tuple[str, str], str | None] = {}

    # ------------------------------------------------------------------
    # SupplierBase interface
    # ------------------------------------------------------------------

    def get_species_list(self) -> list[str]:
        self._ensure_indexes()
        seen: list[str] = []
        for (species, _) in self._solid_prices:
            if species not in seen:
                seen.append(species)
        return seen

    def get_sheet_types(self) -> list[str]:
        self._ensure_indexes()
        seen: list[str] = []
        for (pt, _) in self._sheet_prices:
            if pt not in seen:
                seen.append(pt)
        return seen

    def get_price(self, species: str, thickness: str, board_feet: float) -> float | None:
        self._ensure_indexes()
        per_bf = self._solid_prices.get((species, thickness))
        if per_bf is None:
            return None
        return per_bf * board_feet

    def get_sheet_price(self, product_type: str, thickness: str) -> float | None:
        self._ensure_indexes()
        return self._sheet_prices.get((product_type, thickness))

    def get_catalog(self) -> list[Product]:
        if self._catalog is not None:
            return self._catalog

        # 1. Fresh cache
        if self._cache_dir is not None:
            cached = self._load_cache(ignore_ttl=False)
            if cached is not None:
                self._catalog = cached
                self._build_indexes()
                return self._catalog

        # 2. Scraping
        if self._use_scraper:
            scraped = self._scrape()
            if scraped:
                self._catalog = scraped
                if self._cache_dir is not None:
                    self._save_cache(self._catalog)
                self._build_indexes()
                return self._catalog

            # 3. Stale cache fallback after scrape failure
            if self._cache_dir is not None:
                stale = self._load_cache(ignore_ttl=True)
                if stale is not None:
                    logger.warning("Scraping failed; using stale cache")
                    self._catalog = stale
                    self._build_indexes()
                    return self._catalog

        # 4. Static fallback
        self._catalog = self._build_static_catalog()
        if self._cache_dir is not None:
            self._save_cache(self._catalog)
        self._build_indexes()
        return self._catalog

    # ------------------------------------------------------------------
    # URL lookup methods
    # ------------------------------------------------------------------

    def get_product_url(self, species: str, thickness: str) -> str | None:
        """Return the product URL for a solid-wood species+thickness, or None."""
        self._ensure_indexes()
        return self._solid_urls.get((species, thickness))

    def get_sheet_url(self, product_type: str, thickness: str) -> str | None:
        """Return the product URL for a sheet good type+thickness, or None."""
        self._ensure_indexes()
        return self._sheet_urls.get((product_type, thickness))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_indexes(self) -> None:
        """Make sure the catalog and indexes are loaded."""
        if self._catalog is None:
            self.get_catalog()

    def _build_indexes(self) -> None:
        """Build lookup dicts from self._catalog."""
        self._solid_prices = {}
        self._solid_urls = {}
        self._sheet_prices = {}
        self._sheet_urls = {}
        for p in self._catalog or []:
            key = (p.species, p.thickness)
            if p.category == "solid":
                self._solid_prices[key] = p.price_per_unit
                self._solid_urls[key] = p.url
            else:
                self._sheet_prices[key] = p.price_per_unit
                self._sheet_urls[key] = p.url

    def _scrape(self) -> list[Product]:
        """Fetch live prices and convert to Product objects."""
        urls = [BASE_URL + path for path in LUMBER_PAGES.values()]
        urls += [BASE_URL + path for path in PLYWOOD_PAGES.values()]

        try:
            raw = scrape_pages(urls, BASE_URL)
        except Exception as exc:
            logger.warning("scrape_pages failed: %s", exc)
            return []

        if not raw:
            return []

        products: list[Product] = []
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

            # Normalize sheet thickness to include inch mark (e.g., "3/4" → '3/4"')
            # so it matches the material mapper's key format
            thick = thickness or ""
            if category == "sheet" and thick and not thick.endswith('"'):
                thick = thick + '"'

            products.append(
                Product(
                    name=name,
                    species=species,
                    thickness=thick,
                    price_per_unit=price,
                    unit=unit,
                    category=category,
                    url=url,
                )
            )

        return products

    def _build_static_catalog(self) -> list[Product]:
        """Build catalog from static price tables (no URLs)."""
        products: list[Product] = []

        for species, thicknesses in SOLID_PRICES.items():
            for thickness, price_per_bf in thicknesses.items():
                products.append(
                    Product(
                        name=f"{species} {thickness}",
                        species=species,
                        thickness=thickness,
                        price_per_unit=price_per_bf,
                        unit="BF",
                        category="solid",
                        url=None,
                    )
                )

        for product_type, thicknesses in SHEET_PRICES.items():
            for thickness, price_per_sheet in thicknesses.items():
                products.append(
                    Product(
                        name=f"{product_type} {thickness}",
                        species=product_type,
                        thickness=thickness,
                        price_per_unit=price_per_sheet,
                        unit="sheet",
                        category="sheet",
                        url=None,
                    )
                )

        return products

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
