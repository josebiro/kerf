import pytest
from app.optimizer.buffer import apply_spare_parts, apply_percentage_buffer
from app.models import Part, BoardType


def _make_part(name, qty, board_type="solid"):
    return Part(name=name, quantity=qty, length_mm=762.0, width_mm=63.5,
                thickness_mm=19.05, board_type=BoardType(board_type), stock="4/4 Red Oak", notes="")


class TestApplySpareParts:
    def test_adds_one_spare_per_unique(self):
        parts = [_make_part("Rail", 2), _make_part("Stile", 3)]
        result = apply_spare_parts(parts, spares_per_unique=1)
        spares = [p for p in result if getattr(p, "is_spare", False)]
        assert len(spares) == 2
        assert all(p.quantity == 1 for p in spares)

    def test_adds_multiple_spares(self):
        parts = [_make_part("Rail", 2)]
        result = apply_spare_parts(parts, spares_per_unique=2)
        spares = [p for p in result if getattr(p, "is_spare", False)]
        assert len(spares) == 1
        assert spares[0].quantity == 2

    def test_preserves_original_parts(self):
        parts = [_make_part("Rail", 2)]
        result = apply_spare_parts(parts, spares_per_unique=1)
        originals = [p for p in result if not getattr(p, "is_spare", False)]
        assert len(originals) == 1
        assert originals[0].quantity == 2


class TestApplyPercentageBuffer:
    def test_returns_multiplier(self):
        assert apply_percentage_buffer(15.0) == pytest.approx(1.15)

    def test_zero_percent(self):
        assert apply_percentage_buffer(0.0) == pytest.approx(1.0)
