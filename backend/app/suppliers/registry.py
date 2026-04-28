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
