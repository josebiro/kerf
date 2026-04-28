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
    description: str = ""
    cut_pieces: list[str] = []
    url: str | None = None

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
        """Sum of available subtotals. None only if ALL prices are missing."""
        subtotals = [item.subtotal for item in self.items if item.subtotal is not None]
        if not subtotals:
            return None
        return sum(subtotals)

    @computed_field
    @property
    def has_missing_prices(self) -> bool:
        """True if any item is missing pricing."""
        return any(item.subtotal is None for item in self.items)


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


class ReportRequest(BaseModel):
    session_id: str
    solid_species: str
    sheet_type: str
    all_solid: bool = False
    display_units: str = "in"
    thumbnail: str | None = None  # base64 data URL from canvas


class ProjectCreate(BaseModel):
    name: str
    filename: str
    session_id: str
    solid_species: str
    sheet_type: str
    all_solid: bool = False
    display_units: str = "in"
    analysis_result: AnalyzeResponse
    thumbnail: str | None = None


class ProjectSummary(BaseModel):
    id: str
    name: str
    filename: str
    solid_species: str
    sheet_type: str
    part_count: int
    unique_parts: int
    estimated_cost: float | None
    thumbnail_url: str | None
    created_at: str
    updated_at: str


class ProjectDetail(BaseModel):
    id: str
    name: str
    filename: str
    solid_species: str
    sheet_type: str
    all_solid: bool
    display_units: str
    analysis_result: AnalyzeResponse
    file_url: str
    thumbnail_url: str | None
    created_at: str
    updated_at: str
