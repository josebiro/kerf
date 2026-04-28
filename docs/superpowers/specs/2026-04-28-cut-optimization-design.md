# Cut Optimization — Design Spec

**Date:** 2026-04-28
**Status:** Draft

## Overview

Add a cut optimization engine that lays out parts on boards and sheets to minimize waste, with interactive diagrams and a configurable "mistake buffer." Users see a visual cut layout, can drag parts between boards, rotate parts, and edit board dimensions. The shopping list updates to reflect the optimized material count.

## Goals

- Pack parts onto standard lumber boards and plywood sheets to minimize waste
- Show interactive cut layout diagrams with parts drawn to scale
- Configurable mistake buffer: % waste for sheets (default 15%), +N spare parts for lumber (default +1 per unique part)
- User can drag parts between boards, rotate parts 90° (sheets), and edit board dimensions
- Waste recalculates live on any change
- Include cut layout in PDF report
- Update shopping list to reflect optimized board/sheet count

## Non-Goals

- Grain direction matching (future enhancement)
- Offcut tracking across projects ("I have leftover plywood from last project")
- Multi-step cutting sequences (panel saw first, then table saw)
- Cost-optimizing board selection (picking cheapest combination of board sizes)

---

## Algorithm

### Sheet Goods: 2D Bin-Packing

**Algorithm:** Shelf-based first-fit-decreasing (FFD).

