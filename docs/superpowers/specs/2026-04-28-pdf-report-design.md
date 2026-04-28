# PDF Project Plan Report — Design Spec

**Date:** 2026-04-28
**Status:** Draft
**Parent:** `docs/superpowers/specs/2026-04-27-3mf-cut-list-generator-design.md`

## Overview

Add a "Download PDF" button that generates a polished project plan report combining the 3D model thumbnail, parts list, shopping list with cut pieces, and cost estimate. The report is suitable for both personal workshop use and sharing with clients/collaborators.

## Goals

- Generate a professional PDF report from the analysis results
- Include a 3D model thumbnail captured from the frontend viewer
- Cover all project data: parts, materials, cuts, costs, supplier links
- Single "Download PDF" button in the results view

## Non-Goals

- Customizable report templates or branding
- Multiple report formats (just PDF)
- Server-side 3D rendering (thumbnail comes from the frontend canvas)

---

## Architecture

### Flow

1. User clicks "Download PDF" in the results view
2. Frontend captures the Three.js canvas as a PNG via `canvas.toDataURL('image/png')`
3. Frontend POSTs to `/api/report` with the session ID, analysis config, and base64-encoded thumbnail
4. Backend runs the same analysis pipeline (or uses cached results)
5. Backend renders an HTML template with Jinja2, embedding the thumbnail and all analysis data
6. WeasyPrint converts the HTML to PDF
7. Backend returns the PDF as `application/pdf`
8. Browser triggers a file download

### Why server-side PDF

- Consistent output across browsers and OS
- Proper file download (not a print dialog)
- Clean separation — the HTML template is the single source of truth for report layout
- WeasyPrint has excellent CSS support including `@page`, headers/footers, page breaks

---

## Report Layout

### Page 1 (and overflow)

```
┌──────────────────────────────────────────┐
│  CUT LIST PROJECT PLAN                   │
│  Date: April 28, 2026                    │
│  File: record-player-cabinet.3mf         │
│  Materials: Red Oak / Baltic Birch Ply   │
├──────────────────────────────────────────┤
│                                          │
│         [3D Model Thumbnail]             │
│                                          │
├──────────────────────────────────────────┤
│  PROJECT SUMMARY                         │
│  14 parts (5 unique) · 6.8 BF solid     │
│  lumber · 2 plywood sheets              │
│  Estimated cost: $XXX.XX                 │
├──────────────────────────────────────────┤
│  PARTS LIST                              │
│  ┌──────┬───┬────────────┬──────┬──────┐ │
│  │ Part │Qty│ Dimensions │ Type │Stock │ │
│  ├──────┼───┼────────────┼──────┼──────┤ │
│  │ ...  │   │            │      │      │ │
│  └──────┴───┴────────────┴──────┴──────┘ │
├──────────────────────────────────────────┤
│  SHOPPING LIST                           │
│                                          │
│  4/4 Red Oak — 1.0 BF                   │
│  Boards min 3.5" wide × 17" long        │
│  Cut: 12"×1" (×4), 16"×3" (×2)         │
│                                          │
│  8/4 Red Oak — 5.8 BF                   │
│  Boards min 2.5" wide × 37" long        │
│  Cut: 36"×2" (×4)                       │
│  ...                                     │
├──────────────────────────────────────────┤
│  COST ESTIMATE                           │
│  ┌──────────┬─────┬───────┬─────────┐   │
│  │ Material │ Qty │ Price │Subtotal │   │
│  ├──────────┼─────┼───────┼─────────┤   │
│  │ ...      │     │       │         │   │
│  ├──────────┼─────┼───────┼─────────┤   │
│  │          │     │ Total │ $XXX.XX │   │
│  └──────────┴─────┴───────┴─────────┘   │
│  Supplier links listed below table       │
├──────────────────────────────────────────┤
│  Generated by Cut List Generator · date  │
└──────────────────────────────────────────┘
```

### Styling

- Clean, minimal design with good typography
- Tables with subtle borders and alternating row shading
- Board type badges (solid/sheet/thick stock) as colored labels
- Thumbnail sized to ~4" wide, centered
- `@page` CSS for margins and footer
- Page breaks before Shopping List section if parts table is long

---

## API

### POST /api/report

**Request body (JSON):**

