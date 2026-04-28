import pytest
from app.models import (
    BoardType,
    Part,
    ShoppingItem,
    CostEstimate,
    AnalyzeRequest,
    AnalyzeResponse,
    UploadResponse,
)


def test_part_creation():
    part = Part(
        name="Side Panel",
        quantity=2,
        length_mm=762.0,
        width_mm=304.8,
        thickness_mm=19.05,
        board_type=BoardType.SOLID,
        stock="4/4 Red Oak",
        notes="",
    )
    assert part.name == "Side Panel"
    assert part.quantity == 2
    assert part.board_type == BoardType.SOLID


def test_part_display_dimensions_inches():
    part = Part(
        name="Shelf",
        quantity=1,
        length_mm=863.6,
        width_mm=285.75,
        thickness_mm=19.05,
        board_type=BoardType.SOLID,
        stock="4/4 Red Oak",
        notes="",
    )
    dims = part.display_dimensions("in")
    assert dims == "34.0\" × 11.25\" × 0.75\""


def test_part_display_dimensions_mm():
    part = Part(
        name="Shelf",
        quantity=1,
        length_mm=863.6,
        width_mm=285.75,
        thickness_mm=19.05,
        board_type=BoardType.SOLID,
        stock="4/4 Red Oak",
        notes="",
    )
    dims = part.display_dimensions("mm")
    assert dims == "863.6 × 285.75 × 19.05 mm"


def test_shopping_item_subtotal():
    item = ShoppingItem(
        material="4/4 Red Oak",
        thickness="4/4",
        quantity=18.5,
        unit="BF",
        unit_price=8.50,
    )
    assert item.subtotal == pytest.approx(157.25)


def test_shopping_item_subtotal_none_when_no_price():
    item = ShoppingItem(
        material="4/4 Red Oak",
        thickness="4/4",
        quantity=18.5,
        unit="BF",
        unit_price=None,
    )
    assert item.subtotal is None


def test_cost_estimate_total():
    items = [
        ShoppingItem(material="4/4 Oak", thickness="4/4", quantity=18.5, unit="BF", unit_price=8.50),
        ShoppingItem(material="3/4 Ply", thickness="3/4\"", quantity=2, unit="sheets", unit_price=65.0),
    ]
    estimate = CostEstimate(items=items)
    assert estimate.total == pytest.approx(287.25)


def test_cost_estimate_partial_total_when_some_prices_missing():
    items = [
        ShoppingItem(material="4/4 Oak", thickness="4/4", quantity=18.5, unit="BF", unit_price=8.50),
        ShoppingItem(material="3/4 Ply", thickness="3/4\"", quantity=2, unit="sheets", unit_price=None),
    ]
    estimate = CostEstimate(items=items)
    # Shows partial total from available prices
    assert estimate.total == pytest.approx(157.25)
    assert estimate.has_missing_prices is True


def test_cost_estimate_total_none_when_all_prices_missing():
    items = [
        ShoppingItem(material="4/4 Oak", thickness="4/4", quantity=18.5, unit="BF", unit_price=None),
        ShoppingItem(material="3/4 Ply", thickness="3/4\"", quantity=2, unit="sheets", unit_price=None),
    ]
    estimate = CostEstimate(items=items)
    assert estimate.total is None
    assert estimate.has_missing_prices is True


def test_cost_estimate_no_missing_prices():
    items = [
        ShoppingItem(material="4/4 Oak", thickness="4/4", quantity=18.5, unit="BF", unit_price=8.50),
    ]
    estimate = CostEstimate(items=items)
    assert estimate.has_missing_prices is False


def test_analyze_request_defaults():
    req = AnalyzeRequest(session_id="abc-123", solid_species="Red Oak", sheet_type="Baltic Birch")
    assert req.all_solid is False
    assert req.display_units == "in"


def test_board_type_enum():
    assert BoardType.SOLID.value == "solid"
    assert BoardType.SHEET.value == "sheet"
    assert BoardType.THICK_STOCK.value == "thick_stock"
