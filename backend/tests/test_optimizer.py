import pytest
from app.optimizer.optimize import run_optimization
from app.models import Part, ShoppingItem, BoardType, BufferConfig, BoardSizeConfig


def _sample_parts():
    return [
        Part(name="Shelf", quantity=3, length_mm=406.4, width_mm=381.0,
             thickness_mm=12.7, board_type=BoardType.SHEET,
             stock='1/2" Baltic Birch', notes=""),
        Part(name="Leg", quantity=4, length_mm=914.4, width_mm=50.8,
             thickness_mm=50.8, board_type=BoardType.THICK_STOCK,
             stock="8/4 Red Oak", notes="May need lamination"),
        Part(name="Rail", quantity=2, length_mm=406.4, width_mm=76.2,
             thickness_mm=12.7, board_type=BoardType.SOLID,
             stock="4/4 Red Oak", notes=""),
    ]

def _sample_shopping():
    return [
        ShoppingItem(material='1/2" Baltic Birch', thickness='1/2"', quantity=1.0, unit="sheets"),
        ShoppingItem(material="8/4 Red Oak", thickness="8/4", quantity=5.8, unit="BF"),
        ShoppingItem(material="4/4 Red Oak", thickness="4/4", quantity=1.0, unit="BF"),
    ]


class TestRunOptimization:
    def test_returns_sheets_and_boards(self):
        result = run_optimization(
            parts=_sample_parts(), shopping_list=_sample_shopping(),
            solid_species="Red Oak", sheet_type="Baltic Birch",
        )
        assert len(result.sheets) >= 1
        assert len(result.boards) >= 1

    def test_spare_parts_mode(self):
        config = BufferConfig(lumber_mode="extra_parts", lumber_value=1)
        result = run_optimization(
            parts=_sample_parts(), shopping_list=_sample_shopping(),
            solid_species="Red Oak", sheet_type="Baltic Birch",
            buffer_config=config,
        )
        all_placements = [p for b in result.boards for p in b.placements]
        spares = [p for p in all_placements if p.is_spare]
        assert len(spares) >= 1

    def test_summary_populated(self):
        result = run_optimization(
            parts=_sample_parts(), shopping_list=_sample_shopping(),
            solid_species="Red Oak", sheet_type="Baltic Birch",
        )
        assert result.summary.total_sheets >= 1
        assert result.summary.total_boards >= 1
        assert result.summary.avg_waste_percent >= 0

    def test_custom_board_sizes(self):
        sizes = {"8/4": BoardSizeConfig(width=8.0, length=72.0)}
        result = run_optimization(
            parts=_sample_parts(), shopping_list=_sample_shopping(),
            solid_species="Red Oak", sheet_type="Baltic Birch",
            board_sizes=sizes,
        )
        boards_8_4 = [b for b in result.boards if b.thickness == "8/4"]
        if boards_8_4:
            assert boards_8_4[0].width == 8.0
            assert boards_8_4[0].length == 72.0

    def test_updated_shopping_list_returned(self):
        result = run_optimization(
            parts=_sample_parts(), shopping_list=_sample_shopping(),
            solid_species="Red Oak", sheet_type="Baltic Birch",
        )
        assert len(result.updated_shopping_list) == len(_sample_shopping())
