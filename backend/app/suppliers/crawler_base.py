"""Base class for supplier price crawlers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


_VALID_PRODUCT_TYPES = {"solid", "sheet"}
_VALID_UNITS = {"board_foot", "sheet", "linear_foot"}


@dataclass
class CrawledProduct:
    """A single product scraped from a supplier website."""

    supplier_id: str
    product_type: str  # "solid" or "sheet"
    species_or_name: str
    thickness: str
    price: float
    unit: str  # "board_foot", "sheet", or "linear_foot"
    url: str | None
    crawled_at: datetime

    def __post_init__(self):
        if self.product_type not in _VALID_PRODUCT_TYPES:
            raise ValueError(
                f"product_type must be one of {_VALID_PRODUCT_TYPES}, got {self.product_type!r}"
            )
        if self.unit not in _VALID_UNITS:
            raise ValueError(
                f"unit must be one of {_VALID_UNITS}, got {self.unit!r}"
            )


class CrawlerBase(ABC):
    """Abstract base class for supplier crawlers."""

    supplier_id: str
    supplier_name: str
    base_url: str

    @abstractmethod
    def crawl(self) -> list[CrawledProduct]:
        """Scrape the supplier site and return normalized products."""
        ...
