"""1D first-fit-decreasing strip packing for solid lumber."""

from dataclasses import dataclass
from app.models import Placement, BoardLayout


@dataclass
class LumberPiece:
    name: str
    length: float
    width: float
    is_spare: bool


@dataclass
class _BoardSlot:
    y: float
    height: float
    used_length: float


def pack_lumber(
    pieces: list[LumberPiece],
    board_w: float = 6.0,
    board_l: float = 96.0,
    kerf: float = 0.125,
    material: str = "",
    thickness: str = "",
) -> list[BoardLayout]:
    if not pieces:
        return []

    sorted_pieces = sorted(pieces, key=lambda p: p.length, reverse=True)
    boards: list[dict] = []

    def new_board():
        boards.append({"slots": [], "placements": []})

    new_board()

    for piece in sorted_pieces:
        pl = piece.length + kerf
        pw = piece.width + kerf
        placed = False

        for board in boards:
            for slot in board["slots"]:
                if slot.used_length + pl <= board_l and piece.width <= slot.height:
                    board["placements"].append(Placement(
                        part_name=piece.name, x=slot.used_length, y=slot.y,
                        width=piece.length, height=piece.width,
                        rotated=False, is_spare=piece.is_spare,
                    ))
                    slot.used_length += pl
                    placed = True
                    break
            if placed:
                break

            slot_y = sum(s.height + kerf for s in board["slots"])
            if slot_y + pw <= board_w:
                new_slot = _BoardSlot(y=slot_y, height=piece.width, used_length=pl)
                board["placements"].append(Placement(
                    part_name=piece.name, x=0, y=slot_y,
                    width=piece.length, height=piece.width,
                    rotated=False, is_spare=piece.is_spare,
                ))
                board["slots"].append(new_slot)
                placed = True
                break

        if not placed:
            new_board()
            board = boards[-1]
            new_slot = _BoardSlot(y=0, height=piece.width, used_length=pl)
            board["placements"].append(Placement(
                part_name=piece.name, x=0, y=0,
                width=piece.length, height=piece.width,
                rotated=False, is_spare=piece.is_spare,
            ))
            board["slots"].append(new_slot)

    results = []
    for board in boards:
        if not board["placements"]:
            continue
        board_area = board_w * board_l
        used_area = sum(p.width * p.height for p in board["placements"])
        waste = max(0, (1 - used_area / board_area) * 100)
        results.append(BoardLayout(
            material=material, thickness=thickness,
            width=board_w, length=board_l,
            placements=board["placements"], waste_percent=round(waste, 1),
        ))
    return results
