from app.suppliers.base import SupplierBase
from app.suppliers.woodworkers_source import WoodworkersSourceSupplier

_SUPPLIERS: dict[str, type[SupplierBase]] = {
    "woodworkers_source": WoodworkersSourceSupplier,
}
_instances: dict[str, SupplierBase] = {}


def get_supplier(name: str) -> SupplierBase:
    if name not in _SUPPLIERS:
        raise KeyError(f"Unknown supplier: {name!r}")
    if name not in _instances:
        _instances[name] = _SUPPLIERS[name]()
    return _instances[name]


def list_suppliers() -> list[str]:
    return list(_SUPPLIERS.keys())
