# Cut Optimization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a cut optimization engine that packs parts onto boards/sheets to minimize waste, with visual diagrams, configurable mistake buffer, and editable board sizes.

**Architecture:** Backend packing algorithms (shelf FFD for sheets, 1D FFD for lumber) exposed via `POST /api/optimize`. Frontend renders SVG diagrams of the layouts with buffer controls and editable board sizes. Interactive drag-and-drop is deferred to phase 2 — this phase delivers static optimized layouts with a "Re-optimize" button.

**Tech Stack:** Pure Python algorithms (no external solver), SVG rendering in Svelte, existing WeasyPrint for PDF.

**Spec:** `docs/superpowers/specs/2026-04-28-cut-optimization-design.md`

**Phase 1 scope (this plan):** Algorithms, static diagrams, buffer controls, editable board sizes, re-optimize button, PDF integration.

**Phase 2 (future):** Drag-and-drop parts between boards, click-to-rotate on sheets.

---

## File Map

### Backend

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/app/optimizer/__init__.py` | Create | Package init |
| `backend/app/optimizer/buffer.py` | Create | Add spare parts or percentage waste buffer |
| `backend/app/optimizer/sheet_packer.py` | Create | 2D shelf-based FFD for sheet goods |
| `backend/app/optimizer/lumber_packer.py` | Create | 1D FFD strip-packing for solid lumber |
| `backend/app/optimizer/optimize.py` | Create | Orchestrator: splits parts, runs both packers, assembles response |
| `backend/app/models.py` | Modify | Add optimization-related Pydantic models |
| `backend/app/main.py` | Modify | Add POST /api/optimize endpoint |
| `backend/app/templates/report.html` | Modify | Add cut layout section with SVG diagrams |
| `backend/tests/test_buffer.py` | Create | Buffer logic tests |
| `backend/tests/test_sheet_packer.py` | Create | Sheet packing algorithm tests |
| `backend/tests/test_lumber_packer.py` | Create | Lumber packing algorithm tests |
| `backend/tests/test_optimizer.py` | Create | Orchestrator integration tests |

### Frontend

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/src/lib/types.ts` | Modify | Add optimization types |
| `frontend/src/lib/api.ts` | Modify | Add optimize() function |
| `frontend/src/lib/components/CutLayout.svelte` | Create | Main cut layout component: buffer controls + diagrams + summary |
| `frontend/src/lib/components/SheetDiagram.svelte` | Create | SVG diagram for one sheet |
| `frontend/src/lib/components/BoardDiagram.svelte` | Create | SVG diagram for one lumber board |
| `frontend/src/lib/components/Results.svelte` | Modify | Add "Cut Layout" tab |
| `frontend/src/routes/+page.svelte` | Modify | Call optimize after analyze, pass to Results |

---

## Task 1: Pydantic Models for Optimization

**Files:**
- Modify: `backend/app/models.py`

- [ ] **Step 1: Add optimization models**

Add these classes to the end of `backend/app/models.py`:

```python
class BufferConfig(BaseModel):
    sheet_mode: str = "percentage"    # "percentage" or "extra_parts"
    sheet_value: float = 15.0         # 15% or N extra parts
    lumber_mode: str = "extra_parts"  # "percentage" or "extra_parts"
    lumber_value: float = 1.0         # N extra per unique part or %


class BoardSizeConfig(BaseModel):
    width: float = 6.0    # inches
    length: float = 96.0  # inches


class Placement(BaseModel):
    part_name: str
    x: float
    y: float
    width: float
    height: float
    rotated: bool = False
    is_spare: bool = False


class SheetLayout(BaseModel):
    material: str
    width: float       # sheet width in inches (48)
    length: float      # sheet length in inches (96)
    placements: list[Placement]
    waste_percent: float


class BoardLayout(BaseModel):
    material: str
    thickness: str
    width: float       # board width in inches
    length: float      # board length in inches
    placements: list[Placement]
    waste_percent: float


class OptimizeSummary(BaseModel):
    total_sheets: int
    total_boards: int
    avg_waste_percent: float
    total_spare_parts: int


class OptimizeRequest(BaseModel):
    parts: list[Part]
    shopping_list: list[ShoppingItem]
    solid_species: str
    sheet_type: str
    buffer_config: BufferConfig = BufferConfig()
    board_sizes: dict[str, BoardSizeConfig] = {}


class OptimizeResponse(BaseModel):
    sheets: list[SheetLayout]
    boards: list[BoardLayout]
    summary: OptimizeSummary
    updated_shopping_list: list[ShoppingItem]
```

- [ ] **Step 2: Run existing tests**

```bash
cd backend && source .venv/bin/activate && pytest -v
```

