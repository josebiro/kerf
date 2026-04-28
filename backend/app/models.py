from enum import Enum
from pydantic import BaseModel, computed_field
from app.units import mm_to_inches


class BoardType(str, Enum):
    SOLID = "solid"
    SHEET = "sheet"
    THICK_STOCK = "thick_stock"


class Part(BaseModel):
    name: str
    quantity: int
    length_mm: float
    width_mm: float
    thickness_mm: float
    board_type: BoardType
    stock: str
    notes: str

    def display_dimensions(self, units: str) -> str:
        if units == "mm":
            return f"{self.length_mm} × {self.width_mm} × {self.thickness_mm} mm"
        l = round(mm_to_inches(self.length_mm), 2)
        w = round(mm_to_inches(self.width_mm), 2)
        t = round(mm_to_inches(self.thickness_mm), 2)
        return f'{l}" × {w}" × {t}"'


class ShoppingItem(BaseModel):
    material: str
    thickness: str
    quantity: float
    unit: str
    unit_price: float | None = None

    @computed_field
    @property
    def subtotal(self) -> float | None:
        if self.unit_price is None:
            return None
        return self.quantity * self.unit_price


class CostEstimate(BaseModel):
    items: list[ShoppingItem]

    @computed_field
    @property
    def total(self) -> float | None:
        subtotals = [item.subtotal for item in self.items]
        if any(s is None for s in subtotals):
            return None
        return sum(subtotals)


class AnalyzeRequest(BaseModel):
    session_id: str
    solid_species: str
    sheet_type: str
    all_solid: bool = False
    display_units: str = "in"


class PartPreview(BaseModel):
    name: str
    vertex_count: int


class UploadResponse(BaseModel):
    session_id: str
    file_url: str
    parts_preview: list[PartPreview]


class AnalyzeResponse(BaseModel):
    parts: list[Part]
    shopping_list: list[ShoppingItem]
    cost_estimate: CostEstimate
    display_units: str
