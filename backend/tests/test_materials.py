import pytest
from app.mapper.materials import (
    snap_thickness_to_standard,
    rough_thickness_for,
    add_milling_allowance,
    calculate_board_feet,
    calculate_sheets_needed,
    map_part_to_stock,
    aggregate_shopping_list,
)
from app.models import BoardType, Part, ShoppingItem


class TestSnapThickness:
    def test_exact_three_quarter(self):
        assert snap_thickness_to_standard(0.75) == 0.75
    def test_close_to_three_quarter(self):
        assert snap_thickness_to_standard(0.74) == 0.75
    def test_close_to_half(self):
        assert snap_thickness_to_standard(0.48) == 0.5
    def test_close_to_quarter(self):
        assert snap_thickness_to_standard(0.26) == 0.25
    def test_one_inch(self):
        assert snap_thickness_to_standard(0.98) == 1.0
    def test_no_match_returns_input(self):
        assert snap_thickness_to_standard(0.6) == 0.6


class TestRoughThickness:
    def test_three_quarter_is_four_quarter(self):
        assert rough_thickness_for(0.75) == "4/4"
    def test_one_inch_is_five_quarter(self):
        assert rough_thickness_for(1.0) == "5/4"
    def test_one_and_quarter_is_six_quarter(self):
        assert rough_thickness_for(1.25) == "6/4"
    def test_one_and_three_quarter_is_eight_quarter(self):
        assert rough_thickness_for(1.75) == "8/4"
    def test_half_inch_is_four_quarter(self):
        assert rough_thickness_for(0.5) == "4/4"
    def test_nonstandard_returns_next_up(self):
        assert rough_thickness_for(1.5) == "8/4"


class TestMillingAllowance:
    def test_adds_allowance(self):
        l, w, t = add_milling_allowance(30.0, 5.0, 0.75)
        assert l == pytest.approx(31.0)
        assert w == pytest.approx(5.5)
        assert t == pytest.approx(1.0)


class TestBoardFeet:
    def test_one_board_foot(self):
        assert calculate_board_feet(1.0, 12.0, 12.0) == pytest.approx(1.0)
    def test_typical_board(self):
        assert calculate_board_feet(1.0, 6.0, 96.0) == pytest.approx(4.0)


class TestSheetsNeeded:
    def test_single_small_part(self):
        assert calculate_sheets_needed([(24.0, 30.0)]) == 1
    def test_multiple_parts_fit_one_sheet(self):
        assert calculate_sheets_needed([(24.0, 30.0), (24.0, 30.0)]) == 1
    def test_needs_two_sheets(self):
        parts = [(48.0, 48.0), (48.0, 48.0), (48.0, 48.0)]
        assert calculate_sheets_needed(parts) == 2


class TestMapPartToStock:
    def test_solid_lumber_part(self):
        part = Part(name="Rail", quantity=1, length_mm=762.0, width_mm=63.5,
                    thickness_mm=19.05, board_type=BoardType.SOLID, stock="", notes="")
        result = map_part_to_stock(part, species="Red Oak")
        assert result.stock == "4/4 Red Oak"
        assert result.board_type == BoardType.SOLID

    def test_sheet_good_part(self):
        part = Part(name="Panel", quantity=1, length_mm=762.0, width_mm=609.6,
                    thickness_mm=19.05, board_type=BoardType.SHEET, stock="", notes="")
        result = map_part_to_stock(part, species="Red Oak", sheet_type="Baltic Birch")
        assert result.stock == '3/4" Baltic Birch'

    def test_thick_stock_part(self):
        part = Part(name="Leg", quantity=1, length_mm=736.6, width_mm=63.5,
                    thickness_mm=63.5, board_type=BoardType.THICK_STOCK, stock="",
                    notes="May need lamination")
        result = map_part_to_stock(part, species="Red Oak")
        assert "8/4" in result.stock
        assert "lamination" in result.notes.lower()


class TestAggregateShoppingList:
    def test_aggregates_by_stock(self):
        parts = [
            Part(name="Rail", quantity=2, length_mm=762.0, width_mm=63.5,
                 thickness_mm=19.05, board_type=BoardType.SOLID, stock="4/4 Red Oak", notes=""),
            Part(name="Stile", quantity=2, length_mm=762.0, width_mm=50.8,
                 thickness_mm=19.05, board_type=BoardType.SOLID, stock="4/4 Red Oak", notes=""),
        ]
        items = aggregate_shopping_list(parts)
        solid_items = [i for i in items if i.material == "4/4 Red Oak"]
        assert len(solid_items) == 1
        assert solid_items[0].unit == "BF"
        assert solid_items[0].quantity > 0

    def test_separates_solid_and_sheet(self):
        parts = [
            Part(name="Rail", quantity=1, length_mm=762.0, width_mm=63.5,
                 thickness_mm=19.05, board_type=BoardType.SOLID, stock="4/4 Red Oak", notes=""),
            Part(name="Panel", quantity=1, length_mm=762.0, width_mm=609.6,
                 thickness_mm=19.05, board_type=BoardType.SHEET, stock='3/4" Baltic Birch', notes=""),
        ]
        items = aggregate_shopping_list(parts)
        assert len(items) == 2
        materials = {i.material for i in items}
        assert "4/4 Red Oak" in materials
        assert '3/4" Baltic Birch' in materials
