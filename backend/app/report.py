"""PDF report generation using Jinja2 templates and WeasyPrint."""

from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from app.models import AnalyzeResponse

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)), autoescape=True)


def _build_summary(response: AnalyzeResponse) -> dict:
    """Build the summary stats dict for the report template."""
    total_parts = sum(p.quantity for p in response.parts)
    unique_parts = len(response.parts)
    total_bf = 0.0
    total_sheets = 0
    for item in response.shopping_list:
        if item.unit == "BF":
            total_bf += item.quantity
        elif item.unit == "sheets":
            total_sheets += int(item.quantity)
    return {
        "total_parts": total_parts,
        "unique_parts": unique_parts,
        "total_bf": total_bf,
        "total_sheets": total_sheets,
        "estimated_cost": response.cost_estimate.total,
        "has_missing_prices": response.cost_estimate.has_missing_prices,
    }


def generate_report_pdf(
    response: AnalyzeResponse,
    filename: str,
    solid_species: str,
    sheet_type: str,
    thumbnail_data_url: str | None = None,
) -> bytes:
    """Render the report template and convert to PDF bytes."""
    template = _env.get_template("report.html")
    html_string = template.render(
        date=date.today().strftime("%B %d, %Y"),
        filename=filename,
        solid_species=solid_species,
        sheet_type=sheet_type,
        display_units=response.display_units,
        thumbnail_data_url=thumbnail_data_url,
        summary=_build_summary(response),
        parts=response.parts,
        shopping_list=response.shopping_list,
        cost_estimate=response.cost_estimate,
    )
    return HTML(string=html_string).write_pdf()
