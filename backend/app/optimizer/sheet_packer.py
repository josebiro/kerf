"""2D shelf-based first-fit-decreasing bin packing for sheet goods."""

from dataclasses import dataclass
from app.models import Placement, SheetLayout


@dataclass
class PackingPiece:
    name: str
    width: float
    height: float
    is_spare: bool


@dataclass
class _Shelf:
    y: float
    height: float
    used_width: float


def pack_sheets(
    pieces: list[PackingPiece],
    sheet_w: float = 48.0,
    sheet_l: float = 96.0,
    kerf: float = 0.125,
    material: str = "",
) -> list[SheetLayout]:
    if not pieces:
        return []

    sorted_pieces = sorted(pieces, key=lambda p: p.height, reverse=True)
    sheets: list[dict] = []

    def new_sheet():
        sheets.append({"shelves": [], "placements": []})

    new_sheet()

    for piece in sorted_pieces:
        pw = piece.width + kerf
        ph = piece.height + kerf
        placed = False

        for sheet in sheets:
            for shelf in sheet["shelves"]:
                if shelf.used_width + pw <= sheet_w and piece.height <= shelf.height:
                    sheet["placements"].append(Placement(
                        part_name=piece.name, x=shelf.used_width, y=shelf.y,
                        width=piece.width, height=piece.height,
                        rotated=False, is_spare=piece.is_spare,
                    ))
                    shelf.used_width += pw
                    placed = True
                    break
            if placed:
                break

            shelf_y = sum(s.height + kerf for s in sheet["shelves"])
            if shelf_y + ph <= sheet_l:
                new_shelf = _Shelf(y=shelf_y, height=piece.height, used_width=pw)
                sheet["placements"].append(Placement(
                    part_name=piece.name, x=0, y=shelf_y,
                    width=piece.width, height=piece.height,
                    rotated=False, is_spare=piece.is_spare,
                ))
                sheet["shelves"].append(new_shelf)
                placed = True
                break

        if not placed:
            new_sheet()
            sheet = sheets[-1]
            new_shelf = _Shelf(y=0, height=piece.height, used_width=pw)
            sheet["placements"].append(Placement(
                part_name=piece.name, x=0, y=0,
                width=piece.width, height=piece.height,
                rotated=False, is_spare=piece.is_spare,
            ))
            sheet["shelves"].append(new_shelf)

    sheet_area = sheet_w * sheet_l
    results = []
    for sheet in sheets:
        if not sheet["placements"]:
            continue
        used_area = sum(p.width * p.height for p in sheet["placements"])
        waste = max(0, (1 - used_area / sheet_area) * 100)
        results.append(SheetLayout(
            material=material, width=sheet_w, length=sheet_l,
            placements=sheet["placements"], waste_percent=round(waste, 1),
        ))
    return results
