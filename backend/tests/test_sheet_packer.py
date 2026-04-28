import pytest
from app.optimizer.sheet_packer import pack_sheets, PackingPiece


class TestPackSheets:
    def test_single_small_part_fits_one_sheet(self):
        pieces = [PackingPiece("Part A", 16.0, 15.0, False)]
        sheets = pack_sheets(pieces, sheet_w=48.0, sheet_l=96.0, kerf=0.125)
        assert len(sheets) == 1
        assert len(sheets[0].placements) == 1

    def test_multiple_parts_pack_efficiently(self):
        pieces = [
            PackingPiece("A", 16.0, 15.0, False),
            PackingPiece("B", 16.0, 15.0, False),
            PackingPiece("C", 16.0, 15.0, False),
        ]
        sheets = pack_sheets(pieces, sheet_w=48.0, sheet_l=96.0, kerf=0.125)
        assert len(sheets) == 1

    def test_overflow_creates_new_sheet(self):
        pieces = [PackingPiece(f"P{i}", 25.0, 25.0, False) for i in range(8)]
        sheets = pack_sheets(pieces, sheet_w=48.0, sheet_l=96.0, kerf=0.125)
        assert len(sheets) >= 2

    def test_placements_have_coordinates(self):
        pieces = [PackingPiece("A", 16.0, 15.0, False)]
        sheets = pack_sheets(pieces, sheet_w=48.0, sheet_l=96.0, kerf=0.125)
        p = sheets[0].placements[0]
        assert p.x >= 0
        assert p.y >= 0
        assert p.width == pytest.approx(16.0)
        assert p.height == pytest.approx(15.0)

    def test_kerf_applied_between_parts(self):
        pieces = [
            PackingPiece("A", 23.0, 15.0, False),
            PackingPiece("B", 23.0, 15.0, False),
        ]
        sheets = pack_sheets(pieces, sheet_w=48.0, sheet_l=96.0, kerf=0.125)
        p1, p2 = sheets[0].placements[0], sheets[0].placements[1]
        if p1.y == p2.y:
            assert p2.x >= p1.x + p1.width + 0.125

    def test_waste_percent_calculated(self):
        pieces = [PackingPiece("A", 24.0, 48.0, False)]
        sheets = pack_sheets(pieces, sheet_w=48.0, sheet_l=96.0, kerf=0.125)
        assert sheets[0].waste_percent > 50

    def test_spare_flag_preserved(self):
        pieces = [
            PackingPiece("A", 16.0, 15.0, False),
            PackingPiece("Spare A", 16.0, 15.0, True),
        ]
        sheets = pack_sheets(pieces, sheet_w=48.0, sheet_l=96.0, kerf=0.125)
        spares = [p for p in sheets[0].placements if p.is_spare]
        assert len(spares) == 1

    def test_empty_input_returns_empty(self):
        sheets = pack_sheets([], sheet_w=48.0, sheet_l=96.0, kerf=0.125)
        assert sheets == []