1. Collect all sheet good parts (including spares from mistake buffer)
2. Add kerf allowance (1/8" per cut edge) to each part dimension
3. Sort parts by height descending
4. For each part, try to place it on an existing shelf (left-to-right) on an existing sheet
5. If it doesn't fit on any shelf, start a new shelf on the current sheet
6. If the sheet is full, start a new sheet
7. Parts can be rotated 90° during packing if it results in a better fit

**Sheet size:** 48" × 96" (4' × 8'), fixed.

**Output per sheet:**
- List of placed parts with (x, y, width, height) positions
- Total waste percentage
- Waste area dimensions (for identifying usable offcuts)

### Solid Lumber: 1D Strip-Packing

**Algorithm:** First-fit-decreasing by length.

Solid lumber parts are cut from boards of a given width. Parts need a specific length and width. Multiple parts can be cut side-by-side from a wide board if widths fit.

1. Collect all solid lumber parts (including spares)
2. Add milling allowance to each part (+1" length, +0.5" width)
3. Group parts by rough thickness (4/4, 5/4, 6/4, 8/4)
4. For each thickness group:
   a. Sort parts by length descending
   b. For each part, try to fit it on an existing board (remaining length × board width)
   c. If it fits, place it; otherwise start a new board
5. Parts are packed along the length, side-by-side if widths allow

**Default board sizes** (user-editable):

| Thickness | Default Width | Default Length |
|-----------|-------------|---------------|
| 4/4 | 6" | 96" (8') |
| 5/4 | 6" | 96" (8') |
| 6/4 | 6" | 96" (8') |
| 8/4 | 6" | 72" (6') |

**Output per board:**
- List of placed parts with (x, y, width, height) positions
- Total waste percentage
- Remaining usable length

---

## Mistake Buffer

### Configuration

Two modes, togglable per material type:

**Percentage mode** (default for sheet goods):
- Adds extra area capacity when calculating sheet count
- Default: 15%
- Effect: if parts need 4200 sq in, the optimizer packs for 4830 sq in (4200 × 1.15)
- In practice: may add an extra sheet, or leave more usable waste on the last sheet

**Spare parts mode** (default for solid lumber):
- Adds N extra copies of each unique part before packing
- Default: +1 per unique part
- Effect: if there are 5 unique parts, 5 spare parts are added to the packing list
- Spare parts shown with dashed borders in the diagram

### UI Controls

A settings bar above the cut layout with:
- Toggle: "Waste %" / "Extra parts" (per material type)
- Number input for the value (percentage or count)
- Defaults pre-filled, user can adjust
- "Re-optimize" button to re-run after changes

---

## Interactive Features

### Drag & Drop

- Drag a part from one board/sheet to another
- Drop on empty space below to create a new board
- Waste recalculates live after each move
- Invalid placements (part doesn't fit) snap back with a visual indicator

### Rotate (Sheets Only)

- Click a part on a sheet diagram to rotate 90°
- Part snaps to new position if it still fits
- If rotation causes overlap, revert with a shake animation

### Edit Board Dimensions (Lumber Only)

- Click the board header (e.g., "Board 1 — 8/4 Red Oak (37" × 6")") to edit width and length
- Useful when you're at the lumber yard and found a 7" wide board instead of 6"
- Parts re-flow on the board after dimension change
- "Re-optimize" re-runs the full algorithm with updated dimensions

---

## API

### POST /api/optimize

**Request:**
```json
{
  "parts": [...],           // Part objects from AnalyzeResponse
  "shopping_list": [...],   // ShoppingItem objects
  "solid_species": "Red Oak",
  "sheet_type": "Baltic Birch Ply",
  "buffer_config": {
    "sheet_mode": "percentage",
    "sheet_value": 15,
    "lumber_mode": "extra_parts",
    "lumber_value": 1
  },
  "board_sizes": {
    "4/4": {"width": 6.0, "length": 96.0},
    "5/4": {"width": 6.0, "length": 96.0},
    "6/4": {"width": 6.0, "length": 96.0},
    "8/4": {"width": 6.0, "length": 72.0}
  }
}
```

**Response:**
```json
{
  "sheets": [
    {
      "material": "1/2\" Baltic Birch",
      "width": 48.0,
      "length": 96.0,
      "placements": [
        {"part_name": "Shelf A", "x": 0, "y": 0, "width": 16.25, "height": 15.25, "rotated": false, "is_spare": false},
        {"part_name": "Spare Shelf", "x": 0, "y": 15.375, "width": 16.25, "height": 15.25, "rotated": false, "is_spare": true}
      ],
      "waste_percent": 12.4
    }
  ],
  "boards": [
    {
      "material": "8/4 Red Oak",
      "thickness": "8/4",
      "width": 6.0,
      "length": 72.0,
      "placements": [
        {"part_name": "Leg A", "x": 0, "y": 0, "width": 36.0, "height": 2.0, "is_spare": false},
        {"part_name": "Leg B", "x": 0, "y": 2.5, "width": 36.0, "height": 2.0, "is_spare": false}
      ],
      "waste_percent": 8.2
    }
  ],
  "summary": {
    "total_sheets": 1,
    "total_boards": 2,
    "avg_waste_percent": 10.3,
    "total_spare_parts": 5
  },
  "updated_shopping_list": [...]
}
```

The `updated_shopping_list` reflects the optimized counts (may differ from the naive calculation in the original analysis).

---

## Backend Implementation

### Files

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/app/optimizer/__init__.py` | Create | Package init |
| `backend/app/optimizer/packer.py` | Create | Core packing algorithms (shelf FFD for sheets, FFD for lumber) |
| `backend/app/optimizer/buffer.py` | Create | Mistake buffer logic (add spares, calculate extra area) |
| `backend/app/optimizer/optimize.py` | Create | Orchestrator: takes parts + config, runs both packers, returns layout |
| `backend/app/models.py` | Modify | Add OptimizeRequest, OptimizeResponse, Placement, BoardLayout, SheetLayout models |
| `backend/app/main.py` | Modify | Add POST /api/optimize endpoint |
| `backend/tests/test_packer.py` | Create | Packing algorithm unit tests |
| `backend/tests/test_buffer.py` | Create | Buffer logic tests |
| `backend/tests/test_optimizer.py` | Create | Integration tests for the full optimize flow |

### Packing Algorithm Details

**Shelf FFD for sheets:**

```
for each sheet:
  shelves = []
  for each part (sorted by height desc):
    placed = False
    for each shelf in shelves:
      if part fits in remaining width of shelf:
        place part, update shelf remaining width
        placed = True
        break
    if not placed:
      if new shelf fits on current sheet:
        create shelf, place part
      else:
        start new sheet, create shelf, place part
```

A shelf is a horizontal row across the sheet. Each shelf has a fixed height (determined by the first part placed) and parts are placed left-to-right.

**FFD for lumber:**

Parts are sorted by length. For each part, find the first board with enough remaining length. Parts sit side-by-side on a board if widths allow (board width ÷ part width = how many side-by-side). If no board fits, add a new board.

---

## Frontend Implementation

### Files

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/src/lib/types.ts` | Modify | Add OptimizeRequest, OptimizeResponse, Placement, etc. |
| `frontend/src/lib/api.ts` | Modify | Add `optimize()` function |
| `frontend/src/lib/components/CutLayout.svelte` | Create | Main cut layout component with diagrams, drag/drop, controls |
| `frontend/src/lib/components/SheetDiagram.svelte` | Create | Single sheet diagram with positioned parts |
| `frontend/src/lib/components/BoardDiagram.svelte` | Create | Single board diagram with positioned parts |
| `frontend/src/lib/components/BufferControls.svelte` | Create | Buffer mode toggle + value input |
| `frontend/src/lib/components/Results.svelte` | Modify | Add "Cut Layout" tab |
| `frontend/src/routes/+page.svelte` | Modify | Wire optimize call after analyze |

### Interaction Flow

1. User clicks "Analyze" (existing flow)
2. After analysis completes, frontend automatically calls `POST /api/optimize`
3. "Cut Layout" tab appears in results with the diagrams
4. User can interact (drag, rotate, edit dimensions)
5. Manual changes update local state; "Re-optimize" re-calls the API
6. Shopping list tab shows optimized counts when optimization is available

### Diagram Rendering

SVG-based rendering for the diagrams. Each sheet/board is an SVG viewBox scaled to the material dimensions. Parts are positioned `<rect>` elements with text labels. Drag implemented via SVG mouse events.

- Parts: solid fill, labeled with name + dimensions
- Spare parts: dashed border, amber/yellow tint
- Waste: hatched pattern or light gray
- Kerf lines: thin lines between parts

---

## PDF Report Integration

The cut layout section is added to the report template after the Shopping List section:

- One diagram per sheet/board (rendered as static SVG embedded in HTML)
- Same styling as the web UI but non-interactive
- Summary table with waste percentages
- Buffer settings noted ("Includes +1 spare per unique part")

---

## Testing

- Unit test: shelf FFD packs simple rectangles correctly
- Unit test: FFD lumber packs parts by length
- Unit test: parts that don't fit start a new sheet/board
- Unit test: rotation improves packing (known case)
- Unit test: spare parts mode adds correct number of spares
- Unit test: percentage mode increases effective area
- Unit test: kerf allowance is applied
- Integration test: /api/optimize returns valid layout for the test 3MF fixture
- Frontend: Cut Layout tab renders diagrams
- Frontend: drag & drop moves parts between boards