```json
{
  "session_id": "uuid",
  "solid_species": "Red Oak",
  "sheet_type": "Baltic Birch Ply",
  "all_solid": false,
  "display_units": "in",
  "thumbnail": "data:image/png;base64,iVBOR..."
}
```

The `thumbnail` field is a base64 data URL captured from the Three.js canvas. Optional — if omitted, the report renders without a model image.

**Response:**

- Content-Type: `application/pdf`
- Content-Disposition: `attachment; filename="cut-list-report.pdf"`
- Body: PDF bytes

The endpoint runs the full analysis pipeline (same as `/api/analyze`) to ensure the report data is always fresh, then renders the template and converts to PDF.

---

## Backend Implementation

### Dependencies

Add `weasyprint` to `requirements.txt`. WeasyPrint requires system libraries (`libpango`, `libcairo`) — document in the Dockerfile.

### Files

| File | Responsibility |
|------|---------------|
| `backend/app/report.py` | Report generation: Jinja2 template rendering + WeasyPrint PDF conversion |
| `backend/app/templates/report.html` | Jinja2 HTML template for the report |
| `backend/app/templates/report.css` | Stylesheet for the report (embedded in template or separate) |
| `backend/app/main.py` | New `/api/report` endpoint |
| `backend/app/models.py` | `ReportRequest` Pydantic model |

### Template Data

The template receives:

```python
{
    "date": "April 28, 2026",
    "filename": "record-player-cabinet.3mf",
    "solid_species": "Red Oak",
    "sheet_type": "Baltic Birch Ply",
    "display_units": "in",
    "thumbnail_data_url": "data:image/png;base64,...",  # or None
    "summary": {
        "total_parts": 14,
        "unique_parts": 5,
        "total_bf": 6.8,
        "total_sheets": 2,
        "estimated_cost": 355.45,  # or None
        "has_missing_prices": False,
    },
    "parts": [...],           # same Part objects as AnalyzeResponse
    "shopping_list": [...],   # same ShoppingItem objects
    "cost_estimate": {...},   # same CostEstimate object
}
```

### PDF Generation

```python
from weasyprint import HTML

def generate_report_pdf(template_data: dict) -> bytes:
    html_string = render_template("report.html", **template_data)
    pdf_bytes = HTML(string=html_string).write_pdf()
    return pdf_bytes
```

---

## Frontend Implementation

### Files

| File | Change |
|------|--------|
| `frontend/src/lib/types.ts` | Add `ReportRequest` interface |
| `frontend/src/lib/api.ts` | Add `downloadReport()` function |
| `frontend/src/lib/components/Results.svelte` | Add "Download PDF" button |
| `frontend/src/lib/components/ModelViewer.svelte` | Expose `captureScreenshot()` method |

### Canvas Capture

The `ModelViewer` component needs to expose a way to capture the current canvas as a data URL. Three.js requires `preserveDrawingBuffer: true` on the renderer for `toDataURL()` to work, or we do a render-then-capture in the same frame.

```typescript
// In ModelViewer.svelte — expose a capture function
export function captureScreenshot(): string {
    renderer.render(scene, camera);
    return renderer.domElement.toDataURL('image/png');
}
```

### Download Flow

```typescript
async function downloadPdf() {
    const thumbnail = modelViewer.captureScreenshot();
    const response = await fetch('/api/report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            session_id: uploadResult.session_id,
            solid_species: config.solid_species,
            sheet_type: config.sheet_type,
            all_solid: config.all_solid,
            display_units: config.display_units,
            thumbnail,
        }),
    });
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'cut-list-report.pdf';
    a.click();
    URL.revokeObjectURL(url);
}
```

---

## Docker Changes

WeasyPrint requires system libraries. Add to `backend/Dockerfile`:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 \
    libffi-dev shared-mime-info \
    && rm -rf /var/lib/apt/lists/*
```

---

## Testing

- Unit test: render template with sample data → verify PDF bytes are non-empty and start with `%PDF`
- Unit test: template renders all sections (parts, shopping, cost) with sample data
- Unit test: template handles missing thumbnail gracefully
- Unit test: template handles `has_missing_prices` with partial total
- Integration test: POST to `/api/report` with a valid session → get 200 with PDF content-type
