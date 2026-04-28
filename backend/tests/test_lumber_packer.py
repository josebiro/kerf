import pytest
from app.optimizer.lumber_packer import pack_lumber, LumberPiece


class TestPackLumber:
    def test_single_part_one_board(self):
        pieces = [LumberPiece("Leg", 36.0, 2.0, False)]
        boards = pack_lumber(pieces, board_w=6.0, board_l=96.0, kerf=0.125)
        assert len(boards) == 1
        assert len(boards[0].placements) == 1

    def test_multiple_parts_side_by_side(self):
        pieces = [
            LumberPiece("Leg A", 36.0, 2.0, False),
            LumberPiece("Leg B", 36.0, 2.0, False),
        ]
        boards = pack_lumber(pieces, board_w=6.0, board_l=96.0, kerf=0.125)
        assert len(boards) == 1

    def test_parts_along_length(self):
        pieces = [
            LumberPiece("A", 50.0, 5.0, False),
            LumberPiece("B", 40.0, 5.0, False),
        ]
        boards = pack_lumber(pieces, board_w=6.0, board_l=96.0, kerf=0.125)
        assert len(boards) == 1

    def test_overflow_creates_new_board(self):
        pieces = [
            LumberPiece("A", 50.0, 5.0, False),
            LumberPiece("B", 50.0, 5.0, False),
        ]
        boards = pack_lumber(pieces, board_w=6.0, board_l=96.0, kerf=0.125)
        assert len(boards) == 2

    def test_waste_percent_calculated(self):
        pieces = [LumberPiece("A", 36.0, 2.0, False)]
        boards = pack_lumber(pieces, board_w=6.0, board_l=96.0, kerf=0.125)
        assert boards[0].waste_percent > 50

    def test_spare_flag_preserved(self):
        pieces = [
            LumberPiece("Leg", 36.0, 2.0, False),
            LumberPiece("Spare Leg", 36.0, 2.0, True),
        ]
        boards = pack_lumber(pieces, board_w=6.0, board_l=96.0, kerf=0.125)
        all_placements = [p for b in boards for p in b.placements]
        spares = [p for p in all_placements if p.is_spare]
        assert len(spares) == 1

    def test_empty_input_returns_empty(self):
        boards = pack_lumber([], board_w=6.0, board_l=96.0, kerf=0.125)
        assert boards == []
