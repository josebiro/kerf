import pytest
from app.report import generate_report_pdf, _build_summary
from app.models import (
    AnalyzeResponse, Part, ShoppingItem, CostEstimate, BoardType,
)


def _sample_response() -> AnalyzeResponse:
    parts = [
        Part(name="Side Panel", quantity=2, length_mm=762.0, width_mm=304.8,
             thickness_mm=19.05, board_type=BoardType.SOLID, stock="4/4 Red Oak", notes=""),
        Part(name="Back", quantity=1, length_mm=762.0, width_mm=609.6,
             thickness_mm=19.05, board_type=BoardType.SHEET, stock='3/4" Baltic Birch', notes=""),
    ]
    items = [
        ShoppingItem(material="4/4 Red Oak", thickness="4/4", quantity=5.0,
                     unit="BF", unit_price=4.99, description='Boards min 3.5" wide',
                     cut_pieces=['30" × 12" (×2)'], url="https://example.com/red-oak"),
        ShoppingItem(material='3/4" Baltic Birch', thickness='3/4"', quantity=1.0,
                     unit="sheets", unit_price=58.00, description="1 × 4' × 8' sheet",
                     cut_pieces=['30" × 24"'], url=None),
    ]
    return AnalyzeResponse(
        parts=parts,
        shopping_list=items,
        cost_estimate=CostEstimate(items=items),
        display_units="in",
    )


class TestBuildSummary:
    def test_counts_total_parts(self):
        resp = _sample_response()
        summary = _build_summary(resp)
        assert summary["total_parts"] == 3
        assert summary["unique_parts"] == 2

    def test_sums_board_feet(self):
        resp = _sample_response()
        summary = _build_summary(resp)
        assert summary["total_bf"] == pytest.approx(5.0)

    def test_counts_sheets(self):
        resp = _sample_response()
        summary = _build_summary(resp)
        assert summary["total_sheets"] == 1

    def test_estimated_cost(self):
        resp = _sample_response()
        summary = _build_summary(resp)
        assert summary["estimated_cost"] == pytest.approx(82.95)


class TestGenerateReportPdf:
    def test_returns_valid_pdf_bytes(self):
        resp = _sample_response()
        pdf = generate_report_pdf(resp, "test.3mf", "Red Oak", "Baltic Birch")
        assert isinstance(pdf, bytes)
        assert pdf[:5] == b"%PDF-"
        assert len(pdf) > 1000

    def test_works_without_thumbnail(self):
        resp = _sample_response()
        pdf = generate_report_pdf(resp, "test.3mf", "Red Oak", "Baltic Birch", thumbnail_data_url=None)
        assert pdf[:5] == b"%PDF-"

    def test_works_with_thumbnail(self):
        tiny_png = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        resp = _sample_response()
        pdf = generate_report_pdf(resp, "test.3mf", "Red Oak", "Baltic Birch", thumbnail_data_url=tiny_png)
        assert pdf[:5] == b"%PDF-"

    def test_handles_missing_prices(self):
        items = [
            ShoppingItem(material="4/4 Oak", thickness="4/4", quantity=5.0,
                         unit="BF", unit_price=None, description="test", cut_pieces=[]),
        ]
        resp = AnalyzeResponse(
            parts=[Part(name="P1", quantity=1, length_mm=100, width_mm=50,
                        thickness_mm=19, board_type=BoardType.SOLID, stock="4/4 Oak", notes="")],
            shopping_list=items,
            cost_estimate=CostEstimate(items=items),
            display_units="in",
        )
        pdf = generate_report_pdf(resp, "test.3mf", "Oak", "Ply")
        assert pdf[:5] == b"%PDF-"

    def test_handles_mm_display_units(self):
        resp = _sample_response()
        resp = resp.model_copy(update={"display_units": "mm"})
        pdf = generate_report_pdf(resp, "test.3mf", "Red Oak", "Baltic Birch")
        assert pdf[:5] == b"%PDF-"
