import pytest
import numpy as np
from app.analyzer.geometry import compute_dimensions, classify_board_type
from app.models import BoardType


class TestComputeDimensions:
    def test_simple_box(self):
        vertices = np.array([
            [0, 0, 0], [100, 0, 0], [100, 50, 0], [0, 50, 0],
            [0, 0, 19], [100, 0, 19], [100, 50, 19], [0, 50, 19],
        ], dtype=np.float64)
        length, width, thickness = compute_dimensions(vertices)
        assert length == pytest.approx(100.0)
        assert width == pytest.approx(50.0)
        assert thickness == pytest.approx(19.0)

    def test_dimensions_sorted_descending(self):
        vertices = np.array([
            [0, 0, 0], [10, 0, 0], [10, 200, 0], [0, 200, 0],
            [0, 0, 50], [10, 0, 50], [10, 200, 50], [0, 200, 50],
        ], dtype=np.float64)
        length, width, thickness = compute_dimensions(vertices)
        assert length == pytest.approx(200.0)
        assert width == pytest.approx(50.0)
        assert thickness == pytest.approx(10.0)

    def test_offset_box(self):
        vertices = np.array([
            [100, 100, 100], [300, 100, 100], [300, 200, 100], [100, 200, 100],
            [100, 100, 119], [300, 100, 119], [300, 200, 119], [100, 200, 119],
        ], dtype=np.float64)
        length, width, thickness = compute_dimensions(vertices)
        assert length == pytest.approx(200.0)
        assert width == pytest.approx(100.0)
        assert thickness == pytest.approx(19.0)


class TestClassifyBoardType:
    def test_thick_stock(self):
        board_type, notes = classify_board_type(length_in=29.0, width_in=2.5, thickness_in=2.5)
        assert board_type == BoardType.THICK_STOCK
        assert "lamination" in notes.lower()

    def test_sheet_good(self):
        board_type, notes = classify_board_type(length_in=30.0, width_in=24.0, thickness_in=0.75)
        assert board_type == BoardType.SHEET

    def test_solid_lumber_narrow(self):
        board_type, notes = classify_board_type(length_in=30.0, width_in=2.5, thickness_in=0.75)
        assert board_type == BoardType.SOLID
        assert "glue-up" not in notes.lower()

    def test_solid_lumber_wide_glueup(self):
        board_type, notes = classify_board_type(length_in=30.0, width_in=18.0, thickness_in=1.0)
        assert board_type == BoardType.SOLID
        assert "glue-up" in notes.lower()

    def test_solid_narrow_at_boundary(self):
        board_type, notes = classify_board_type(length_in=30.0, width_in=12.0, thickness_in=0.75)
        assert board_type == BoardType.SOLID

    def test_all_solid_override_converts_sheet_to_solid(self):
        board_type, notes = classify_board_type(length_in=30.0, width_in=24.0, thickness_in=0.75, all_solid=True)
        assert board_type == BoardType.SOLID
        assert "glue-up" in notes.lower()

    def test_thin_small_panel_is_solid(self):
        board_type, notes = classify_board_type(length_in=10.0, width_in=14.0, thickness_in=0.25)
        assert board_type == BoardType.SOLID
