"""Crawler for Makerstock (makerstock.com)."""

import logging
from datetime import datetime, timezone

from app.suppliers.crawler_base import CrawlerBase, CrawledProduct

logger = logging.getLogger(__name__)

MAKERSTOCK_SOLID_PRICES: dict[str, dict[str, float]] = {}
MAKERSTOCK_SHEET_PRICES: dict[str, dict[str, float]] = {}


class MakerstockCrawler(CrawlerBase):
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
