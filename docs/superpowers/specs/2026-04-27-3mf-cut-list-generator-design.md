# 3MF Cut List Generator — Design Spec

**Date:** 2026-04-27
**Status:** Draft

## Overview

A web application that takes a 3MF furniture model, analyzes its geometry, and produces a cut list, shopping list, and cost estimate. Users upload a file, select materials, and get a complete bill of materials priced against real supplier catalogs.

## Goals

- Accept 3MF files (units built in) and extract individual part bodies
- Classify parts as solid lumber or sheet goods based on geometry
- Map parts to standard lumber sizes with milling allowances
- Price materials against Woodworkers Source catalog (modular for future suppliers)
- Present results as a parts list, shopping list, and cost estimate
- Display the uploaded 3D model in-browser for visual reference

## Non-Goals (v1)

- User authentication (session-isolated, no login)
- Per-part material tagging (global material selection only)
- Single-body decomposition (assumes separate bodies per part)
- Cut optimization / nesting (naive area calculation for sheets)
- Actual ordering / cart integration (price lookup only)
- Organic/sculptural geometry (furniture-style flat boards only)

---

## Architecture

### Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | SvelteKit | Lightweight, user familiarity, sufficient for file-upload-and-results workflow |
| Backend | Python FastAPI | Best ecosystem for 3MF parsing, geometry math, web scraping |
| 3D Viewer | Three.js + 3MFLoader | Renders 3MF directly in browser, no backend conversion |
| Session Storage | Server-side temp dirs (UUID) | No database needed for v1 |
| Price Cache | JSON file | Cached supplier catalog with 24h TTL |

### Service Boundary

Two services communicating over REST:

- **SvelteKit frontend** (port 5173 dev / served statically in prod) — handles upload UI, material selection, results display, 3D viewer
- **FastAPI backend** (port 8000) — 3MF parsing, geometry analysis, material mapping, supplier pricing

### API Surface

```
POST /api/upload
  Body: multipart/form-data (3mf file)
  Returns: { session_id, file_url, parts_preview[] }

POST /api/analyze
  Body: { session_id, solid_species, sheet_type, all_solid: bool, display_units: "in"|"mm" }
  Returns: { parts_list[], shopping_list[], cost_estimate }

GET /api/files/{session_id}/{filename}
  Returns: raw 3MF file (for Three.js viewer)

GET /api/species
  Returns: available lumber species from supplier catalog

GET /api/sheet-types
  Returns: available sheet good types from supplier catalog
```

### Session Isolation

Each upload creates a UUID-based temp directory on the server. The session ID is returned to the client and used for all subsequent requests. No cookies, no auth — just the session ID in the request body/URL.

Sessions auto-expire after a configurable TTL (default: 2 hours). A background task or startup sweep cleans expired sessions.

---

## 3MF Parsing

### File Structure

3MF is a ZIP archive containing XML. The primary file is `3D/3dmodel.model`:

```xml
<model unit="millimeter">
  <resources>
    <object id="1" name="Side Panel">
      <mesh>
        <vertices>
          <vertex x="0" y="0" z="0" />
          ...
        </vertices>
        <triangles>
          <triangle v1="0" v2="1" v3="2" />
          ...
        </triangles>
      </mesh>
    </object>
    <object id="2" name="Shelf">...</object>
  </resources>
  <build>
    <item objectid="1" transform="..." />
    <item objectid="2" transform="..." />
  </build>
</model>
```

### Parsing Pipeline

1. **Extract** — unzip, parse XML with `xml.etree.ElementTree`
2. **Read units** — pull `unit` attribute from `<model>` element (millimeter, centimeter, inch, foot, meter, micrometer)
3. **Enumerate bodies** — iterate `<object>` elements, extract vertex arrays as numpy arrays
4. **Apply transforms** — apply `<build>` item transform matrices to vertex coordinates
5. **Name parts** — use `name` attribute from `<object>` if present, else generate "Part 1", "Part 2", etc.
6. **Detect duplicates** — identify parts with identical geometry (same mesh within tolerance) and group them with a quantity count

---

## Geometry Analysis

### Bounding Box Computation

For each body, compute the axis-aligned bounding box (AABB) from the transformed vertex array. Extract the three dimensions and sort them: Length >= Width >= Thickness.

