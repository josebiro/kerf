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
        has_premium = any("premium" in n.lower() for n in names)
        has_natural = any("natural" in n.lower() for n in names)
        assert has_premium or has_natural

    def test_walnut_extracts_prices(self):
        html = (FIXTURES / "walnut_page.html").read_text()
        products = parse_product_page(html, base_url="https://www.woodworkerssource.com")
        lumber = [p for p in products if p["unit"] == "BF"]
        for p in lumber:
            assert p["price"] > 5.0
            assert p["price"] < 50.0

    def test_walnut_finds_plywood(self):
        html = (FIXTURES / "walnut_page.html").read_text()
        products = parse_product_page(html, base_url="https://www.woodworkerssource.com")
        sheets = [p for p in products if p["unit"] == "sheet"]
        assert len(sheets) >= 1

    def test_empty_html_returns_empty(self):
        products = parse_product_page("<html><body></body></html>", base_url="https://www.woodworkerssource.com")
        assert products == []
