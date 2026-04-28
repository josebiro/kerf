import json
import time
import pytest
from pathlib import Path
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
