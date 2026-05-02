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
    crawler = FakeCrawler()
    products = crawler.crawl()
    assert len(products) == 1
    assert products[0].species_or_name == "Red Oak"
    assert products[0].supplier_id == "fake_supplier"


def test_crawled_product_rejects_invalid_product_type():
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


from app.suppliers.woodworkers_source import WoodworkersSourceCrawler


def test_ws_crawler_has_correct_metadata():
    crawler = WoodworkersSourceCrawler()
    assert crawler.supplier_id == "woodworkers_source"
    assert crawler.supplier_name == "Woodworkers Source"
    assert "woodworkerssource.com" in crawler.base_url


def test_ws_crawler_static_fallback():
    crawler = WoodworkersSourceCrawler(use_scraper=False)
    products = crawler.crawl()
    assert len(products) > 0
    solid = [p for p in products if p.product_type == "solid"]
    sheet = [p for p in products if p.product_type == "sheet"]
    assert len(solid) > 0
    assert len(sheet) > 0
    red_oak_4_4 = [p for p in solid if p.species_or_name == "Red Oak" and p.thickness == "4/4"]
    assert len(red_oak_4_4) == 1
    assert red_oak_4_4[0].price == 5.50
    assert red_oak_4_4[0].unit == "board_foot"
