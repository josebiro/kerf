import numpy as np
from app.models import BoardType

_ONE_SQ_FT_IN = 144.0


def compute_dimensions(vertices: np.ndarray) -> tuple[float, float, float]:
    """Compute axis-aligned bounding box dimensions from vertices (in mm).
    Returns (length, width, thickness) sorted descending.
    """
    mins = vertices.min(axis=0)
    maxs = vertices.max(axis=0)
    dims = maxs - mins
    dims_sorted = sorted(dims, reverse=True)
    return dims_sorted[0], dims_sorted[1], dims_sorted[2]


def classify_board_type(
    length_in: float,
    width_in: float,
    thickness_in: float,
    all_solid: bool = False,
) -> tuple[BoardType, str]:
    """Classify a part into a board type based on dimensions in inches.

    Rules evaluated top-to-bottom, first match wins:
      1. Thickness > 1.5"           → thick stock
      2. Thickness <= 3/4" AND face area > 1 sq ft AND width > 12" → sheet good
      3. Width > 12"                → solid lumber (glue-up needed)
      4. Otherwise                  → solid lumber

    If all_solid is True, sheet goods are reclassified as solid lumber.
    Returns (board_type, notes).
    """
    face_area = length_in * width_in

    if thickness_in > 1.5:
        return BoardType.THICK_STOCK, "May need lamination"

    if thickness_in <= 0.75 and face_area > _ONE_SQ_FT_IN and width_in > 12.0:
        if all_solid:
            glue_boards = max(2, int(np.ceil(width_in / 6.0)))
            return BoardType.SOLID, f"Glue-up: {glue_boards} boards (overridden from sheet)"
        return BoardType.SHEET, ""

    if width_in > 12.0:
        glue_boards = max(2, int(np.ceil(width_in / 6.0)))
        return BoardType.SOLID, f"Glue-up: {glue_boards} boards"

    return BoardType.SOLID, ""