Expected: All 138 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/app/models.py
git commit -m "feat: add Pydantic models for cut optimization"
```

---

## Task 2: Buffer Logic

**Files:**
- Create: `backend/app/optimizer/__init__.py`
- Create: `backend/app/optimizer/buffer.py`
- Create: `backend/tests/test_buffer.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_buffer.py
import pytest
from app.optimizer.buffer import apply_spare_parts, apply_percentage_buffer
from app.models import Part, BoardType


def _make_part(name: str, qty: int, board_type: str = "solid") -> Part:
    return Part(
        name=name, quantity=qty, length_mm=762.0, width_mm=63.5,
        thickness_mm=19.05, board_type=BoardType(board_type),
        stock="4/4 Red Oak", notes="",
    )


class TestApplySpareParts:
    def test_adds_one_spare_per_unique(self):
        parts = [_make_part("Rail", 2), _make_part("Stile", 3)]
        result = apply_spare_parts(parts, spares_per_unique=1)
        # Should add 1 spare Rail and 1 spare Stile
        spares = [p for p in result if p.is_spare]
        assert len(spares) == 2
        assert all(p.quantity == 1 for p in spares)

    def test_adds_multiple_spares(self):
        parts = [_make_part("Rail", 2)]
        result = apply_spare_parts(parts, spares_per_unique=2)
        spares = [p for p in result if p.is_spare]
        assert len(spares) == 1
        assert spares[0].quantity == 2

    def test_preserves_original_parts(self):
        parts = [_make_part("Rail", 2)]
        result = apply_spare_parts(parts, spares_per_unique=1)
        originals = [p for p in result if not p.is_spare]
        assert len(originals) == 1
        assert originals[0].quantity == 2


class TestApplyPercentageBuffer:
    def test_returns_multiplier(self):
        multiplier = apply_percentage_buffer(15.0)
        assert multiplier == pytest.approx(1.15)

    def test_zero_percent(self):
        multiplier = apply_percentage_buffer(0.0)
        assert multiplier == pytest.approx(1.0)
```

- [ ] **Step 2: Implement buffer module**

```python
# backend/app/optimizer/__init__.py
```

```python
# backend/app/optimizer/buffer.py
"""Mistake buffer logic for cut optimization."""

from app.models import Part


class SparePart(Part):
    """A spare part added by the mistake buffer."""
    is_spare: bool = True


def apply_spare_parts(parts: list[Part], spares_per_unique: int = 1) -> list[Part]:
    """Add spare copies of each unique part. Returns original parts + spares."""
    result = list(parts)
    for part in parts:
        spare = SparePart(
            name=f"Spare {part.name}",
            quantity=spares_per_unique,
            length_mm=part.length_mm,
            width_mm=part.width_mm,
            thickness_mm=part.thickness_mm,
            board_type=part.board_type,
            stock=part.stock,
            notes="(mistake buffer)",
            is_spare=True,
        )
        result.append(spare)
    return result


def apply_percentage_buffer(percentage: float) -> float:
    """Return an area multiplier for percentage-based buffer. 15% → 1.15."""
    return 1.0 + (percentage / 100.0)
```

- [ ] **Step 3: Run tests**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_buffer.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/optimizer/ backend/tests/test_buffer.py
git commit -m "feat: add mistake buffer logic for cut optimization"
```

---

## Task 3: Sheet Packer (2D Shelf FFD)

