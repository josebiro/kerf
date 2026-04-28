from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Product:
    name: str
    species: str
    thickness: str
    price_per_unit: float
    unit: str       # "BF" or "sheet"
    category: str   # "solid" or "sheet"


class SupplierBase(ABC):
    @abstractmethod
    def get_catalog(self) -> list[Product]: ...

    @abstractmethod
    def get_price(self, species: str, thickness: str, board_feet: float) -> float | None: ...

    @abstractmethod
    def get_sheet_price(self, product_type: str, thickness: str) -> float | None: ...

    @abstractmethod
    def get_species_list(self) -> list[str]: ...

    @abstractmethod
    def get_sheet_types(self) -> list[str]: ...
