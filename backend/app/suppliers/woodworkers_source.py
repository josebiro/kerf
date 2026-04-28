import json
import time
from pathlib import Path

from app.suppliers.base import SupplierBase, Product


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

CACHE_TTL = 86400  # 24 hours in seconds
CACHE_FILENAME = "woodworkers_source_catalog.json"


class WoodworkersSourceSupplier(SupplierBase):
    """Static-price supplier implementation for Woodworkers Source.

    Live scraping is a future enhancement; this version uses curated
    baseline prices. A JSON cache with a 24-hour TTL avoids rebuilding
    the catalog on every instantiation.
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        self._cache_dir = cache_dir
        self._catalog: list[Product] | None = None

    # ------------------------------------------------------------------
    # SupplierBase interface
    # ------------------------------------------------------------------

    def get_species_list(self) -> list[str]:
        return list(SOLID_PRICES.keys())

    def get_sheet_types(self) -> list[str]:
        return list(SHEET_PRICES.keys())

    def get_price(self, species: str, thickness: str, board_feet: float) -> float | None:
        species_prices = SOLID_PRICES.get(species)
        if species_prices is None:
            return None
        per_bf = species_prices.get(thickness)
        if per_bf is None:
            return None
        return per_bf * board_feet

    def get_sheet_price(self, product_type: str, thickness: str) -> float | None:
        type_prices = SHEET_PRICES.get(product_type)
        if type_prices is None:
            return None
        return type_prices.get(thickness)

    def get_catalog(self) -> list[Product]:
        if self._catalog is not None:
            return self._catalog

        # Try loading from cache first
        if self._cache_dir is not None:
            cached = self._load_cache()
            if cached is not None:
                self._catalog = cached
                return self._catalog

        # Build fresh catalog
        self._catalog = self._build_catalog()

        # Persist to cache
        if self._cache_dir is not None:
            self._save_cache(self._catalog)

        return self._catalog

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_catalog(self) -> list[Product]:
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
                }
                for p in catalog
            ],
        }
        self._cache_path().write_text(json.dumps(payload, indent=2))

    def _load_cache(self) -> list[Product] | None:
        path = self._cache_path()
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text())
            age = time.time() - payload["timestamp"]
            if age > CACHE_TTL:
                return None
            return [Product(**item) for item in payload["products"]]
        except (KeyError, TypeError, json.JSONDecodeError):
            return None