**Files:**
- Create: `backend/app/optimizer/sheet_packer.py`
- Create: `backend/tests/test_sheet_packer.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_sheet_packer.py
import pytest
from app.optimizer.sheet_packer import pack_sheets, PackingPiece


class TestPackSheets:
    def test_single_small_part_fits_one_sheet(self):
        pieces = [PackingPiece("Part A", 16.0, 15.0, False)]
        sheets = pack_sheets(pieces, sheet_w=48.0, sheet_l=96.0, kerf=0.125)
        assert len(sheets) == 1
        assert len(sheets[0].placements) == 1

    def test_multiple_parts_pack_efficiently(self):
        # 3 pieces that should fit on one 48x96 sheet
        pieces = [
            PackingPiece("A", 16.0, 15.0, False),
            PackingPiece("B", 16.0, 15.0, False),
            PackingPiece("C", 16.0, 15.0, False),
        ]
        sheets = pack_sheets(pieces, sheet_w=48.0, sheet_l=96.0, kerf=0.125)
        assert len(sheets) == 1

    def test_overflow_creates_new_sheet(self):
        # Parts that exceed one sheet
        pieces = [PackingPiece(f"P{i}", 25.0, 25.0, False) for i in range(8)]
        # 8 × 25×25 = 5000 sq in, sheet = 4608 sq in
        sheets = pack_sheets(pieces, sheet_w=48.0, sheet_l=96.0, kerf=0.125)
        assert len(sheets) >= 2

    def test_placements_have_coordinates(self):
        pieces = [PackingPiece("A", 16.0, 15.0, False)]
        sheets = pack_sheets(pieces, sheet_w=48.0, sheet_l=96.0, kerf=0.125)
        p = sheets[0].placements[0]
        assert p.x >= 0
        assert p.y >= 0
        assert p.width == pytest.approx(16.0)
        assert p.height == pytest.approx(15.0)

    def test_kerf_applied_between_parts(self):
        # Two parts side by side — kerf should create gap
        pieces = [
            PackingPiece("A", 23.0, 15.0, False),
            PackingPiece("B", 23.0, 15.0, False),
        ]
        sheets = pack_sheets(pieces, sheet_w=48.0, sheet_l=96.0, kerf=0.125)
        p1, p2 = sheets[0].placements[0], sheets[0].placements[1]
        # Second part should start after first + kerf
        if p1.y == p2.y:  # same shelf
            assert p2.x >= p1.x + p1.width + 0.125

    def test_waste_percent_calculated(self):
        pieces = [PackingPiece("A", 24.0, 48.0, False)]
        sheets = pack_sheets(pieces, sheet_w=48.0, sheet_l=96.0, kerf=0.125)
        # Part is 24×48 = 1152 sq in, sheet is 48×96 = 4608, waste ≈ 75%
        assert sheets[0].waste_percent > 50

    def test_spare_flag_preserved(self):
        pieces = [
            PackingPiece("A", 16.0, 15.0, False),
            PackingPiece("Spare A", 16.0, 15.0, True),
        ]
        sheets = pack_sheets(pieces, sheet_w=48.0, sheet_l=96.0, kerf=0.125)
        placements = sheets[0].placements
        spares = [p for p in placements if p.is_spare]
        assert len(spares) == 1
```

- [ ] **Step 2: Implement sheet packer**

```python
# backend/app/optimizer/sheet_packer.py
"""2D shelf-based first-fit-decreasing bin packing for sheet goods."""

from dataclasses import dataclass
from app.models import Placement, SheetLayout


@dataclass
class PackingPiece:
    name: str
    width: float   # inches
    height: float  # inches
    is_spare: bool


@dataclass
class _Shelf:
    y: float          # top-left Y position on the sheet
    height: float     # shelf height (set by first piece)
    used_width: float # how much width is consumed


def pack_sheets(
    pieces: list[PackingPiece],
    sheet_w: float = 48.0,
    sheet_l: float = 96.0,
    kerf: float = 0.125,
    material: str = "",
) -> list[SheetLayout]:
    """Pack rectangular pieces onto sheets using shelf FFD.

    Pieces are sorted by height descending. Each shelf spans the full
    sheet width. Pieces are placed left-to-right within shelves.
    A new shelf is started when a piece doesn't fit horizontally.
    A new sheet is started when a piece doesn't fit vertically.
    """
    if not pieces:
        return []

    # Sort by height descending for better shelf utilization
    sorted_pieces = sorted(pieces, key=lambda p: p.height, reverse=True)

    sheets: list[dict] = []  # [{shelves: [_Shelf], placements: [Placement]}]

    def new_sheet():
        sheets.append({"shelves": [], "placements": []})

    new_sheet()

    for piece in sorted_pieces:
        pw = piece.width + kerf
        ph = piece.height + kerf
        placed = False

        for sheet in sheets:
            for shelf in sheet["shelves"]:
                if shelf.used_width + pw <= sheet_w and piece.height <= shelf.height:
                    # Fits on this shelf
                    sheet["placements"].append(Placement(
                        part_name=piece.name,
                        x=shelf.used_width,
                        y=shelf.y,
                        width=piece.width,
                        height=piece.height,
                        rotated=False,
                        is_spare=piece.is_spare,
                    ))
                    shelf.used_width += pw
                    placed = True
                    break

            if placed:
                break

            # Try new shelf on this sheet
            shelf_y = sum(s.height + kerf for s in sheet["shelves"])
            if shelf_y + ph <= sheet_l:
                new_shelf = _Shelf(y=shelf_y, height=piece.height, used_width=0)
                sheet["placements"].append(Placement(
                    part_name=piece.name,
                    x=0,
                    y=shelf_y,
                    width=piece.width,
                    height=piece.height,
                    rotated=False,
                    is_spare=piece.is_spare,
                ))
                new_shelf.used_width = pw
                sheet["shelves"].append(new_shelf)
                placed = True
                break

        if not placed:
            new_sheet()
            sheet = sheets[-1]
            new_shelf = _Shelf(y=0, height=piece.height, used_width=pw)
            sheet["placements"].append(Placement(
                part_name=piece.name,
                x=0,
                y=0,
                width=piece.width,
                height=piece.height,
                rotated=False,
                is_spare=piece.is_spare,
            ))
            sheet["shelves"].append(new_shelf)

    # Convert to SheetLayout objects
    sheet_area = sheet_w * sheet_l
    results = []
    for sheet in sheets:
        if not sheet["placements"]:
            continue
        used_area = sum(p.width * p.height for p in sheet["placements"])
        waste = max(0, (1 - used_area / sheet_area) * 100)
        results.append(SheetLayout(
            material=material,
            width=sheet_w,
            length=sheet_l,
            placements=sheet["placements"],
            waste_percent=round(waste, 1),
        ))

    return results
```

