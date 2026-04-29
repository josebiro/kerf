"""Cut optimization orchestrator."""

from app.models import (
    Part, ShoppingItem, BoardType, BufferConfig, BoardSizeConfig,
    SheetSizeConfig, OptimizeResponse, OptimizeSummary,
)
from app.optimizer.buffer import apply_spare_parts, apply_percentage_buffer
from app.optimizer.sheet_packer import pack_sheets, PackingPiece
from app.optimizer.lumber_packer import pack_lumber, LumberPiece
from app.units import mm_to_inches

DEFAULT_BOARD_SIZES = {
    "4/4": BoardSizeConfig(width=6.0, length=96.0),
    "5/4": BoardSizeConfig(width=6.0, length=96.0),
    "6/4": BoardSizeConfig(width=6.0, length=96.0),
    "8/4": BoardSizeConfig(width=6.0, length=72.0),
}

SHEET_WIDTH = 48.0
SHEET_LENGTH = 96.0
KERF = 0.125
MILL_LENGTH = 1.0
MILL_WIDTH = 0.5


def _expand_parts(parts: list[Part]) -> list[Part]:
    """Expand grouped parts (qty > 1) into individual instances."""
    expanded = []
    for part in parts:
        for i in range(part.quantity):
            suffix = f" #{i+1}" if part.quantity > 1 else ""
            expanded.append(part.model_copy(update={
                "name": f"{part.name}{suffix}",
                "quantity": 1,
            }))
    return expanded


def run_optimization(
    parts: list[Part],
    shopping_list: list[ShoppingItem],
    solid_species: str,
    sheet_type: str,
    buffer_config: BufferConfig = BufferConfig(),
    board_sizes: dict[str, BoardSizeConfig] | None = None,
    sheet_size: SheetSizeConfig | None = None,
) -> OptimizeResponse:
    """Run the full cut optimization pipeline."""
    sizes = {**DEFAULT_BOARD_SIZES, **(board_sizes or {})}
    s_size = sheet_size or SheetSizeConfig()

    sheet_parts = [p for p in parts if p.board_type == BoardType.SHEET]
    lumber_parts = [p for p in parts if p.board_type in (BoardType.SOLID, BoardType.THICK_STOCK)]

    sheet_expanded = _expand_parts(sheet_parts)
    lumber_expanded = _expand_parts(lumber_parts)

    # Apply sheet buffer
    if buffer_config.sheet_mode == "extra_parts" and sheet_parts:
        sheet_with_buffer = apply_spare_parts(sheet_expanded, int(buffer_config.sheet_value))
    else:
        sheet_with_buffer = list(sheet_expanded)

    # Apply lumber buffer
    if buffer_config.lumber_mode == "extra_parts" and lumber_parts:
        spares_added = apply_spare_parts(lumber_parts, int(buffer_config.lumber_value))
        spare_parts_only = [p for p in spares_added if getattr(p, "is_spare", False)]
        lumber_spare_expanded = _expand_parts(spare_parts_only)
        lumber_with_buffer = lumber_expanded + lumber_spare_expanded
    else:
        lumber_with_buffer = list(lumber_expanded)

    # Pack sheets
    sheet_pieces = [
        PackingPiece(
            name=p.name,
            width=mm_to_inches(p.width_mm) + 2 * KERF,
            height=mm_to_inches(p.length_mm) + 2 * KERF,
            is_spare=getattr(p, "is_spare", False),
        )
        for p in sheet_with_buffer
    ]
    sheet_layouts = pack_sheets(sheet_pieces, s_size.width, s_size.length, KERF, material=sheet_type)

    # Pack lumber by thickness group
    board_layouts = []
    thickness_groups: dict[str, list[Part]] = {}
    for p in lumber_with_buffer:
        rough = p.stock.split()[0] if p.stock else "4/4"
        thickness_groups.setdefault(rough, []).append(p)

    for thickness, group_parts in thickness_groups.items():
        size = sizes.get(thickness, BoardSizeConfig())
        lumber_pieces = [
            LumberPiece(
                name=p.name,
                length=mm_to_inches(p.length_mm) + MILL_LENGTH,
                width=mm_to_inches(p.width_mm) + MILL_WIDTH,
                is_spare=getattr(p, "is_spare", False),
            )
            for p in group_parts
        ]
        layouts = pack_lumber(
            lumber_pieces, size.width, size.length, KERF,
            material=f"{thickness} {solid_species}", thickness=thickness,
        )
        board_layouts.extend(layouts)

    # Summary
    total_sheets = len(sheet_layouts)
    total_boards = len(board_layouts)
    all_waste = [s.waste_percent for s in sheet_layouts] + [b.waste_percent for b in board_layouts]
    avg_waste = sum(all_waste) / len(all_waste) if all_waste else 0.0
    total_spares = sum(
        1 for layout in sheet_layouts + board_layouts
        for p in layout.placements if p.is_spare
    )

    # Updated shopping list
    updated = list(shopping_list)
    for i, item in enumerate(updated):
        if item.unit == "sheets":
            matching = [s for s in sheet_layouts if sheet_type in (s.material or "")]
            if matching:
                updated[i] = item.model_copy(update={"quantity": float(len(matching))})
        elif item.unit == "BF":
            matching = [b for b in board_layouts if item.thickness and b.thickness == item.thickness]
            if matching:
                total_bf = sum(b.width * b.length / 144.0 for b in matching)
                updated[i] = item.model_copy(update={"quantity": round(total_bf, 1)})

    return OptimizeResponse(
        sheets=sheet_layouts,
        boards=board_layouts,
        summary=OptimizeSummary(
            total_sheets=total_sheets,
            total_boards=total_boards,
            avg_waste_percent=round(avg_waste, 1),
            total_spare_parts=total_spares,
        ),
        updated_shopping_list=updated,
        buffer_config=buffer_config,
        board_sizes=sizes,
        sheet_size=s_size,
    )
