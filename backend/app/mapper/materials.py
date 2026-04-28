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


def _format_dim(inches: float) -> str:
    """Format inches as a clean string (drop trailing zeros)."""
    if inches == int(inches):
        return f'{int(inches)}"'
    return f'{inches:.2f}'.rstrip("0").rstrip(".") + '"'


def aggregate_shopping_list(parts: list[Part]) -> list[ShoppingItem]:
    # Track per-part details for descriptions
    solid_by_stock: dict[str, list[tuple[float, float, float, int, str]]] = {}  # stock → [(l, w, t, qty, name)]
    sheet_by_stock: dict[str, list[tuple[float, float, int, str]]] = {}  # stock → [(w, l, qty, name)]

    for part in parts:
        if part.board_type in (BoardType.SOLID, BoardType.THICK_STOCK):
            thickness_in = mm_to_inches(part.thickness_mm)
            width_in = mm_to_inches(part.width_mm)
            length_in = mm_to_inches(part.length_mm)
            entries = solid_by_stock.setdefault(part.stock, [])
            entries.append((length_in, width_in, thickness_in, part.quantity, part.name))
        else:
            width_in = mm_to_inches(part.width_mm) + 2 * _KERF
            length_in = mm_to_inches(part.length_mm) + 2 * _KERF
            entries = sheet_by_stock.setdefault(part.stock, [])
            entries.append((width_in, length_in, part.quantity, part.name))

    items: list[ShoppingItem] = []

    for stock, part_entries in solid_by_stock.items():
        total_bf = 0.0
        cut_pieces: list[str] = []
        max_width = 0.0
        max_length = 0.0

        for length_in, width_in, thickness_in, qty, name in part_entries:
            _, w_rough, t_rough = add_milling_allowance(length_in, width_in, thickness_in)
            l_rough = length_in + _MILL_LENGTH
            bf = calculate_board_feet(t_rough, w_rough, l_rough) * qty
            total_bf += bf
            max_width = max(max_width, w_rough)
            max_length = max(max_length, l_rough)
            piece = f'{_format_dim(length_in)} × {_format_dim(width_in)}'
            if qty > 1:
                piece += f" (×{qty})"
            cut_pieces.append(piece)

        thickness = stock.split()[0] if stock else ""
        description = f'Boards min {_format_dim(max_width)} wide × {_format_dim(max_length)} long'

        items.append(ShoppingItem(
            material=stock, thickness=thickness, quantity=round(total_bf, 1),
            unit="BF", description=description, cut_pieces=cut_pieces,
        ))

    for stock, part_entries in sheet_by_stock.items():
        all_dims: list[tuple[float, float]] = []
        cut_pieces: list[str] = []

        for width_in, length_in, qty, name in part_entries:
            for _ in range(qty):
                all_dims.append((width_in, length_in))
            piece = f'{_format_dim(length_in)} × {_format_dim(width_in)}'
            if qty > 1:
                piece += f" (×{qty})"
            cut_pieces.append(piece)

        thickness = stock.split('"')[0] + '"' if '"' in stock else ""
        sheets = calculate_sheets_needed(all_dims)
        description = f"{sheets} × 4' × 8' sheet{'s' if sheets > 1 else ''}"

        items.append(ShoppingItem(
            material=stock, thickness=thickness, quantity=float(sheets),
            unit="sheets", description=description, cut_pieces=cut_pieces,
        ))

    return items