- [ ] **Step 3: Run tests**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_sheet_packer.py -v
```

Expected: All 7 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/optimizer/sheet_packer.py backend/tests/test_sheet_packer.py
git commit -m "feat: add 2D shelf-based FFD sheet packer"
```

---

## Task 4: Lumber Packer (1D FFD)

**Files:**
- Create: `backend/app/optimizer/lumber_packer.py`
- Create: `backend/tests/test_lumber_packer.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_lumber_packer.py
import pytest
from app.optimizer.lumber_packer import pack_lumber, LumberPiece


class TestPackLumber:
    def test_single_part_one_board(self):
        pieces = [LumberPiece("Leg", 36.0, 2.0, False)]
        boards = pack_lumber(pieces, board_w=6.0, board_l=96.0, kerf=0.125)
        assert len(boards) == 1
        assert len(boards[0].placements) == 1

    def test_multiple_parts_side_by_side(self):
        # Two 2" wide parts should fit side-by-side on a 6" board
        pieces = [
            LumberPiece("Leg A", 36.0, 2.0, False),
            LumberPiece("Leg B", 36.0, 2.0, False),
        ]
        boards = pack_lumber(pieces, board_w=6.0, board_l=96.0, kerf=0.125)
        assert len(boards) == 1

    def test_parts_along_length(self):
        # Two 50" parts can't sit side by side but fit end-to-end on a 96" board
        pieces = [
            LumberPiece("A", 50.0, 5.0, False),
            LumberPiece("B", 40.0, 5.0, False),
        ]
        boards = pack_lumber(pieces, board_w=6.0, board_l=96.0, kerf=0.125)
        assert len(boards) == 1

    def test_overflow_creates_new_board(self):
        # Parts that don't fit on one board
        pieces = [
            LumberPiece("A", 50.0, 5.0, False),
            LumberPiece("B", 50.0, 5.0, False),
        ]
        boards = pack_lumber(pieces, board_w=6.0, board_l=96.0, kerf=0.125)
        assert len(boards) == 2

    def test_waste_percent_calculated(self):
        pieces = [LumberPiece("A", 36.0, 2.0, False)]
        boards = pack_lumber(pieces, board_w=6.0, board_l=96.0, kerf=0.125)
        # 36×2 = 72 sq in on a 6×96 = 576 sq in board → ~87.5% waste
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
```

- [ ] **Step 2: Implement lumber packer**