Internally, all dimensions are stored in the 3MF's native units and converted to inches for lumber matching. The user's display unit preference controls presentation only.

### Board Type Inference

Rules are evaluated top-to-bottom; first match wins:

| Priority | Condition | Classification | Example |
|----------|-----------|---------------|---------|
| 1 | Thickness > 1.5" | **Thick stock** (may need lamination) | Table leg: 2.5" x 2.5" x 29" |
| 2 | Thickness <= 3/4" AND face area > 1 sq ft AND width > 12" | **Sheet good** | Cabinet side: 3/4" x 24" x 30" |
| 3 | Width > 12" | **Solid lumber** (glue-up needed) | Wide panel: 1" x 18" x 30" |
| 4 | Otherwise | **Solid lumber** | Face frame rail: 3/4" x 2.5" x 30" |

These are heuristics. The "all solid" toggle overrides sheet good classification, mapping those parts to solid lumber with glue-up notes instead. Per-part overrides are deferred to a future version.

---

## Material Mapping

### User Configuration (Global)

Two material selections plus controls:

- **Solid lumber species** — dropdown populated from supplier catalog (e.g., Red Oak, Walnut, Maple, Poplar, Cherry)
- **Sheet good type** — dropdown populated from supplier catalog (e.g., Red Oak veneer ply, Baltic Birch, MDF, Melamine)
- **"All solid lumber" toggle** — when on, all parts classified as sheet goods are remapped to solid lumber with glue-up notes
- **Display units toggle** — inches or millimeters (presentation only; conversion happens internally regardless)

### Mapping Algorithm

**For each part:**

1. Snap thickness to nearest standard size (within tolerance, e.g., 0.74" -> 3/4")
2. Check "all solid" toggle — if on, override sheet good classification

**Solid lumber path:**

3. Match snapped thickness to rough lumber size: 3/4" -> 4/4, 1" -> 5/4, 1-1/4" -> 6/4, 1-3/4" -> 8/4
4. Add milling allowance: +1/4" thickness, +1/2" width, +1" length
5. Calculate board feet: (thickness_in x width_in x length_in) / 144
6. If width > 12": flag as "glue-up needed", calculate number of boards (assuming ~6" average board width)

**Sheet good path:**

