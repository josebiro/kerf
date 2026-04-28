import math
from app.models import BoardType, Part, ShoppingItem
from app.units import mm_to_inches

_STANDARD_THICKNESSES = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75]
_SNAP_TOLERANCE = 0.0625  # 1/16"

_FINISHED_TO_ROUGH = {
    0.25: "4/4", 0.5: "4/4", 0.75: "4/4",
    1.0: "5/4", 1.25: "6/4", 1.5: "8/4", 1.75: "8/4",
}

_MILL_LENGTH = 1.0
_MILL_WIDTH = 0.5
_MILL_THICKNESS = 0.25
_SHEET_WIDTH = 48.0
_SHEET_LENGTH = 96.0
_KERF = 0.125

_THICKNESS_TO_FRACTION = {
    0.25: "1/4", 0.5: "1/2", 0.75: "3/4",
    1.0: "1", 1.25: "1-1/4", 1.5: "1-1/2", 1.75: "1-3/4",
}


def _thickness_label(thickness_in: float) -> str:
    """Return a fraction string for standard thicknesses, else decimal."""
    return _THICKNESS_TO_FRACTION.get(thickness_in, str(thickness_in))


def snap_thickness_to_standard(thickness_in: float) -> float:
    for std in _STANDARD_THICKNESSES:
        if abs(thickness_in - std) <= _SNAP_TOLERANCE:
            return std
    return thickness_in


def rough_thickness_for(finished_in: float) -> str:
    for finished, rough in sorted(_FINISHED_TO_ROUGH.items()):
        if finished >= finished_in:
            return rough
    return "8/4"


def add_milling_allowance(length_in: float, width_in: float, thickness_in: float) -> tuple[float, float, float]:
    return (length_in + _MILL_LENGTH, width_in + _MILL_WIDTH, thickness_in + _MILL_THICKNESS)


def calculate_board_feet(thickness_in: float, width_in: float, length_in: float) -> float:
    return (thickness_in * width_in * length_in) / 144.0


def calculate_sheets_needed(parts: list[tuple[float, float]]) -> int:
    sheet_area = _SHEET_WIDTH * _SHEET_LENGTH
    total_area = sum(w * l for w, l in parts)
    return max(1, math.ceil(total_area / sheet_area))


def map_part_to_stock(part: Part, species: str = "", sheet_type: str = "") -> Part:
    thickness_in = mm_to_inches(part.thickness_mm)
    snapped = snap_thickness_to_standard(thickness_in)
    if part.board_type == BoardType.SHEET:
        label = _thickness_label(snapped)
        stock = f'{label}" {sheet_type}' if sheet_type else f'{label}" plywood'
        return part.model_copy(update={"stock": stock})
    if part.board_type == BoardType.THICK_STOCK:
        rough = "8/4"
        stock = f"{rough} {species}" if species else f"{rough} hardwood"
        notes = part.notes if part.notes else "May need lamination"
        return part.model_copy(update={"stock": stock, "notes": notes})
    rough = rough_thickness_for(snapped)
    stock = f"{rough} {species}" if species else f"{rough} hardwood"
    return part.model_copy(update={"stock": stock})


def aggregate_shopping_list(parts: list[Part]) -> list[ShoppingItem]:
    solid_by_stock: dict[str, float] = {}
    sheet_by_stock: dict[str, list[tuple[float, float]]] = {}
    for part in parts:
        if part.board_type in (BoardType.SOLID, BoardType.THICK_STOCK):
            thickness_in = mm_to_inches(part.thickness_mm)
            width_in = mm_to_inches(part.width_mm)
            length_in = mm_to_inches(part.length_mm)
            _, w_rough, t_rough = add_milling_allowance(length_in, width_in, thickness_in)
            l_rough = length_in + _MILL_LENGTH
            bf = calculate_board_feet(t_rough, w_rough, l_rough) * part.quantity
            solid_by_stock[part.stock] = solid_by_stock.get(part.stock, 0.0) + bf
        else:
            width_in = mm_to_inches(part.width_mm) + 2 * _KERF
            length_in = mm_to_inches(part.length_mm) + 2 * _KERF
            sheet_parts = sheet_by_stock.setdefault(part.stock, [])
            for _ in range(part.quantity):
                sheet_parts.append((width_in, length_in))
    items: list[ShoppingItem] = []
    for stock, bf in solid_by_stock.items():
        thickness = stock.split()[0] if stock else ""
        items.append(ShoppingItem(material=stock, thickness=thickness, quantity=round(bf, 1), unit="BF"))
    for stock, part_dims in sheet_by_stock.items():
        thickness = stock.split('"')[0] + '"' if '"' in stock else ""
        sheets = calculate_sheets_needed(part_dims)
        items.append(ShoppingItem(material=stock, thickness=thickness, quantity=float(sheets), unit="sheets"))
    return items