```python
# backend/app/optimizer/lumber_packer.py
"""1D first-fit-decreasing strip packing for solid lumber."""

from dataclasses import dataclass
from app.models import Placement, BoardLayout


@dataclass
class LumberPiece:
    name: str
    length: float  # inches (along the board)
    width: float   # inches (across the board)
    is_spare: bool


@dataclass
class _BoardSlot:
    """Tracks a row of parts across the board width."""
    y: float          # y position (across board width)
    height: float     # width of this row of parts
    used_length: float  # how much length is consumed in this row


def pack_lumber(
    pieces: list[LumberPiece],
    board_w: float = 6.0,
    board_l: float = 96.0,
    kerf: float = 0.125,
    material: str = "",
    thickness: str = "",
) -> list[BoardLayout]:
    """Pack lumber pieces onto boards using first-fit-decreasing.

    Parts are sorted by length descending. Each board has rows across
    its width. Parts are placed along the length within rows, and new
    rows are added across the width when a part doesn't fit.
    """
    if not pieces:
        return []

    sorted_pieces = sorted(pieces, key=lambda p: p.length, reverse=True)

    boards: list[dict] = []  # [{slots: [_BoardSlot], placements: [Placement]}]

    def new_board():
        boards.append({"slots": [], "placements": []})

    new_board()

    for piece in sorted_pieces:
        pl = piece.length + kerf
        pw = piece.width + kerf
        placed = False

        for board in boards:
            # Try to fit in an existing slot (row)
            for slot in board["slots"]:
                if slot.used_length + pl <= board_l and piece.width <= slot.height:
                    board["placements"].append(Placement(
                        part_name=piece.name,
                        x=slot.used_length,
                        y=slot.y,
                        width=piece.length,
                        height=piece.width,
                        rotated=False,
                        is_spare=piece.is_spare,
                    ))
                    slot.used_length += pl
                    placed = True
                    break

            if placed:
                break

            # Try new row on this board
            slot_y = sum(s.height + kerf for s in board["slots"])
            if slot_y + pw <= board_w:
                new_slot = _BoardSlot(y=slot_y, height=piece.width, used_length=pl)
                board["placements"].append(Placement(
                    part_name=piece.name,
                    x=0,
                    y=slot_y,
                    width=piece.length,
                    height=piece.width,
                    rotated=False,
                    is_spare=piece.is_spare,
                ))
                board["slots"].append(new_slot)
                placed = True
                break

        if not placed:
            new_board()
            board = boards[-1]
            new_slot = _BoardSlot(y=0, height=piece.width, used_length=pl)
            board["placements"].append(Placement(
                part_name=piece.name,
                x=0,
                y=0,
                width=piece.length,
                height=piece.width,
                rotated=False,
                is_spare=piece.is_spare,
            ))
            board["slots"].append(new_slot)

    # Convert to BoardLayout objects
    results = []
    for board in boards:
        if not board["placements"]:
            continue
        board_area = board_w * board_l
        used_area = sum(p.width * p.height for p in board["placements"])
        waste = max(0, (1 - used_area / board_area) * 100)
        results.append(BoardLayout(
            material=material,
            thickness=thickness,
            width=board_w,
            length=board_l,
            placements=board["placements"],
            waste_percent=round(waste, 1),
        ))

    return results
```

- [ ] **Step 3: Run tests**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_lumber_packer.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/optimizer/lumber_packer.py backend/tests/test_lumber_packer.py
git commit -m "feat: add 1D FFD lumber packer"
```

---

## Task 5: Optimizer Orchestrator + API Endpoint

**Files:**
- Create: `backend/app/optimizer/optimize.py`
- Create: `backend/tests/test_optimizer.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write orchestrator tests**

```python
# backend/tests/test_optimizer.py
import pytest
from app.optimizer.optimize import run_optimization
from app.models import (
    Part, ShoppingItem, BoardType, BufferConfig, BoardSizeConfig,
)


def _sample_parts() -> list[Part]:
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


def _sample_shopping() -> list[ShoppingItem]:
    return [
        ShoppingItem(material='1/2" Baltic Birch', thickness='1/2"', quantity=1.0, unit="sheets"),
        ShoppingItem(material="8/4 Red Oak", thickness="8/4", quantity=5.8, unit="BF"),
        ShoppingItem(material="4/4 Red Oak", thickness="4/4", quantity=1.0, unit="BF"),
    ]


class TestRunOptimization:
    def test_returns_sheets_and_boards(self):
        result = run_optimization(
            parts=_sample_parts(),
            shopping_list=_sample_shopping(),
            solid_species="Red Oak",
            sheet_type="Baltic Birch",
        )
        assert len(result.sheets) >= 1
        assert len(result.boards) >= 1

    def test_spare_parts_mode(self):
        config = BufferConfig(lumber_mode="extra_parts", lumber_value=1)
        result = run_optimization(
            parts=_sample_parts(),
            shopping_list=_sample_shopping(),
            solid_species="Red Oak",
            sheet_type="Baltic Birch",
            buffer_config=config,
        )
        all_placements = []
        for b in result.boards:
            all_placements.extend(b.placements)
        spares = [p for p in all_placements if p.is_spare]
        assert len(spares) >= 1

    def test_summary_populated(self):
        result = run_optimization(
            parts=_sample_parts(),
            shopping_list=_sample_shopping(),
            solid_species="Red Oak",
            sheet_type="Baltic Birch",
        )
        assert result.summary.total_sheets >= 1
        assert result.summary.total_boards >= 1
        assert result.summary.avg_waste_percent >= 0

    def test_custom_board_sizes(self):
        sizes = {"8/4": BoardSizeConfig(width=8.0, length=72.0)}
        result = run_optimization(
            parts=_sample_parts(),
            shopping_list=_sample_shopping(),
            solid_species="Red Oak",
            sheet_type="Baltic Birch",
            board_sizes=sizes,
        )
        boards_8_4 = [b for b in result.boards if b.thickness == "8/4"]
        if boards_8_4:
            assert boards_8_4[0].width == 8.0
            assert boards_8_4[0].length == 72.0
```