3. Match thickness to available sheet thickness (1/4", 1/2", 3/4")
4. Add kerf allowance: +1/8" per cut edge
5. Tally total area per thickness/type
6. Calculate sheets needed: total_area / sheet_area (48" x 96"), rounded up

### Output: Parts List

Each entry contains:

- Part name (from 3MF object name or generated)
- Quantity (grouped identical parts)
- Dimensions (L x W x T in display units)
- Classification (solid / sheet / thick stock)
- Stock recommendation (e.g., "4/4 Red Oak")
- Notes (glue-up needed, lamination needed, etc.)

### Output: Shopping List

Aggregated by material + thickness:

- Material description (e.g., "4/4 Red Oak")
- Total quantity (board feet or sheet count)
- Unit price (from supplier)
- Subtotal
- Grand total across all materials

---

## Supplier Module

### Interface

```python
class SupplierBase(ABC):
    """Abstract interface for lumber suppliers."""

    @abstractmethod
    def get_catalog(self) -> list[Product]:
        """Available lumber and sheet goods with dimensions and prices."""

    @abstractmethod
    def get_price(self, species: str, thickness: str, board_feet: float) -> Money:
        """Price for a solid lumber request."""

    @abstractmethod
    def get_sheet_price(self, product_type: str, thickness: str) -> Money:
        """Price for a sheet good."""

    @abstractmethod
    def get_species_list(self) -> list[str]:
        """Available lumber species."""

    @abstractmethod
    def get_sheet_types(self) -> list[str]:
        """Available sheet good types."""
```

### Woodworkers Source Implementation

- **Data source:** Scrape product pages from woodworkerssource.com
- **Caching:** Store catalog locally as JSON with 24-hour TTL
- **Rate limiting:** Respectful request throttling (1 req/sec max during scraping)
- **Mapping:** Map their product categories to the standard types used by the material mapper
- **Fallback:** If scraping fails or cache is stale, return prices as unavailable — the parts list and shopping list still render, just without cost data

### Future Suppliers

New suppliers implement `SupplierBase` and register in a supplier registry. The frontend can offer a supplier selector once multiple are available. Some suppliers may offer APIs instead of requiring scraping.

---

## Frontend

### Technology

- SvelteKit with TypeScript
- Three.js with 3MFLoader for model display
- Tailwind CSS for styling

### Three-Step Workflow

**Step 1: Upload**

- Drag-and-drop zone or click-to-browse for .3mf files
- Client-side validation: file extension check, reasonable size limit (50MB)
- On successful upload: display file name/size, load 3D viewer, show configure step

**Step 2: Configure**

- Solid lumber species dropdown (populated from `/api/species`)
- Sheet good type dropdown (populated from `/api/sheet-types`)
- "All solid lumber" toggle
- Display units toggle (in / mm)
- "Analyze" button triggers `/api/analyze`

**Step 3: Results**

Three tabs:

- **Parts List** — table with part name, qty, dimensions, type, stock, notes
- **Shopping List** — aggregated materials with quantities
- **Cost Estimate** — pricing breakdown with subtotals and total

Action buttons: CSV export, print-friendly view.

### 3D Model Viewer

- Renders after upload, persists through configure and results steps
- Three.js with OrbitControls (rotate, zoom, pan)
- Loads the 3MF file directly via the 3MFLoader addon
- Positioned alongside the main content (side panel or collapsible)
- Future: highlight parts on hover/click to link viewer to parts list

### Loading States

Analysis takes a few seconds. Show progressive status:
"Parsing model..." → "Analyzing geometry..." → "Looking up prices..."

### Error Handling

- Invalid file format → clear error message with retry option
- No bodies found → "Model appears empty or contains no mesh data"
- Pricing unavailable → show parts list and shopping list without costs, note that supplier pricing is temporarily unavailable
- Analysis failure → descriptive error with option to re-upload

---

## Project Structure

```
mayor/
├── frontend/                 # SvelteKit app
│   ├── src/
│   │   ├── routes/
│   │   │   └── +page.svelte  # Main (and only) page
│   │   ├── lib/
│   │   │   ├── components/   # Upload, Configure, Results, ModelViewer
│   │   │   ├── api.ts        # Backend API client
│   │   │   └── types.ts      # Shared TypeScript types
│   │   └── app.html
│   ├── static/
│   ├── package.json
│   └── svelte.config.js
│
├── backend/                  # Python FastAPI app
│   ├── app/
│   │   ├── main.py           # FastAPI app, routes
│   │   ├── parser/
│   │   │   └── threemf.py    # 3MF extraction and parsing
│   │   ├── analyzer/
│   │   │   └── geometry.py   # Bounding boxes, board type inference
│   │   ├── mapper/
│   │   │   └── materials.py  # Standard sizes, milling allowances, mapping
│   │   ├── suppliers/
│   │   │   ├── base.py       # SupplierBase ABC
│   │   │   ├── registry.py   # Supplier registry
│   │   │   └── woodworkers_source.py
│   │   ├── models.py         # Pydantic models (Part, ShoppingItem, CostEstimate)
│   │   └── session.py        # Session management, temp dir lifecycle
│   ├── tests/
│   ├── requirements.txt
│   └── pyproject.toml
│
├── docker-compose.yml        # Both services
├── .gitignore
└── docs/
```

---

## Deployment

Docker Compose with two services:

- `frontend` — Node container running SvelteKit (or static build served by nginx)
- `backend` — Python container running FastAPI with uvicorn

For development: run both services locally with hot reload. SvelteKit proxies API requests to FastAPI.

---

## Future Enhancements (Ordered by Value)

1. **Per-part material tagging** — override system inference per part
2. **Cut optimization / nesting** — bin-packing algorithm to minimize waste on sheets and boards
3. **User accounts + auth** — save projects, revisit past analyses
4. **Additional suppliers** — more pricing sources, supplier comparison
5. **Part highlighting** — click parts list row to highlight body in 3D viewer
6. **Actual ordering** — generate cart / place order with supplier
7. **Single-body decomposition** — split monolithic models into board components
8. **Organic geometry** — slice non-rectangular shapes into glueable slabs
9. **PDF export** — formatted cut list and shopping list for the shop
10. **Share links** — shareable read-only view of analysis results
