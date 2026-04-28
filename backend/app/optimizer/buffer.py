"""Mistake buffer logic for cut optimization."""

from app.models import Part


class SparePart(Part):
    """A spare part added by the mistake buffer."""
    is_spare: bool = True


def apply_spare_parts(parts: list[Part], spares_per_unique: int = 1) -> list[Part]:
    """Add spare copies of each unique part. Returns original parts + spares."""
    result = list(parts)
    for part in parts:
        spare = SparePart(
            name=f"Spare {part.name}",
            quantity=spares_per_unique,
            length_mm=part.length_mm,
            width_mm=part.width_mm,
            thickness_mm=part.thickness_mm,
            board_type=part.board_type,
            stock=part.stock,
            notes="(mistake buffer)",
            is_spare=True,
        )
        result.append(spare)
    return result


def apply_percentage_buffer(percentage: float) -> float:
    """Return an area multiplier for percentage-based buffer. 15% → 1.15."""
    return 1.0 + (percentage / 100.0)