- [ ] **Step 2: Implement orchestrator**

```python
# backend/app/optimizer/optimize.py
"""Cut optimization orchestrator."""

from app.models import (
    Part, ShoppingItem, BoardType, BufferConfig, BoardSizeConfig,
    OptimizeResponse, OptimizeSummary,
)
from app.optimizer.buffer import apply_spare_parts, apply_percentage_buffer
from app.optimizer.sheet_packer import pack_sheets, PackingPiece
from app.optimizer.lumber_packer import pack_lumber, LumberPiece
from app.units import mm_to_inches

# Default board sizes by rough thickness
DEFAULT_BOARD_SIZES = {
    "4/4": BoardSizeConfig(width=6.0, length=96.0),
    "5/4": BoardSizeConfig(width=6.0, length=96.0),
    "6/4": BoardSizeConfig(width=6.0, length=96.0),
    "8/4": BoardSizeConfig(width=6.0, length=72.0),
}

SHEET_WIDTH = 48.0
SHEET_LENGTH = 96.0
KERF = 0.125
MILL_LENGTH = 1.0
MILL_WIDTH = 0.5


def _expand_parts(parts: list[Part]) -> list[Part]:
    """Expand grouped parts (qty > 1) into individual instances."""
    expanded = []
    for part in parts:
        for i in range(part.quantity):
            suffix = f" #{i+1}" if part.quantity > 1 else ""
            expanded.append(part.model_copy(update={
                "name": f"{part.name}{suffix}",
                "quantity": 1,
            }))
    return expanded


def run_optimization(
    parts: list[Part],
    shopping_list: list[ShoppingItem],
    solid_species: str,
    sheet_type: str,
    buffer_config: BufferConfig = BufferConfig(),
    board_sizes: dict[str, BoardSizeConfig] | None = None,
) -> OptimizeResponse:
    """Run the full cut optimization pipeline."""
    sizes = {**DEFAULT_BOARD_SIZES, **(board_sizes or {})}

    # Separate parts by type
    sheet_parts = [p for p in parts if p.board_type == BoardType.SHEET]
    lumber_parts = [p for p in parts if p.board_type in (BoardType.SOLID, BoardType.THICK_STOCK)]

    # Expand grouped parts
    sheet_expanded = _expand_parts(sheet_parts)
    lumber_expanded = _expand_parts(lumber_parts)

    # Apply buffers
    if buffer_config.sheet_mode == "extra_parts":
        sheet_with_buffer = apply_spare_parts(sheet_expanded, int(buffer_config.sheet_value))
    else:
        sheet_with_buffer = list(sheet_expanded)

    if buffer_config.lumber_mode == "extra_parts":
        # Apply spares to the unexpanded list then expand the spares
        spares_added = apply_spare_parts(lumber_parts, int(buffer_config.lumber_value))
        spare_parts_only = [p for p in spares_added if getattr(p, "is_spare", False)]
        lumber_spare_expanded = _expand_parts(spare_parts_only)
        lumber_with_buffer = lumber_expanded + lumber_spare_expanded
    else:
        lumber_with_buffer = list(lumber_expanded)

    # Pack sheets
    sheet_pieces = [
        PackingPiece(
            name=p.name,
            width=mm_to_inches(p.width_mm) + 2 * KERF,
            height=mm_to_inches(p.length_mm) + 2 * KERF,
            is_spare=getattr(p, "is_spare", False),
        )
        for p in sheet_with_buffer
    ]
    sheet_layouts = pack_sheets(
        sheet_pieces, SHEET_WIDTH, SHEET_LENGTH, KERF,
        material=sheet_type,
    )

    # Pack lumber by thickness group
    board_layouts = []
    thickness_groups: dict[str, list[Part]] = {}
    for p in lumber_with_buffer:
        rough = p.stock.split()[0] if p.stock else "4/4"
        thickness_groups.setdefault(rough, []).append(p)

    for thickness, group_parts in thickness_groups.items():
        size = sizes.get(thickness, BoardSizeConfig())
        lumber_pieces = [
            LumberPiece(
                name=p.name,
                length=mm_to_inches(p.length_mm) + MILL_LENGTH,
                width=mm_to_inches(p.width_mm) + MILL_WIDTH,
                is_spare=getattr(p, "is_spare", False),
            )
            for p in group_parts
        ]
        layouts = pack_lumber(
            lumber_pieces, size.width, size.length, KERF,
            material=f"{thickness} {solid_species}",
            thickness=thickness,
        )
        board_layouts.extend(layouts)

    # Summary
    total_sheets = len(sheet_layouts)
    total_boards = len(board_layouts)
    all_waste = [s.waste_percent for s in sheet_layouts] + [b.waste_percent for b in board_layouts]
    avg_waste = sum(all_waste) / len(all_waste) if all_waste else 0.0
    total_spares = sum(
        1 for layout in sheet_layouts + board_layouts
        for p in layout.placements if p.is_spare
    )

    # Updated shopping list
    updated = list(shopping_list)
    for i, item in enumerate(updated):
        if item.unit == "sheets":
            matching = [s for s in sheet_layouts if s.material == item.material or sheet_type in (item.material or "")]
            if matching:
                updated[i] = item.model_copy(update={"quantity": float(len(matching))})
        elif item.unit == "BF":
            matching = [b for b in board_layouts if item.thickness and b.thickness == item.thickness]
            if matching:
                total_bf = sum(b.width * b.length / 144.0 for b in matching)
                updated[i] = item.model_copy(update={"quantity": round(total_bf, 1)})

    return OptimizeResponse(
        sheets=sheet_layouts,
        boards=board_layouts,
        summary=OptimizeSummary(
            total_sheets=total_sheets,
            total_boards=total_boards,
            avg_waste_percent=round(avg_waste, 1),
            total_spare_parts=total_spares,
        ),
        updated_shopping_list=updated,
    )
```

- [ ] **Step 3: Run tests**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_optimizer.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 4: Add API endpoint**

Add to `backend/app/main.py` imports:

```python
from app.models import OptimizeRequest, OptimizeResponse
from app.optimizer.optimize import run_optimization
```

Add endpoint at the end:

```python
@app.post("/api/optimize", response_model=OptimizeResponse)
async def optimize_cuts(request: OptimizeRequest):
    return run_optimization(
        parts=request.parts,
        shopping_list=request.shopping_list,
        solid_species=request.solid_species,
        sheet_type=request.sheet_type,
        buffer_config=request.buffer_config,
        board_sizes=request.board_sizes,
    )
```

- [ ] **Step 5: Run full test suite**

```bash
cd backend && source .venv/bin/activate && pytest -v
```

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/optimizer/optimize.py backend/tests/test_optimizer.py backend/app/main.py
git commit -m "feat: add cut optimizer orchestrator and POST /api/optimize endpoint"
```

---

## Task 6: Frontend Types + API Client

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Add optimization types**

Add to the end of `frontend/src/lib/types.ts`:

```typescript
export interface BufferConfig {
	sheet_mode: 'percentage' | 'extra_parts';
	sheet_value: number;
	lumber_mode: 'percentage' | 'extra_parts';
	lumber_value: number;
}

export interface BoardSizeConfig {
	width: number;
	length: number;
}

export interface Placement {
	part_name: string;
	x: number;
	y: number;
	width: number;
	height: number;
	rotated: boolean;
	is_spare: boolean;
}

export interface SheetLayout {
	material: string;
	width: number;
	length: number;
	placements: Placement[];
	waste_percent: number;
}

export interface BoardLayout {
	material: string;
	thickness: string;
	width: number;
	length: number;
	placements: Placement[];
	waste_percent: number;
}

export interface OptimizeSummary {
	total_sheets: number;
	total_boards: number;
	avg_waste_percent: number;
	total_spare_parts: number;
}

export interface OptimizeRequest {
	parts: Part[];
	shopping_list: ShoppingItem[];
	solid_species: string;
	sheet_type: string;
	buffer_config?: BufferConfig;
	board_sizes?: Record<string, BoardSizeConfig>;
}

export interface OptimizeResponse {
	sheets: SheetLayout[];
	boards: BoardLayout[];
	summary: OptimizeSummary;
	updated_shopping_list: ShoppingItem[];
}
```

- [ ] **Step 2: Add optimize API function**

Add to `frontend/src/lib/api.ts` (update the type import and add function):

```typescript
// Add OptimizeRequest, OptimizeResponse to the existing import
import type { ..., OptimizeRequest, OptimizeResponse } from './types';

export async function optimizeCuts(request: OptimizeRequest): Promise<OptimizeResponse> {
	const response = await fetch(`${BASE}/optimize`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', ...authHeaders() },
		body: JSON.stringify(request),
	});
	if (!response.ok) {
		const detail = await response.json().catch(() => ({ detail: 'Optimization failed' }));
		throw new Error(detail.detail || 'Optimization failed');
	}
	return response.json();
}
```

- [ ] **Step 3: Verify build**

```bash
cd frontend && npx svelte-check && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts
git commit -m "feat: add optimization types and API client"
```

---

## Task 7: Frontend Diagram Components

**Files:**
- Create: `frontend/src/lib/components/SheetDiagram.svelte`
- Create: `frontend/src/lib/components/BoardDiagram.svelte`
- Create: `frontend/src/lib/components/CutLayout.svelte`

- [ ] **Step 1: Create SheetDiagram component**

Create `frontend/src/lib/components/SheetDiagram.svelte` — an SVG component that renders a single sheet with positioned parts. Each part is a `<rect>` with a text label. Spare parts have dashed stroke and amber fill. Waste is the background. The viewBox matches the sheet dimensions so parts are drawn to scale.

Props: `layout: SheetLayout`

- [ ] **Step 2: Create BoardDiagram component**

Create `frontend/src/lib/components/BoardDiagram.svelte` — similar to SheetDiagram but for a lumber board. Horizontal layout (boards are long and narrow). Same part styling.

Props: `layout: BoardLayout`

- [ ] **Step 3: Create CutLayout component**

Create `frontend/src/lib/components/CutLayout.svelte` — the main component that:
- Shows buffer controls (sheet mode + value, lumber mode + value)
- Shows default board size editors (per thickness)
- "Re-optimize" button
- Lists all sheet diagrams, then all board diagrams
- Shows summary table (total sheets, boards, avg waste, spare parts)

Props: `sheets: SheetLayout[]`, `boards: BoardLayout[]`, `summary: OptimizeSummary`, `onReoptimize: (config: BufferConfig, sizes: Record<string, BoardSizeConfig>) => void`, `optimizing: boolean`

- [ ] **Step 4: Verify build**

```bash
cd frontend && npx svelte-check && npm run build
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/components/SheetDiagram.svelte \
  frontend/src/lib/components/BoardDiagram.svelte \
  frontend/src/lib/components/CutLayout.svelte
git commit -m "feat: add SVG cut layout diagram components"
```

---

## Task 8: Wire Into Results + Page

**Files:**
- Modify: `frontend/src/lib/components/Results.svelte`
- Modify: `frontend/src/routes/+page.svelte`

- [ ] **Step 1: Add Cut Layout tab to Results**

Add a new `cutLayout` tab alongside parts/shopping/cost. Import `CutLayout` component. Add props for the optimization data: `optimizeResult: OptimizeResponse | null`, `onReoptimize`, `optimizing`.

When the Cut Layout tab is active, render the `<CutLayout>` component with the optimization data.

If `optimizeResult` is available, the shopping list tab should show `optimizeResult.updated_shopping_list` instead of the original.

- [ ] **Step 2: Wire optimize call in +page.svelte**

After a successful analyze, automatically call `optimizeCuts()` with the analysis results and default buffer config. Store the result in `optimizeResult` state. Pass it to `<Results>`.

Add a `handleReoptimize` function that re-calls the API with updated buffer config and board sizes.

- [ ] **Step 3: Verify build**

```bash
cd frontend && npx svelte-check && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/components/Results.svelte frontend/src/routes/+page.svelte
git commit -m "feat: add Cut Layout tab and auto-optimize after analysis"
```

---

## Task 9: PDF Report Integration

**Files:**
- Modify: `backend/app/templates/report.html`
- Modify: `backend/app/report.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Update report.py to accept optimization data**

Update `generate_report_pdf` signature to optionally accept `OptimizeResponse`. If provided, render the cut layout section in the template.

- [ ] **Step 2: Add cut layout section to report.html**

After the Shopping List section, add a "Cut Layout" section that renders static SVG diagrams for each sheet and board layout. Same visual style as the frontend but non-interactive. Use inline SVG in the Jinja2 template.

- [ ] **Step 3: Update /api/report to include optimization**

Run the optimizer in the report endpoint and pass the results to the template.

- [ ] **Step 4: Run tests**

```bash
cd backend && source .venv/bin/activate && pytest -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/templates/report.html backend/app/report.py backend/app/main.py
git commit -m "feat: include cut layout diagrams in PDF report"
```

---

## Task 10: End-to-End Verification

- [ ] **Step 1: Run full backend test suite**

```bash
cd backend && source .venv/bin/activate && pytest -v
```

- [ ] **Step 2: Verify frontend builds**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Manual smoke test**

1. Upload 3MF → analyze → verify Cut Layout tab appears with diagrams
2. Adjust buffer settings → click Re-optimize → verify layout updates
3. Edit board dimensions → Re-optimize → verify boards change
4. Download PDF → verify cut layout diagrams appear in report
5. Spare parts shown with dashed borders and different color
6. Waste areas visible with percentage labels

- [ ] **Step 4: Commit and push**

```bash
git add -A && git commit -m "chore: cut optimization e2e fixes" && git push
```
