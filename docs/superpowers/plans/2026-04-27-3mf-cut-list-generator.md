# 3MF Cut List Generator — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a web app that parses 3MF furniture models, classifies parts, maps to standard lumber sizes, and costs against a supplier catalog.

**Architecture:** SvelteKit frontend + Python FastAPI backend communicating over REST. Backend handles 3MF parsing, geometry analysis, material mapping, and supplier pricing. Frontend handles upload, 3D model viewing (Three.js), material configuration, and results display.

**Tech Stack:** Python 3.12+, FastAPI, numpy, BeautifulSoup4, SvelteKit, TypeScript, Three.js, Tailwind CSS, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-04-27-3mf-cut-list-generator-design.md`

---

## File Map

### Backend (`backend/`)

| File | Responsibility |
|------|---------------|
| `pyproject.toml` | Project metadata, dependencies |
| `requirements.txt` | Pinned dependencies for Docker |
| `app/__init__.py` | Package init |
| `app/main.py` | FastAPI app, CORS, route registration, session cleanup on startup |
| `app/models.py` | Pydantic models: Part, ShoppingItem, CostEstimate, AnalyzeRequest, AnalyzeResponse, UploadResponse |
| `app/units.py` | Unit conversion (mm canonical internally, convert to/from inches) |
| `app/session.py` | Session creation (UUID temp dirs), lookup, TTL cleanup |
| `app/parser/__init__.py` | Package init |
| `app/parser/threemf.py` | 3MF ZIP extraction, XML parsing, vertex/transform extraction, duplicate detection |
| `app/analyzer/__init__.py` | Package init |
| `app/analyzer/geometry.py` | AABB computation, dimension sorting, board type inference rules |
| `app/mapper/__init__.py` | Package init |
| `app/mapper/materials.py` | Thickness snapping, milling allowances, board feet calculation, sheet calculation, shopping list aggregation |
| `app/suppliers/__init__.py` | Package init |
| `app/suppliers/base.py` | SupplierBase ABC, Product and Money dataclasses |
| `app/suppliers/registry.py` | Supplier registry (get supplier by name) |
| `app/suppliers/woodworkers_source.py` | Scraper, JSON cache with TTL, rate limiting |
| `tests/__init__.py` | Package init |
| `tests/conftest.py` | Shared fixtures: test 3MF file builder, FastAPI test client |
| `tests/test_models.py` | Pydantic model validation |
| `tests/test_units.py` | Unit conversion tests |
| `tests/test_session.py` | Session lifecycle tests |
| `tests/test_parser.py` | 3MF parsing tests |
| `tests/test_geometry.py` | Board classification tests |
| `tests/test_materials.py` | Material mapping tests |
| `tests/test_supplier.py` | Supplier interface + WS mock tests |
| `tests/test_routes.py` | API endpoint integration tests |

### Frontend (`frontend/`)

| File | Responsibility |
|------|---------------|
| `src/lib/types.ts` | TypeScript types mirroring backend Pydantic models |
| `src/lib/api.ts` | Backend API client (upload, analyze, species, sheet-types) |
| `src/lib/components/Upload.svelte` | Drag-and-drop file upload with validation |
| `src/lib/components/ModelViewer.svelte` | Three.js 3MF renderer with OrbitControls |
| `src/lib/components/Configure.svelte` | Species/sheet dropdowns, toggles, analyze button |
| `src/lib/components/Results.svelte` | Tabbed results: parts list, shopping list, cost estimate |
| `src/routes/+page.svelte` | Main page orchestrating the three-step workflow |
| `src/routes/+layout.svelte` | App layout shell |

### Root

| File | Responsibility |
|------|---------------|
| `.gitignore` | Ignore node_modules, __pycache__, .venv, sessions, etc. |
| `docker-compose.yml` | Frontend + backend services |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/parser/__init__.py`
- Create: `backend/app/analyzer/__init__.py`
- Create: `backend/app/mapper/__init__.py`
- Create: `backend/app/suppliers/__init__.py`
- Create: `backend/tests/__init__.py`
- Create: `frontend/` (SvelteKit scaffold)
- Create: `.gitignore`

- [ ] **Step 1: Create backend project structure**

```toml
# backend/pyproject.toml
[project]
name = "cutlist-backend"
version = "0.1.0"
requires-python = ">=3.12"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

```txt
# backend/requirements.txt
fastapi==0.115.6
uvicorn[standard]==0.34.0
python-multipart==0.0.18
numpy==2.2.1
beautifulsoup4==4.12.3
requests==2.32.3
httpx==0.28.1
pytest==8.3.4
pytest-asyncio==0.25.0
```

Create empty `__init__.py` in each package directory:
- `backend/app/__init__.py`
- `backend/app/parser/__init__.py`
- `backend/app/analyzer/__init__.py`
- `backend/app/mapper/__init__.py`
- `backend/app/suppliers/__init__.py`
- `backend/tests/__init__.py`

- [ ] **Step 2: Install backend dependencies**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

- [ ] **Step 3: Verify pytest runs (no tests yet)**

```bash
cd backend && source .venv/bin/activate && pytest -v
```

Expected: "no tests ran" with exit code 0 (or 5 for no tests collected — both are fine).

- [ ] **Step 4: Scaffold SvelteKit frontend**

```bash
cd /home/josebiro/gt/mayor
npx sv create frontend --template minimal --types ts --no-add-ons --no-install
cd frontend
npm install
npm install -D tailwindcss @tailwindcss/vite three
npm install -D @types/three
```

- [ ] **Step 5: Configure Tailwind CSS**

Add Tailwind vite plugin to `frontend/vite.config.ts`:

```ts
import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()]
});
```

Add to `frontend/src/app.css`:

```css
@import 'tailwindcss';
```

Import the CSS in `frontend/src/routes/+layout.svelte`:

```svelte
<script>
	import '../app.css';
	let { children } = $props();
</script>

{@render children()}
```

- [ ] **Step 6: Configure SvelteKit dev proxy to FastAPI**

Add proxy config to `frontend/vite.config.ts`:

```ts
import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		proxy: {
			'/api': 'http://localhost:8000'
		}
	}
});
```

- [ ] **Step 7: Create .gitignore**

```gitignore
# Python
__pycache__/
*.pyc
.venv/
*.egg-info/
.pytest_cache/

# Node
node_modules/
.svelte-kit/
build/

# IDE
.vscode/
.idea/

# App
backend/sessions/
backend/cache/
.superpowers/

# OS
.DS_Store
```

- [ ] **Step 8: Verify frontend builds**

```bash
cd frontend && npm run build
```

Expected: Build completes without errors.

- [ ] **Step 9: Commit**

```bash
git add backend/pyproject.toml backend/requirements.txt \
  backend/app/__init__.py backend/app/parser/__init__.py \
  backend/app/analyzer/__init__.py backend/app/mapper/__init__.py \
  backend/app/suppliers/__init__.py backend/tests/__init__.py \
  frontend/ .gitignore
git commit -m "scaffold: backend (FastAPI) and frontend (SvelteKit) project structure"
```

---

## Task 2: Pydantic Models + Unit Conversion

**Files:**
- Create: `backend/app/models.py`
- Create: `backend/app/units.py`
- Create: `backend/tests/test_models.py`
- Create: `backend/tests/test_units.py`

- [ ] **Step 1: Write failing tests for unit conversion**

```python
# backend/tests/test_units.py
import pytest
from app.units import mm_to_inches, inches_to_mm, convert_from_3mf_unit


def test_mm_to_inches():
    assert mm_to_inches(25.4) == pytest.approx(1.0)
    assert mm_to_inches(0.0) == pytest.approx(0.0)
    assert mm_to_inches(304.8) == pytest.approx(12.0)


def test_inches_to_mm():
    assert inches_to_mm(1.0) == pytest.approx(25.4)
    assert inches_to_mm(12.0) == pytest.approx(304.8)


def test_convert_from_3mf_millimeter():
    assert convert_from_3mf_unit(100.0, "millimeter") == pytest.approx(100.0)


def test_convert_from_3mf_centimeter():
    assert convert_from_3mf_unit(10.0, "centimeter") == pytest.approx(100.0)


def test_convert_from_3mf_inch():
    assert convert_from_3mf_unit(1.0, "inch") == pytest.approx(25.4)


def test_convert_from_3mf_foot():
    assert convert_from_3mf_unit(1.0, "foot") == pytest.approx(304.8)


def test_convert_from_3mf_meter():
    assert convert_from_3mf_unit(1.0, "meter") == pytest.approx(1000.0)


def test_convert_from_3mf_micrometer():
    assert convert_from_3mf_unit(1000.0, "micrometer") == pytest.approx(1.0)


def test_convert_from_3mf_unknown_unit_raises():
    with pytest.raises(ValueError, match="Unknown 3MF unit"):
        convert_from_3mf_unit(1.0, "cubits")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_units.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.units'`

- [ ] **Step 3: Implement unit conversion**

```python
# backend/app/units.py
"""Unit conversion utilities.

Internally all dimensions are stored in millimeters. Convert from the 3MF file's
declared unit on parse, and convert to inches for lumber matching / display.
"""

_3MF_UNIT_TO_MM = {
    "millimeter": 1.0,
    "centimeter": 10.0,
    "meter": 1000.0,
    "inch": 25.4,
    "foot": 304.8,
    "micrometer": 0.001,
}


def convert_from_3mf_unit(value: float, unit: str) -> float:
    """Convert a value from a 3MF unit to millimeters."""
    factor = _3MF_UNIT_TO_MM.get(unit)
    if factor is None:
        raise ValueError(f"Unknown 3MF unit: {unit!r}")
    return value * factor


def mm_to_inches(mm: float) -> float:
    """Convert millimeters to inches."""
    return mm / 25.4


def inches_to_mm(inches: float) -> float:
    """Convert inches to millimeters."""
    return inches * 25.4
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_units.py -v
```

Expected: All 8 tests PASS.

- [ ] **Step 5: Write failing tests for Pydantic models**

```python
# backend/tests/test_models.py
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


def test_cost_estimate_total_none_when_any_price_missing():
    items = [
        ShoppingItem(material="4/4 Oak", thickness="4/4", quantity=18.5, unit="BF", unit_price=8.50),
        ShoppingItem(material="3/4 Ply", thickness="3/4\"", quantity=2, unit="sheets", unit_price=None),
    ]
    estimate = CostEstimate(items=items)
    assert estimate.total is None


def test_analyze_request_defaults():
    req = AnalyzeRequest(session_id="abc-123", solid_species="Red Oak", sheet_type="Baltic Birch")
    assert req.all_solid is False
    assert req.display_units == "in"


def test_board_type_enum():
    assert BoardType.SOLID.value == "solid"
    assert BoardType.SHEET.value == "sheet"
    assert BoardType.THICK_STOCK.value == "thick_stock"
```

- [ ] **Step 6: Run tests to verify they fail**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_models.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.models'`

- [ ] **Step 7: Implement Pydantic models**

```python
# backend/app/models.py
from enum import Enum
from pydantic import BaseModel, computed_field
from app.units import mm_to_inches


class BoardType(str, Enum):
    SOLID = "solid"
    SHEET = "sheet"
    THICK_STOCK = "thick_stock"


class Part(BaseModel):
    name: str
    quantity: int
    length_mm: float
    width_mm: float
    thickness_mm: float
    board_type: BoardType
    stock: str
    notes: str

    def display_dimensions(self, units: str) -> str:
        if units == "mm":
            return f"{self.length_mm} × {self.width_mm} × {self.thickness_mm} mm"
        l = round(mm_to_inches(self.length_mm), 2)
        w = round(mm_to_inches(self.width_mm), 2)
        t = round(mm_to_inches(self.thickness_mm), 2)
        return f'{l}" × {w}" × {t}"'


class ShoppingItem(BaseModel):
    material: str
    thickness: str
    quantity: float
    unit: str
    unit_price: float | None = None

    @computed_field
    @property
    def subtotal(self) -> float | None:
        if self.unit_price is None:
            return None
        return self.quantity * self.unit_price


class CostEstimate(BaseModel):
    items: list[ShoppingItem]

    @computed_field
    @property
    def total(self) -> float | None:
        subtotals = [item.subtotal for item in self.items]
        if any(s is None for s in subtotals):
            return None
        return sum(subtotals)


class AnalyzeRequest(BaseModel):
    session_id: str
    solid_species: str
    sheet_type: str
    all_solid: bool = False
    display_units: str = "in"


class PartPreview(BaseModel):
    name: str
    vertex_count: int


class UploadResponse(BaseModel):
    session_id: str
    file_url: str
    parts_preview: list[PartPreview]


class AnalyzeResponse(BaseModel):
    parts: list[Part]
    shopping_list: list[ShoppingItem]
    cost_estimate: CostEstimate
    display_units: str
```

- [ ] **Step 8: Run tests to verify they pass**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_models.py tests/test_units.py -v
```

Expected: All tests PASS.

- [ ] **Step 9: Commit**

```bash
cd backend
git add app/models.py app/units.py tests/test_models.py tests/test_units.py
git commit -m "feat: add Pydantic models and unit conversion utilities"
```

---

## Task 3: Session Management

**Files:**
- Create: `backend/app/session.py`
- Create: `backend/tests/test_session.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_session.py
import os
import time
from pathlib import Path
from app.session import create_session, get_session_path, cleanup_expired_sessions


def test_create_session_returns_uuid(tmp_path):
    session_id = create_session(base_dir=tmp_path)
    assert len(session_id) == 36  # UUID format
    assert (tmp_path / session_id).is_dir()


def test_get_session_path_returns_path(tmp_path):
    session_id = create_session(base_dir=tmp_path)
    path = get_session_path(session_id, base_dir=tmp_path)
    assert path is not None
    assert path.is_dir()


def test_get_session_path_returns_none_for_missing(tmp_path):
    path = get_session_path("nonexistent-id", base_dir=tmp_path)
    assert path is None


def test_cleanup_expired_sessions(tmp_path):
    session_id = create_session(base_dir=tmp_path)
    session_dir = tmp_path / session_id
    # Backdate the directory modification time by 3 hours
    old_time = time.time() - (3 * 3600)
    os.utime(session_dir, (old_time, old_time))

    removed = cleanup_expired_sessions(base_dir=tmp_path, ttl_seconds=7200)
    assert removed == 1
    assert not session_dir.exists()


def test_cleanup_keeps_fresh_sessions(tmp_path):
    session_id = create_session(base_dir=tmp_path)
    removed = cleanup_expired_sessions(base_dir=tmp_path, ttl_seconds=7200)
    assert removed == 0
    assert (tmp_path / session_id).is_dir()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_session.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.session'`

- [ ] **Step 3: Implement session management**

```python
# backend/app/session.py
import shutil
import time
import uuid
from pathlib import Path

DEFAULT_BASE_DIR = Path(__file__).parent.parent / "sessions"
DEFAULT_TTL_SECONDS = 7200  # 2 hours


def create_session(base_dir: Path = DEFAULT_BASE_DIR) -> str:
    """Create a new session directory and return the session ID."""
    session_id = str(uuid.uuid4())
    session_dir = base_dir / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_id


def get_session_path(session_id: str, base_dir: Path = DEFAULT_BASE_DIR) -> Path | None:
    """Return the session directory path, or None if it doesn't exist."""
    session_dir = base_dir / session_id
    if session_dir.is_dir():
        return session_dir
    return None


def cleanup_expired_sessions(
    base_dir: Path = DEFAULT_BASE_DIR,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> int:
    """Remove session directories older than ttl_seconds. Returns count removed."""
    if not base_dir.exists():
        return 0
    now = time.time()
    removed = 0
    for entry in base_dir.iterdir():
        if entry.is_dir():
            mtime = entry.stat().st_mtime
            if now - mtime > ttl_seconds:
                shutil.rmtree(entry)
                removed += 1
    return removed
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_session.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/session.py tests/test_session.py
git commit -m "feat: add session management with UUID temp dirs and TTL cleanup"
```

---

## Task 4: 3MF Parser

**Files:**
- Create: `backend/tests/conftest.py`
- Create: `backend/app/parser/threemf.py`
- Create: `backend/tests/test_parser.py`

- [ ] **Step 1: Write test fixture — programmatic 3MF file builder**

```python
# backend/tests/conftest.py
import io
import zipfile
import pytest
from pathlib import Path


def build_3mf_xml(
    unit: str = "millimeter",
    objects: list[dict] | None = None,
) -> str:
    """Build a minimal 3D/3dmodel.model XML string.

    Each object dict has:
        - id: str
        - name: str (optional)
        - vertices: list of (x, y, z) tuples
        - triangles: list of (v1, v2, v3) tuples
        - transform: str (optional, for build item)
    """
    if objects is None:
        # Default: single 100x50x19 mm box (roughly 4"x2"x3/4")
        objects = [
            {
                "id": "1",
                "name": "TestBox",
                "vertices": [
                    (0, 0, 0), (100, 0, 0), (100, 50, 0), (0, 50, 0),
                    (0, 0, 19), (100, 0, 19), (100, 50, 19), (0, 50, 19),
                ],
                "triangles": [
                    (0, 1, 2), (0, 2, 3),  # bottom
                    (4, 6, 5), (4, 7, 6),  # top
                    (0, 4, 5), (0, 5, 1),  # front
                    (2, 6, 7), (2, 7, 3),  # back
                    (0, 3, 7), (0, 7, 4),  # left
                    (1, 5, 6), (1, 6, 2),  # right
                ],
            }
        ]

    resource_xml = ""
    build_xml = ""
    for obj in objects:
        verts = "\n".join(
            f'          <vertex x="{x}" y="{y}" z="{z}" />'
            for x, y, z in obj["vertices"]
        )
        tris = "\n".join(
            f'          <triangle v1="{v1}" v2="{v2}" v3="{v3}" />'
            for v1, v2, v3 in obj["triangles"]
        )
        name_attr = f' name="{obj["name"]}"' if "name" in obj else ""
        resource_xml += f"""
    <object id="{obj['id']}"{name_attr} type="model">
      <mesh>
        <vertices>
{verts}
        </vertices>
        <triangles>
{tris}
        </triangles>
      </mesh>
    </object>"""

        transform_attr = ""
        if "transform" in obj:
            transform_attr = f' transform="{obj["transform"]}"'
        build_xml += f'    <item objectid="{obj["id"]}"{transform_attr} />\n'

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<model unit="{unit}" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">
  <resources>{resource_xml}
  </resources>
  <build>
{build_xml}  </build>
</model>"""


def build_3mf_bytes(
    unit: str = "millimeter",
    objects: list[dict] | None = None,
) -> bytes:
    """Build a complete 3MF file (ZIP) as bytes."""
    xml_content = build_3mf_xml(unit=unit, objects=objects)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("3D/3dmodel.model", xml_content)
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml" />'
            "</Types>",
        )
    return buf.getvalue()


@pytest.fixture
def simple_box_3mf(tmp_path) -> Path:
    """A 3MF file containing a single 100x50x19mm box."""
    path = tmp_path / "box.3mf"
    path.write_bytes(build_3mf_bytes())
    return path


@pytest.fixture
def multi_part_3mf(tmp_path) -> Path:
    """A 3MF file with two different parts: a wide panel and a narrow rail."""
    objects = [
        {
            "id": "1",
            "name": "Side Panel",
            "vertices": [
                (0, 0, 0), (600, 0, 0), (600, 400, 0), (0, 400, 0),
                (0, 0, 19), (600, 0, 19), (600, 400, 19), (0, 400, 19),
            ],
            "triangles": [
                (0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6),
                (0, 4, 5), (0, 5, 1), (2, 6, 7), (2, 7, 3),
                (0, 3, 7), (0, 7, 4), (1, 5, 6), (1, 6, 2),
            ],
        },
        {
            "id": "2",
            "name": "Rail",
            "vertices": [
                (0, 0, 0), (500, 0, 0), (500, 60, 0), (0, 60, 0),
                (0, 0, 19), (500, 0, 19), (500, 60, 19), (0, 60, 19),
            ],
            "triangles": [
                (0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6),
                (0, 4, 5), (0, 5, 1), (2, 6, 7), (2, 7, 3),
                (0, 3, 7), (0, 7, 4), (1, 5, 6), (1, 6, 2),
            ],
        },
    ]
    path = tmp_path / "multi.3mf"
    path.write_bytes(build_3mf_bytes(objects=objects))
    return path
```

- [ ] **Step 2: Write failing parser tests**

```python
# backend/tests/test_parser.py
import pytest
from pathlib import Path
from tests.conftest import build_3mf_bytes
from app.parser.threemf import parse_3mf, ParsedBody


def test_parse_3mf_returns_unit_and_bodies(simple_box_3mf):
    result = parse_3mf(simple_box_3mf)
    assert result.unit == "millimeter"
    assert len(result.bodies) == 1


def test_parsed_body_has_name(simple_box_3mf):
    result = parse_3mf(simple_box_3mf)
    assert result.bodies[0].name == "TestBox"


def test_parsed_body_has_vertices(simple_box_3mf):
    result = parse_3mf(simple_box_3mf)
    body = result.bodies[0]
    assert body.vertices.shape == (8, 3)


def test_parsed_body_vertices_in_mm(simple_box_3mf):
    result = parse_3mf(simple_box_3mf)
    body = result.bodies[0]
    # Box is 100x50x19mm; max coords should match
    assert body.vertices[:, 0].max() == pytest.approx(100.0)
    assert body.vertices[:, 1].max() == pytest.approx(50.0)
    assert body.vertices[:, 2].max() == pytest.approx(19.0)


def test_parse_inch_units(tmp_path):
    # 4" x 2" x 0.75" box in inches
    objects = [
        {
            "id": "1",
            "name": "InchBox",
            "vertices": [
                (0, 0, 0), (4, 0, 0), (4, 2, 0), (0, 2, 0),
                (0, 0, 0.75), (4, 0, 0.75), (4, 2, 0.75), (0, 2, 0.75),
            ],
            "triangles": [
                (0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6),
                (0, 4, 5), (0, 5, 1), (2, 6, 7), (2, 7, 3),
                (0, 3, 7), (0, 7, 4), (1, 5, 6), (1, 6, 2),
            ],
        }
    ]
    path = tmp_path / "inch.3mf"
    path.write_bytes(build_3mf_bytes(unit="inch", objects=objects))
    result = parse_3mf(path)
    body = result.bodies[0]
    # Should be converted to mm: 4" = 101.6mm
    assert body.vertices[:, 0].max() == pytest.approx(101.6)
    assert body.vertices[:, 2].max() == pytest.approx(19.05)


def test_parse_multi_part(multi_part_3mf):
    result = parse_3mf(multi_part_3mf)
    assert len(result.bodies) == 2
    names = {b.name for b in result.bodies}
    assert names == {"Side Panel", "Rail"}


def test_parse_unnamed_object(tmp_path):
    objects = [
        {
            "id": "1",
            "vertices": [
                (0, 0, 0), (10, 0, 0), (10, 10, 0), (0, 10, 0),
                (0, 0, 10), (10, 0, 10), (10, 10, 10), (0, 10, 10),
            ],
            "triangles": [
                (0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6),
                (0, 4, 5), (0, 5, 1), (2, 6, 7), (2, 7, 3),
                (0, 3, 7), (0, 7, 4), (1, 5, 6), (1, 6, 2),
            ],
        }
    ]
    path = tmp_path / "unnamed.3mf"
    path.write_bytes(build_3mf_bytes(objects=objects))
    result = parse_3mf(path)
    assert result.bodies[0].name == "Part 1"


def test_parse_with_transform(tmp_path):
    # Transform that translates the box by (200, 0, 0)
    # 3MF transform is a 3x4 matrix: "m00 m01 m02 m10 m11 m12 m20 m21 m22 m30 m31 m32"
    # Identity rotation + translation (200, 0, 0):
    objects = [
        {
            "id": "1",
            "name": "Translated",
            "vertices": [
                (0, 0, 0), (100, 0, 0), (100, 50, 0), (0, 50, 0),
                (0, 0, 19), (100, 0, 19), (100, 50, 19), (0, 50, 19),
            ],
            "triangles": [
                (0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6),
                (0, 4, 5), (0, 5, 1), (2, 6, 7), (2, 7, 3),
                (0, 3, 7), (0, 7, 4), (1, 5, 6), (1, 6, 2),
            ],
            "transform": "1 0 0 0 1 0 0 0 1 200 0 0",
        }
    ]
    path = tmp_path / "transformed.3mf"
    path.write_bytes(build_3mf_bytes(objects=objects))
    result = parse_3mf(path)
    body = result.bodies[0]
    # Box should now span x: 200 to 300 (but dimensions are still 100x50x19)
    assert body.vertices[:, 0].min() == pytest.approx(200.0)
    assert body.vertices[:, 0].max() == pytest.approx(300.0)


def test_parse_invalid_file_raises(tmp_path):
    path = tmp_path / "bad.3mf"
    path.write_text("not a zip file")
    with pytest.raises(ValueError, match="Invalid 3MF"):
        parse_3mf(path)
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_parser.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.parser.threemf'`

- [ ] **Step 4: Implement 3MF parser**

```python
# backend/app/parser/threemf.py
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.units import convert_from_3mf_unit

_NS = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}


@dataclass
class ParsedBody:
    name: str
    vertices: np.ndarray  # shape (N, 3), in millimeters
    triangle_count: int


@dataclass
class ParseResult:
    unit: str
    bodies: list[ParsedBody]


def _parse_transform(transform_str: str) -> np.ndarray:
    """Parse a 3MF transform string into a 4x4 matrix.

    3MF format: "m00 m01 m02 m10 m11 m12 m20 m21 m22 m30 m31 m32"
    This is a row-major 3x4 affine matrix (rotation columns + translation row).
    """
    vals = [float(v) for v in transform_str.strip().split()]
    if len(vals) != 12:
        raise ValueError(f"Transform must have 12 values, got {len(vals)}")
    mat = np.eye(4)
    mat[0, 0], mat[0, 1], mat[0, 2] = vals[0], vals[1], vals[2]
    mat[1, 0], mat[1, 1], mat[1, 2] = vals[3], vals[4], vals[5]
    mat[2, 0], mat[2, 1], mat[2, 2] = vals[6], vals[7], vals[8]
    mat[3, 0], mat[3, 1], mat[3, 2] = vals[9], vals[10], vals[11]
    return mat


def parse_3mf(file_path: Path) -> ParseResult:
    """Parse a 3MF file and return extracted bodies with vertices in mm."""
    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            model_xml = zf.read("3D/3dmodel.model")
    except (zipfile.BadZipFile, KeyError) as e:
        raise ValueError(f"Invalid 3MF file: {e}") from e

    root = ET.fromstring(model_xml)
    unit = root.get("unit", "millimeter")

    # Build object lookup: id -> (name, vertices, triangle_count)
    objects: dict[str, tuple[str | None, np.ndarray, int]] = {}
    unnamed_counter = 0

    for obj in root.findall(".//m:object", _NS):
        obj_id = obj.get("id")
        obj_name = obj.get("name")
        mesh = obj.find("m:mesh", _NS)
        if mesh is None:
            continue

        verts_elem = mesh.find("m:vertices", _NS)
        if verts_elem is None:
            continue

        vertices = []
        for v in verts_elem.findall("m:vertex", _NS):
            vertices.append((float(v.get("x")), float(v.get("y")), float(v.get("z"))))

        tri_elem = mesh.find("m:triangles", _NS)
        tri_count = len(tri_elem.findall("m:triangle", _NS)) if tri_elem is not None else 0

        vert_array = np.array(vertices, dtype=np.float64)
        objects[obj_id] = (obj_name, vert_array, tri_count)

    # Process build items (apply transforms)
    bodies: list[ParsedBody] = []
    build = root.find("m:build", _NS)
    items = build.findall("m:item", _NS) if build is not None else []

    for item in items:
        obj_id = item.get("objectid")
        if obj_id not in objects:
            continue

        obj_name, vert_array, tri_count = objects[obj_id]
        verts = vert_array.copy()

        # Apply transform if present
        transform_str = item.get("transform")
        if transform_str:
            mat = _parse_transform(transform_str)
            # Add homogeneous coordinate
            ones = np.ones((verts.shape[0], 1))
            homogeneous = np.hstack([verts, ones])
            # Multiply: each vertex row × transform matrix
            transformed = homogeneous @ mat
            verts = transformed[:, :3]

        # Convert to mm
        for col in range(3):
            verts[:, col] = np.array(
                [convert_from_3mf_unit(v, unit) for v in verts[:, col]]
            )

        # Assign name
        if obj_name is None:
            unnamed_counter += 1
            obj_name = f"Part {unnamed_counter}"

        bodies.append(ParsedBody(name=obj_name, vertices=verts, triangle_count=tri_count))

    return ParseResult(unit=unit, bodies=bodies)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_parser.py -v
```

Expected: All 9 tests PASS.

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/parser/threemf.py tests/conftest.py tests/test_parser.py
git commit -m "feat: add 3MF parser with unit conversion and transform support"
```

---

## Task 5: Geometry Analyzer

**Files:**
- Create: `backend/app/analyzer/geometry.py`
- Create: `backend/tests/test_geometry.py`

- [ ] **Step 1: Write failing tests for bounding box and classification**

```python
# backend/tests/test_geometry.py
import pytest
import numpy as np
from app.analyzer.geometry import compute_dimensions, classify_board_type
from app.models import BoardType


class TestComputeDimensions:
    def test_simple_box(self):
        # 100x50x19mm box
        vertices = np.array([
            [0, 0, 0], [100, 0, 0], [100, 50, 0], [0, 50, 0],
            [0, 0, 19], [100, 0, 19], [100, 50, 19], [0, 50, 19],
        ], dtype=np.float64)
        length, width, thickness = compute_dimensions(vertices)
        assert length == pytest.approx(100.0)
        assert width == pytest.approx(50.0)
        assert thickness == pytest.approx(19.0)

    def test_dimensions_sorted_descending(self):
        # 10x200x50mm — should sort to 200, 50, 10
        vertices = np.array([
            [0, 0, 0], [10, 0, 0], [10, 200, 0], [0, 200, 0],
            [0, 0, 50], [10, 0, 50], [10, 200, 50], [0, 200, 50],
        ], dtype=np.float64)
        length, width, thickness = compute_dimensions(vertices)
        assert length == pytest.approx(200.0)
        assert width == pytest.approx(50.0)
        assert thickness == pytest.approx(10.0)

    def test_offset_box(self):
        # Box from (100,100,100) to (300, 200, 119) → 200x100x19
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
        # 2.5" x 2.5" x 29" — table leg
        board_type, notes = classify_board_type(
            length_in=29.0, width_in=2.5, thickness_in=2.5
        )
        assert board_type == BoardType.THICK_STOCK
        assert "lamination" in notes.lower()

    def test_sheet_good(self):
        # 3/4" x 24" x 30" — cabinet side panel (face area = 720 sq in > 144)
        board_type, notes = classify_board_type(
            length_in=30.0, width_in=24.0, thickness_in=0.75
        )
        assert board_type == BoardType.SHEET

    def test_solid_lumber_narrow(self):
        # 3/4" x 2.5" x 30" — face frame rail
        board_type, notes = classify_board_type(
            length_in=30.0, width_in=2.5, thickness_in=0.75
        )
        assert board_type == BoardType.SOLID
        assert "glue-up" not in notes.lower()

    def test_solid_lumber_wide_glueup(self):
        # 1" x 18" x 30" — wide panel, not thin enough for sheet
        board_type, notes = classify_board_type(
            length_in=30.0, width_in=18.0, thickness_in=1.0
        )
        assert board_type == BoardType.SOLID
        assert "glue-up" in notes.lower()

    def test_solid_narrow_at_boundary(self):
        # 3/4" x 12" x 30" — exactly 12" wide, face area = 360 > 144
        # but width is exactly 12", not > 12" → sheet good rule needs > 12"
        # face area = 360 > 144 sq in, thickness <= 3/4", width = 12" (not > 12")
        # Priority 2 requires width > 12" → falls to priority 4 (otherwise) → solid
        board_type, notes = classify_board_type(
            length_in=30.0, width_in=12.0, thickness_in=0.75
        )
        assert board_type == BoardType.SOLID

    def test_all_solid_override_converts_sheet_to_solid(self):
        # Same as sheet good test, but with all_solid=True
        board_type, notes = classify_board_type(
            length_in=30.0, width_in=24.0, thickness_in=0.75, all_solid=True
        )
        assert board_type == BoardType.SOLID
        assert "glue-up" in notes.lower()

    def test_thin_small_panel_is_solid(self):
        # 1/4" x 14" x 10" — face area = 140 < 144 sq in
        # thickness <= 3/4" AND width > 12" BUT face area <= 1 sq ft
        # Falls to priority 3 (width > 12") → solid with glue-up
        board_type, notes = classify_board_type(
            length_in=10.0, width_in=14.0, thickness_in=0.25
        )
        assert board_type == BoardType.SOLID
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_geometry.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.analyzer.geometry'`

- [ ] **Step 3: Implement geometry analyzer**

```python
# backend/app/analyzer/geometry.py
import numpy as np
from app.models import BoardType

# 1 square foot = 144 square inches
_ONE_SQ_FT_IN = 144.0


def compute_dimensions(vertices: np.ndarray) -> tuple[float, float, float]:
    """Compute axis-aligned bounding box dimensions from vertices (in mm).

    Returns (length, width, thickness) sorted descending.
    """
    mins = vertices.min(axis=0)
    maxs = vertices.max(axis=0)
    dims = maxs - mins
    dims_sorted = sorted(dims, reverse=True)
    return dims_sorted[0], dims_sorted[1], dims_sorted[2]


def classify_board_type(
    length_in: float,
    width_in: float,
    thickness_in: float,
    all_solid: bool = False,
) -> tuple[BoardType, str]:
    """Classify a part into a board type based on dimensions in inches.

    Rules evaluated top-to-bottom, first match wins:
      1. Thickness > 1.5"           → thick stock
      2. Thickness <= 3/4" AND face area > 1 sq ft AND width > 12" → sheet good
      3. Width > 12"                → solid lumber (glue-up needed)
      4. Otherwise                  → solid lumber

    If all_solid is True, sheet goods are reclassified as solid lumber.

    Returns (board_type, notes).
    """
    face_area = length_in * width_in

    # Priority 1: thick stock
    if thickness_in > 1.5:
        return BoardType.THICK_STOCK, "May need lamination"

    # Priority 2: sheet good
    if thickness_in <= 0.75 and face_area > _ONE_SQ_FT_IN and width_in > 12.0:
        if all_solid:
            glue_boards = max(2, int(np.ceil(width_in / 6.0)))
            return BoardType.SOLID, f"Glue-up: {glue_boards} boards (overridden from sheet)"
        return BoardType.SHEET, ""

    # Priority 3: wide solid (glue-up)
    if width_in > 12.0:
        glue_boards = max(2, int(np.ceil(width_in / 6.0)))
        return BoardType.SOLID, f"Glue-up: {glue_boards} boards"

    # Priority 4: standard solid
    return BoardType.SOLID, ""
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_geometry.py -v
```

Expected: All 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/analyzer/geometry.py tests/test_geometry.py
git commit -m "feat: add geometry analyzer with AABB computation and board type classification"
```

---

## Task 6: Material Mapper

**Files:**
- Create: `backend/app/mapper/materials.py`
- Create: `backend/tests/test_materials.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_materials.py
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
        # 0.6" doesn't snap to anything within tolerance
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
        # 1/2" finished → still needs 4/4 rough stock
        assert rough_thickness_for(0.5) == "4/4"

    def test_nonstandard_returns_next_up(self):
        # 1.5" finished → needs 8/4 rough
        assert rough_thickness_for(1.5) == "8/4"


class TestMillingAllowance:
    def test_adds_allowance(self):
        l, w, t = add_milling_allowance(30.0, 5.0, 0.75)
        assert l == pytest.approx(31.0)    # +1"
        assert w == pytest.approx(5.5)     # +0.5"
        assert t == pytest.approx(1.0)     # +0.25"


class TestBoardFeet:
    def test_one_board_foot(self):
        # 1" x 12" x 12" = 1 BF
        assert calculate_board_feet(1.0, 12.0, 12.0) == pytest.approx(1.0)

    def test_typical_board(self):
        # 1" x 6" x 96" = 4 BF
        assert calculate_board_feet(1.0, 6.0, 96.0) == pytest.approx(4.0)


class TestSheetsNeeded:
    def test_single_small_part(self):
        # One 24x30 part from a 48x96 sheet
        assert calculate_sheets_needed([(24.0, 30.0)]) == 1

    def test_multiple_parts_fit_one_sheet(self):
        # Two small parts
        assert calculate_sheets_needed([(24.0, 30.0), (24.0, 30.0)]) == 1

    def test_needs_two_sheets(self):
        # Parts that exceed one sheet area
        parts = [(48.0, 48.0), (48.0, 48.0), (48.0, 48.0)]
        # 3 × 2304 = 6912 > 4608 (one sheet) → 2 sheets
        assert calculate_sheets_needed(parts) == 2


class TestMapPartToStock:
    def test_solid_lumber_part(self):
        part = Part(
            name="Rail",
            quantity=1,
            length_mm=762.0,     # 30"
            width_mm=63.5,       # 2.5"
            thickness_mm=19.05,  # 0.75"
            board_type=BoardType.SOLID,
            stock="",
            notes="",
        )
        result = map_part_to_stock(part, species="Red Oak")
        assert result.stock == "4/4 Red Oak"
        assert result.board_type == BoardType.SOLID

    def test_sheet_good_part(self):
        part = Part(
            name="Panel",
            quantity=1,
            length_mm=762.0,     # 30"
            width_mm=609.6,      # 24"
            thickness_mm=19.05,  # 0.75"
            board_type=BoardType.SHEET,
            stock="",
            notes="",
        )
        result = map_part_to_stock(part, species="Red Oak", sheet_type="Baltic Birch")
        assert result.stock == '3/4" Baltic Birch'

    def test_thick_stock_part(self):
        part = Part(
            name="Leg",
            quantity=1,
            length_mm=736.6,     # 29"
            width_mm=63.5,       # 2.5"
            thickness_mm=63.5,   # 2.5"
            board_type=BoardType.THICK_STOCK,
            stock="",
            notes="May need lamination",
        )
        result = map_part_to_stock(part, species="Red Oak")
        assert "8/4" in result.stock
        assert "lamination" in result.notes.lower()


class TestAggregateShoppingList:
    def test_aggregates_by_stock(self):
        parts = [
            Part(name="Rail", quantity=2, length_mm=762.0, width_mm=63.5,
                 thickness_mm=19.05, board_type=BoardType.SOLID,
                 stock="4/4 Red Oak", notes=""),
            Part(name="Stile", quantity=2, length_mm=762.0, width_mm=50.8,
                 thickness_mm=19.05, board_type=BoardType.SOLID,
                 stock="4/4 Red Oak", notes=""),
        ]
        items = aggregate_shopping_list(parts)
        # Should combine into one line item for "4/4 Red Oak"
        solid_items = [i for i in items if i.material == "4/4 Red Oak"]
        assert len(solid_items) == 1
        assert solid_items[0].unit == "BF"
        assert solid_items[0].quantity > 0

    def test_separates_solid_and_sheet(self):
        parts = [
            Part(name="Rail", quantity=1, length_mm=762.0, width_mm=63.5,
                 thickness_mm=19.05, board_type=BoardType.SOLID,
                 stock="4/4 Red Oak", notes=""),
            Part(name="Panel", quantity=1, length_mm=762.0, width_mm=609.6,
                 thickness_mm=19.05, board_type=BoardType.SHEET,
                 stock='3/4" Baltic Birch', notes=""),
        ]
        items = aggregate_shopping_list(parts)
        assert len(items) == 2
        materials = {i.material for i in items}
        assert "4/4 Red Oak" in materials
        assert '3/4" Baltic Birch' in materials
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_materials.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.mapper.materials'`

- [ ] **Step 3: Implement material mapper**

```python
# backend/app/mapper/materials.py
import math
from app.models import BoardType, Part, ShoppingItem
from app.units import mm_to_inches

# Standard finished thicknesses (inches) and snap tolerance
_STANDARD_THICKNESSES = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75]
_SNAP_TOLERANCE = 0.0625  # 1/16"

# Finished thickness → rough quarter notation
_FINISHED_TO_ROUGH = {
    0.25: "4/4",
    0.5: "4/4",
    0.75: "4/4",
    1.0: "5/4",
    1.25: "6/4",
    1.5: "8/4",
    1.75: "8/4",
}

# Milling allowances
_MILL_LENGTH = 1.0    # inches
_MILL_WIDTH = 0.5     # inches
_MILL_THICKNESS = 0.25  # inches

# Standard sheet dimensions
_SHEET_WIDTH = 48.0   # inches
_SHEET_LENGTH = 96.0  # inches

# Kerf allowance per cut edge
_KERF = 0.125  # 1/8"


def snap_thickness_to_standard(thickness_in: float) -> float:
    """Snap a thickness to the nearest standard if within tolerance."""
    for std in _STANDARD_THICKNESSES:
        if abs(thickness_in - std) <= _SNAP_TOLERANCE:
            return std
    return thickness_in


def rough_thickness_for(finished_in: float) -> str:
    """Return the rough quarter notation for a finished thickness."""
    # Find the smallest rough stock that works
    for finished, rough in sorted(_FINISHED_TO_ROUGH.items()):
        if finished >= finished_in:
            return rough
    return "8/4"  # default to thickest


def add_milling_allowance(
    length_in: float, width_in: float, thickness_in: float
) -> tuple[float, float, float]:
    """Add milling allowances to finished dimensions."""
    return (
        length_in + _MILL_LENGTH,
        width_in + _MILL_WIDTH,
        thickness_in + _MILL_THICKNESS,
    )


def calculate_board_feet(thickness_in: float, width_in: float, length_in: float) -> float:
    """Calculate board feet: (T × W × L) / 144."""
    return (thickness_in * width_in * length_in) / 144.0


def calculate_sheets_needed(parts: list[tuple[float, float]]) -> int:
    """Calculate sheets needed for a list of (width, length) parts in inches.

    Naive: sum area / sheet area, rounded up.
    """
    sheet_area = _SHEET_WIDTH * _SHEET_LENGTH
    total_area = sum(w * l for w, l in parts)
    return max(1, math.ceil(total_area / sheet_area))


def map_part_to_stock(
    part: Part,
    species: str = "",
    sheet_type: str = "",
) -> Part:
    """Fill in the stock field for a part based on its classification."""
    thickness_in = mm_to_inches(part.thickness_mm)
    snapped = snap_thickness_to_standard(thickness_in)

    if part.board_type == BoardType.SHEET:
        stock = f'{snapped}" {sheet_type}' if sheet_type else f'{snapped}" plywood'
        return part.model_copy(update={"stock": stock})

    if part.board_type == BoardType.THICK_STOCK:
        rough = "8/4"  # thick stock always needs the thickest available
        stock = f"{rough} {species}" if species else f"{rough} hardwood"
        notes = part.notes if part.notes else "May need lamination"
        return part.model_copy(update={"stock": stock, "notes": notes})

    # Solid lumber
    rough = rough_thickness_for(snapped)
    stock = f"{rough} {species}" if species else f"{rough} hardwood"
    return part.model_copy(update={"stock": stock})


def aggregate_shopping_list(parts: list[Part]) -> list[ShoppingItem]:
    """Aggregate parts into shopping list items by stock type."""
    solid_by_stock: dict[str, float] = {}  # stock → total board feet
    sheet_by_stock: dict[str, list[tuple[float, float]]] = {}  # stock → [(w, l), ...]

    for part in parts:
        if part.board_type in (BoardType.SOLID, BoardType.THICK_STOCK):
            thickness_in = mm_to_inches(part.thickness_mm)
            width_in = mm_to_inches(part.width_mm)
            length_in = mm_to_inches(part.length_mm)
            _, w_rough, t_rough = add_milling_allowance(length_in, width_in, thickness_in)
            l_rough = length_in + _MILL_LENGTH

            bf = calculate_board_feet(t_rough, w_rough, l_rough) * part.quantity
            solid_by_stock[part.stock] = solid_by_stock.get(part.stock, 0.0) + bf
        else:
            width_in = mm_to_inches(part.width_mm) + 2 * _KERF
            length_in = mm_to_inches(part.length_mm) + 2 * _KERF
            sheet_parts = sheet_by_stock.setdefault(part.stock, [])
            for _ in range(part.quantity):
                sheet_parts.append((width_in, length_in))

    items: list[ShoppingItem] = []
    for stock, bf in solid_by_stock.items():
        thickness = stock.split()[0] if stock else ""
        items.append(ShoppingItem(
            material=stock,
            thickness=thickness,
            quantity=round(bf, 1),
            unit="BF",
        ))

    for stock, part_dims in sheet_by_stock.items():
        thickness = stock.split('"')[0] + '"' if '"' in stock else ""
        sheets = calculate_sheets_needed(part_dims)
        items.append(ShoppingItem(
            material=stock,
            thickness=thickness,
            quantity=float(sheets),
            unit="sheets",
        ))

    return items
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_materials.py -v
```

Expected: All 16 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/mapper/materials.py tests/test_materials.py
git commit -m "feat: add material mapper with thickness snapping, board feet, and shopping list aggregation"
```

---

## Task 7: Supplier Module

**Files:**
- Create: `backend/app/suppliers/base.py`
- Create: `backend/app/suppliers/registry.py`
- Create: `backend/app/suppliers/woodworkers_source.py`
- Create: `backend/tests/test_supplier.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_supplier.py
import json
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.suppliers.base import SupplierBase, Product
from app.suppliers.registry import get_supplier, list_suppliers
from app.suppliers.woodworkers_source import WoodworkersSourceSupplier


class TestSupplierBase:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            SupplierBase()


class TestRegistry:
    def test_list_suppliers_includes_woodworkers_source(self):
        names = list_suppliers()
        assert "woodworkers_source" in names

    def test_get_supplier_returns_instance(self):
        supplier = get_supplier("woodworkers_source")
        assert isinstance(supplier, SupplierBase)

    def test_get_unknown_supplier_raises(self):
        with pytest.raises(KeyError):
            get_supplier("nonexistent")


class TestWoodworkersSource:
    def test_get_species_list(self):
        supplier = WoodworkersSourceSupplier(cache_dir=None)
        species = supplier.get_species_list()
        assert len(species) > 0
        assert "Red Oak" in species

    def test_get_sheet_types(self):
        supplier = WoodworkersSourceSupplier(cache_dir=None)
        types = supplier.get_sheet_types()
        assert len(types) > 0
        assert "Baltic Birch" in types

    def test_get_price_returns_value(self):
        supplier = WoodworkersSourceSupplier(cache_dir=None)
        price = supplier.get_price("Red Oak", "4/4", 10.0)
        assert price is not None
        assert price > 0

    def test_get_sheet_price_returns_value(self):
        supplier = WoodworkersSourceSupplier(cache_dir=None)
        price = supplier.get_sheet_price("Baltic Birch", '3/4"')
        assert price is not None
        assert price > 0

    def test_get_catalog_returns_products(self):
        supplier = WoodworkersSourceSupplier(cache_dir=None)
        catalog = supplier.get_catalog()
        assert len(catalog) > 0
        assert all(isinstance(p, Product) for p in catalog)

    def test_cache_saves_and_loads(self, tmp_path):
        supplier = WoodworkersSourceSupplier(cache_dir=tmp_path)
        # First call populates cache
        catalog1 = supplier.get_catalog()
        cache_file = tmp_path / "woodworkers_source_catalog.json"
        assert cache_file.exists()

        # Second call reads from cache
        supplier2 = WoodworkersSourceSupplier(cache_dir=tmp_path)
        catalog2 = supplier2.get_catalog()
        assert len(catalog2) == len(catalog1)

    def test_unknown_species_returns_none(self):
        supplier = WoodworkersSourceSupplier(cache_dir=None)
        price = supplier.get_price("Unicorn Wood", "4/4", 10.0)
        assert price is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_supplier.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.suppliers.base'`

- [ ] **Step 3: Implement supplier base**

```python
# backend/app/suppliers/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Product:
    name: str
    species: str
    thickness: str
    price_per_unit: float
    unit: str  # "BF" or "sheet"
    category: str  # "solid" or "sheet"


class SupplierBase(ABC):
    """Abstract interface for lumber suppliers."""

    @abstractmethod
    def get_catalog(self) -> list[Product]:
        """Available lumber and sheet goods with dimensions and prices."""

    @abstractmethod
    def get_price(self, species: str, thickness: str, board_feet: float) -> float | None:
        """Price for a solid lumber request. Returns None if unavailable."""

    @abstractmethod
    def get_sheet_price(self, product_type: str, thickness: str) -> float | None:
        """Price for a sheet good. Returns None if unavailable."""

    @abstractmethod
    def get_species_list(self) -> list[str]:
        """Available lumber species."""

    @abstractmethod
    def get_sheet_types(self) -> list[str]:
        """Available sheet good types."""
```

- [ ] **Step 4: Implement Woodworkers Source supplier with static baseline prices**

The initial implementation uses a static price table as a baseline. The scraper that fetches live prices from woodworkerssource.com is a follow-up enhancement — it depends on their current site structure and needs careful testing against live HTML. Starting with known-good static data lets us build and test the full pipeline end-to-end.

```python
# backend/app/suppliers/woodworkers_source.py
import json
import time
from pathlib import Path
from app.suppliers.base import SupplierBase, Product

# Static baseline prices ($/BF for solid, $/sheet for sheet goods)
# Source: woodworkerssource.com approximate retail prices as of 2026-04
_SOLID_PRICES: dict[str, dict[str, float]] = {
    "Red Oak": {"4/4": 8.50, "5/4": 9.75, "6/4": 10.50, "8/4": 11.00},
    "White Oak": {"4/4": 9.00, "5/4": 10.25, "6/4": 11.50, "8/4": 12.50},
    "Walnut": {"4/4": 13.00, "5/4": 14.50, "6/4": 15.50, "8/4": 17.00},
    "Hard Maple": {"4/4": 8.75, "5/4": 10.00, "6/4": 11.00, "8/4": 12.00},
    "Cherry": {"4/4": 10.50, "5/4": 11.75, "6/4": 12.50, "8/4": 14.00},
    "Poplar": {"4/4": 5.50, "5/4": 6.25, "6/4": 7.00, "8/4": 7.75},
    "Ash": {"4/4": 7.50, "5/4": 8.50, "6/4": 9.50, "8/4": 10.50},
    "Sapele": {"4/4": 11.00, "5/4": 12.50, "6/4": 13.50, "8/4": 15.00},
}

_SHEET_PRICES: dict[str, dict[str, float]] = {
    "Baltic Birch": {'1/4"': 45.00, '1/2"': 55.00, '3/4"': 72.00},
    "Red Oak Veneer Ply": {'1/4"': 38.00, '1/2"': 52.00, '3/4"': 65.00},
    "Walnut Veneer Ply": {'1/4"': 55.00, '1/2"': 70.00, '3/4"': 85.00},
    "Maple Veneer Ply": {'1/4"': 40.00, '1/2"': 54.00, '3/4"': 68.00},
    "Cherry Veneer Ply": {'1/4"': 48.00, '1/2"': 62.00, '3/4"': 78.00},
    "MDF": {'1/4"': 22.00, '1/2"': 30.00, '3/4"': 38.00},
    "Melamine": {'1/2"': 35.00, '3/4"': 45.00},
}

_CACHE_TTL = 86400  # 24 hours


class WoodworkersSourceSupplier(SupplierBase):
    """Supplier backed by Woodworkers Source pricing.

    Uses static baseline prices. A future enhancement will scrape live prices
    from woodworkerssource.com and cache them.
    """

    def __init__(self, cache_dir: Path | None = None):
        self._cache_dir = cache_dir
        self._catalog: list[Product] | None = None

    def _cache_path(self) -> Path | None:
        if self._cache_dir is None:
            return None
        return self._cache_dir / "woodworkers_source_catalog.json"

    def _load_cache(self) -> list[Product] | None:
        path = self._cache_path()
        if path is None or not path.exists():
            return None
        data = json.loads(path.read_text())
        if time.time() - data.get("timestamp", 0) > _CACHE_TTL:
            return None
        return [Product(**p) for p in data["products"]]

    def _save_cache(self, products: list[Product]) -> None:
        path = self._cache_path()
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "timestamp": time.time(),
            "products": [
                {
                    "name": p.name,
                    "species": p.species,
                    "thickness": p.thickness,
                    "price_per_unit": p.price_per_unit,
                    "unit": p.unit,
                    "category": p.category,
                }
                for p in products
            ],
        }
        path.write_text(json.dumps(data))

    def _build_catalog(self) -> list[Product]:
        products: list[Product] = []
        for species, thicknesses in _SOLID_PRICES.items():
            for thickness, price in thicknesses.items():
                products.append(Product(
                    name=f"{thickness} {species}",
                    species=species,
                    thickness=thickness,
                    price_per_unit=price,
                    unit="BF",
                    category="solid",
                ))
        for sheet_type, thicknesses in _SHEET_PRICES.items():
            for thickness, price in thicknesses.items():
                products.append(Product(
                    name=f"{thickness} {sheet_type}",
                    species=sheet_type,
                    thickness=thickness,
                    price_per_unit=price,
                    unit="sheet",
                    category="sheet",
                ))
        return products

    def get_catalog(self) -> list[Product]:
        if self._catalog is not None:
            return self._catalog
        cached = self._load_cache()
        if cached is not None:
            self._catalog = cached
            return cached
        products = self._build_catalog()
        self._save_cache(products)
        self._catalog = products
        return products

    def get_price(self, species: str, thickness: str, board_feet: float) -> float | None:
        prices = _SOLID_PRICES.get(species)
        if prices is None:
            return None
        per_bf = prices.get(thickness)
        if per_bf is None:
            return None
        return round(per_bf * board_feet, 2)

    def get_sheet_price(self, product_type: str, thickness: str) -> float | None:
        prices = _SHEET_PRICES.get(product_type)
        if prices is None:
            return None
        return prices.get(thickness)

    def get_species_list(self) -> list[str]:
        return list(_SOLID_PRICES.keys())

    def get_sheet_types(self) -> list[str]:
        return list(_SHEET_PRICES.keys())
```

- [ ] **Step 5: Implement supplier registry**

```python
# backend/app/suppliers/registry.py
from app.suppliers.base import SupplierBase
from app.suppliers.woodworkers_source import WoodworkersSourceSupplier

_SUPPLIERS: dict[str, type[SupplierBase]] = {
    "woodworkers_source": WoodworkersSourceSupplier,
}

_instances: dict[str, SupplierBase] = {}


def get_supplier(name: str) -> SupplierBase:
    """Get a supplier instance by name. Raises KeyError if not found."""
    if name not in _SUPPLIERS:
        raise KeyError(f"Unknown supplier: {name!r}")
    if name not in _instances:
        _instances[name] = _SUPPLIERS[name]()
    return _instances[name]


def list_suppliers() -> list[str]:
    """List registered supplier names."""
    return list(_SUPPLIERS.keys())
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_supplier.py -v
```

Expected: All 10 tests PASS.

- [ ] **Step 7: Commit**

```bash
cd backend
git add app/suppliers/base.py app/suppliers/registry.py \
  app/suppliers/woodworkers_source.py tests/test_supplier.py
git commit -m "feat: add supplier module with Woodworkers Source static pricing and JSON cache"
```

---

## Task 8: FastAPI Routes

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/tests/test_routes.py`

- [ ] **Step 1: Write failing integration tests**

```python
# backend/tests/test_routes.py
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from tests.conftest import build_3mf_bytes


@pytest.fixture
def client(tmp_path):
    """Create a test client with a temp session directory."""
    # Patch session base dir before importing app
    from app import session as session_mod
    original = session_mod.DEFAULT_BASE_DIR
    session_mod.DEFAULT_BASE_DIR = tmp_path

    from app.main import app
    yield TestClient(app)

    session_mod.DEFAULT_BASE_DIR = original


class TestUpload:
    def test_upload_valid_3mf(self, client):
        data = build_3mf_bytes()
        response = client.post(
            "/api/upload",
            files={"file": ("test.3mf", data, "application/octet-stream")},
        )
        assert response.status_code == 200
        body = response.json()
        assert "session_id" in body
        assert "file_url" in body
        assert len(body["parts_preview"]) == 1
        assert body["parts_preview"][0]["name"] == "TestBox"

    def test_upload_invalid_file(self, client):
        response = client.post(
            "/api/upload",
            files={"file": ("test.3mf", b"not a zip", "application/octet-stream")},
        )
        assert response.status_code == 400

    def test_upload_wrong_extension(self, client):
        data = build_3mf_bytes()
        response = client.post(
            "/api/upload",
            files={"file": ("test.stl", data, "application/octet-stream")},
        )
        assert response.status_code == 400


class TestAnalyze:
    def _upload(self, client) -> str:
        data = build_3mf_bytes()
        resp = client.post(
            "/api/upload",
            files={"file": ("test.3mf", data, "application/octet-stream")},
        )
        return resp.json()["session_id"]

    def test_analyze_returns_parts(self, client):
        session_id = self._upload(client)
        response = client.post("/api/analyze", json={
            "session_id": session_id,
            "solid_species": "Red Oak",
            "sheet_type": "Baltic Birch",
        })
        assert response.status_code == 200
        body = response.json()
        assert len(body["parts"]) == 1
        assert body["parts"][0]["name"] == "TestBox"
        assert body["parts"][0]["board_type"] == "solid"

    def test_analyze_returns_shopping_list(self, client):
        session_id = self._upload(client)
        response = client.post("/api/analyze", json={
            "session_id": session_id,
            "solid_species": "Red Oak",
            "sheet_type": "Baltic Birch",
        })
        body = response.json()
        assert len(body["shopping_list"]) > 0

    def test_analyze_returns_cost_estimate(self, client):
        session_id = self._upload(client)
        response = client.post("/api/analyze", json={
            "session_id": session_id,
            "solid_species": "Red Oak",
            "sheet_type": "Baltic Birch",
        })
        body = response.json()
        assert "cost_estimate" in body
        assert "total" in body["cost_estimate"]

    def test_analyze_invalid_session(self, client):
        response = client.post("/api/analyze", json={
            "session_id": "nonexistent",
            "solid_species": "Red Oak",
            "sheet_type": "Baltic Birch",
        })
        assert response.status_code == 404

    def test_analyze_with_display_units_mm(self, client):
        session_id = self._upload(client)
        response = client.post("/api/analyze", json={
            "session_id": session_id,
            "solid_species": "Red Oak",
            "sheet_type": "Baltic Birch",
            "display_units": "mm",
        })
        assert response.status_code == 200
        body = response.json()
        assert body["display_units"] == "mm"


class TestFileServing:
    def test_serve_uploaded_file(self, client):
        data = build_3mf_bytes()
        resp = client.post(
            "/api/upload",
            files={"file": ("test.3mf", data, "application/octet-stream")},
        )
        file_url = resp.json()["file_url"]
        response = client.get(file_url)
        assert response.status_code == 200

    def test_serve_missing_file_404(self, client):
        response = client.get("/api/files/nonexistent/test.3mf")
        assert response.status_code == 404


class TestCatalogEndpoints:
    def test_get_species(self, client):
        response = client.get("/api/species")
        assert response.status_code == 200
        species = response.json()
        assert "Red Oak" in species

    def test_get_sheet_types(self, client):
        response = client.get("/api/sheet-types")
        assert response.status_code == 200
        types = response.json()
        assert "Baltic Birch" in types
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_routes.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 3: Implement FastAPI app**

```python
# backend/app/main.py
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    CostEstimate,
    Part,
    PartPreview,
    ShoppingItem,
    UploadResponse,
)
from app.parser.threemf import parse_3mf
from app.analyzer.geometry import compute_dimensions, classify_board_type
from app.mapper.materials import map_part_to_stock, aggregate_shopping_list
from app.session import create_session, get_session_path, cleanup_expired_sessions
from app.suppliers.registry import get_supplier
from app.units import mm_to_inches

app = FastAPI(title="Cut List Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_cleanup():
    cleanup_expired_sessions()


@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".3mf"):
        raise HTTPException(status_code=400, detail="Only .3mf files are accepted")

    session_id = create_session()
    session_dir = get_session_path(session_id)

    file_path = session_dir / file.filename
    content = await file.read()
    file_path.write_bytes(content)

    try:
        result = parse_3mf(file_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    previews = [
        PartPreview(name=body.name, vertex_count=body.vertices.shape[0])
        for body in result.bodies
    ]

    return UploadResponse(
        session_id=session_id,
        file_url=f"/api/files/{session_id}/{file.filename}",
        parts_preview=previews,
    )


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    session_dir = get_session_path(request.session_id)
    if session_dir is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Find the 3mf file in the session
    threemf_files = list(session_dir.glob("*.3mf"))
    if not threemf_files:
        raise HTTPException(status_code=404, detail="No 3MF file in session")

    result = parse_3mf(threemf_files[0])

    # Analyze each body
    parts: list[Part] = []
    seen_geometries: dict[str, int] = {}  # geometry hash → index in parts

    for body in result.bodies:
        length_mm, width_mm, thickness_mm = compute_dimensions(body.vertices)
        length_in = mm_to_inches(length_mm)
        width_in = mm_to_inches(width_mm)
        thickness_in = mm_to_inches(thickness_mm)

        board_type, notes = classify_board_type(
            length_in, width_in, thickness_in, all_solid=request.all_solid
        )

        # Simple duplicate detection: round dimensions and hash
        geo_key = f"{round(length_mm, 1)}x{round(width_mm, 1)}x{round(thickness_mm, 1)}"
        if geo_key in seen_geometries:
            idx = seen_geometries[geo_key]
            parts[idx] = parts[idx].model_copy(
                update={"quantity": parts[idx].quantity + 1}
            )
            continue

        part = Part(
            name=body.name,
            quantity=1,
            length_mm=round(length_mm, 2),
            width_mm=round(width_mm, 2),
            thickness_mm=round(thickness_mm, 2),
            board_type=board_type,
            stock="",
            notes=notes,
        )
        part = map_part_to_stock(
            part,
            species=request.solid_species,
            sheet_type=request.sheet_type,
        )

        seen_geometries[geo_key] = len(parts)
        parts.append(part)

    # Build shopping list
    shopping_list = aggregate_shopping_list(parts)

    # Look up prices
    supplier = get_supplier("woodworkers_source")
    for i, item in enumerate(shopping_list):
        if item.unit == "BF":
            price = supplier.get_price(request.solid_species, item.thickness, item.quantity)
            if price is not None:
                unit_price = price / item.quantity if item.quantity > 0 else 0
                shopping_list[i] = item.model_copy(update={"unit_price": unit_price})
        else:
            price = supplier.get_sheet_price(request.sheet_type, item.thickness)
            if price is not None:
                shopping_list[i] = item.model_copy(update={"unit_price": price})

    cost_estimate = CostEstimate(items=shopping_list)

    return AnalyzeResponse(
        parts=parts,
        shopping_list=shopping_list,
        cost_estimate=cost_estimate,
        display_units=request.display_units,
    )


@app.get("/api/files/{session_id}/{filename}")
async def serve_file(session_id: str, filename: str):
    session_dir = get_session_path(session_id)
    if session_dir is None:
        raise HTTPException(status_code=404, detail="Session not found")
    file_path = session_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


@app.get("/api/species")
async def get_species():
    supplier = get_supplier("woodworkers_source")
    return supplier.get_species_list()


@app.get("/api/sheet-types")
async def get_sheet_types():
    supplier = get_supplier("woodworkers_source")
    return supplier.get_sheet_types()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_routes.py -v
```

Expected: All 11 tests PASS.

- [ ] **Step 5: Run all backend tests together**

```bash
cd backend && source .venv/bin/activate && pytest -v
```

Expected: All tests PASS (models, units, session, parser, geometry, materials, supplier, routes).

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/main.py tests/test_routes.py
git commit -m "feat: add FastAPI routes for upload, analyze, file serving, and catalog endpoints"
```

---

## Task 9: Frontend Types and API Client

**Files:**
- Create: `frontend/src/lib/types.ts`
- Create: `frontend/src/lib/api.ts`

- [ ] **Step 1: Create TypeScript types**

```typescript
// frontend/src/lib/types.ts

export type BoardType = 'solid' | 'sheet' | 'thick_stock';
export type DisplayUnits = 'in' | 'mm';

export interface PartPreview {
	name: string;
	vertex_count: number;
}

export interface UploadResponse {
	session_id: string;
	file_url: string;
	parts_preview: PartPreview[];
}

export interface Part {
	name: string;
	quantity: number;
	length_mm: number;
	width_mm: number;
	thickness_mm: number;
	board_type: BoardType;
	stock: string;
	notes: string;
}

export interface ShoppingItem {
	material: string;
	thickness: string;
	quantity: number;
	unit: string;
	unit_price: number | null;
	subtotal: number | null;
}

export interface CostEstimate {
	items: ShoppingItem[];
	total: number | null;
}

export interface AnalyzeRequest {
	session_id: string;
	solid_species: string;
	sheet_type: string;
	all_solid?: boolean;
	display_units?: DisplayUnits;
}

export interface AnalyzeResponse {
	parts: Part[];
	shopping_list: ShoppingItem[];
	cost_estimate: CostEstimate;
	display_units: DisplayUnits;
}
```

- [ ] **Step 2: Create API client**

```typescript
// frontend/src/lib/api.ts

import type { UploadResponse, AnalyzeRequest, AnalyzeResponse } from './types';

const BASE = '/api';

export async function uploadFile(file: File): Promise<UploadResponse> {
	const formData = new FormData();
	formData.append('file', file);

	const response = await fetch(`${BASE}/upload`, {
		method: 'POST',
		body: formData,
	});

	if (!response.ok) {
		const detail = await response.json().catch(() => ({ detail: 'Upload failed' }));
		throw new Error(detail.detail || 'Upload failed');
	}

	return response.json();
}

export async function analyze(request: AnalyzeRequest): Promise<AnalyzeResponse> {
	const response = await fetch(`${BASE}/analyze`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(request),
	});

	if (!response.ok) {
		const detail = await response.json().catch(() => ({ detail: 'Analysis failed' }));
		throw new Error(detail.detail || 'Analysis failed');
	}

	return response.json();
}

export async function getSpecies(): Promise<string[]> {
	const response = await fetch(`${BASE}/species`);
	if (!response.ok) throw new Error('Failed to fetch species');
	return response.json();
}

export async function getSheetTypes(): Promise<string[]> {
	const response = await fetch(`${BASE}/sheet-types`);
	if (!response.ok) throw new Error('Failed to fetch sheet types');
	return response.json();
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx svelte-check
```

Expected: No errors in `types.ts` or `api.ts`.

- [ ] **Step 4: Commit**

```bash
cd frontend
git add src/lib/types.ts src/lib/api.ts
git commit -m "feat: add TypeScript types and API client for backend communication"
```

---

## Task 10: Upload Component

**Files:**
- Create: `frontend/src/lib/components/Upload.svelte`

- [ ] **Step 1: Create Upload component**

```svelte
<!-- frontend/src/lib/components/Upload.svelte -->
<script lang="ts">
	import { uploadFile } from '$lib/api';
	import type { UploadResponse } from '$lib/types';

	interface Props {
		onUpload: (result: UploadResponse) => void;
	}

	let { onUpload }: Props = $props();

	let dragOver = $state(false);
	let uploading = $state(false);
	let error = $state('');

	function validateFile(file: File): string | null {
		if (!file.name.toLowerCase().endsWith('.3mf')) {
			return 'Only .3mf files are accepted';
		}
		if (file.size > 50 * 1024 * 1024) {
			return 'File must be under 50MB';
		}
		return null;
	}

	async function handleFile(file: File) {
		error = '';
		const validationError = validateFile(file);
		if (validationError) {
			error = validationError;
			return;
		}

		uploading = true;
		try {
			const result = await uploadFile(file);
			onUpload(result);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Upload failed';
		} finally {
			uploading = false;
		}
	}

	function handleDrop(event: DragEvent) {
		event.preventDefault();
		dragOver = false;
		const file = event.dataTransfer?.files[0];
		if (file) handleFile(file);
	}

	function handleDragOver(event: DragEvent) {
		event.preventDefault();
		dragOver = true;
	}

	function handleDragLeave() {
		dragOver = false;
	}

	function handleInputChange(event: Event) {
		const input = event.target as HTMLInputElement;
		const file = input.files?.[0];
		if (file) handleFile(file);
	}
</script>

<div
	class="border-2 border-dashed rounded-lg p-12 text-center transition-colors cursor-pointer
		{dragOver ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}"
	role="button"
	tabindex="0"
	ondrop={handleDrop}
	ondragover={handleDragOver}
	ondragleave={handleDragLeave}
	onclick={() => document.getElementById('file-input')?.click()}
	onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') document.getElementById('file-input')?.click(); }}
>
	{#if uploading}
		<p class="text-gray-500">Uploading...</p>
	{:else}
		<p class="text-lg text-gray-600 mb-2">Drop .3mf file here</p>
		<p class="text-sm text-gray-400">or click to browse</p>
	{/if}
	<input
		id="file-input"
		type="file"
		accept=".3mf"
		class="hidden"
		onchange={handleInputChange}
	/>
</div>

{#if error}
	<p class="mt-4 text-red-600 text-sm">{error}</p>
{/if}
```

- [ ] **Step 2: Verify it compiles**

```bash
cd frontend && npx svelte-check
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
cd frontend
git add src/lib/components/Upload.svelte
git commit -m "feat: add drag-and-drop Upload component with validation"
```

---

## Task 11: 3D Model Viewer

**Files:**
- Create: `frontend/src/lib/components/ModelViewer.svelte`

- [ ] **Step 1: Create ModelViewer component**

```svelte
<!-- frontend/src/lib/components/ModelViewer.svelte -->
<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import * as THREE from 'three';
	import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
	import { ThreeMFLoader } from 'three/addons/loaders/3MFLoader.js';

	interface Props {
		fileUrl: string;
	}

	let { fileUrl }: Props = $props();

	let container: HTMLDivElement;
	let renderer: THREE.WebGLRenderer;
	let animationId: number;

	onMount(() => {
		const scene = new THREE.Scene();
		scene.background = new THREE.Color(0xf0f0f0);

		const camera = new THREE.PerspectiveCamera(
			45,
			container.clientWidth / container.clientHeight,
			0.1,
			10000,
		);
		camera.position.set(200, 200, 200);

		renderer = new THREE.WebGLRenderer({ antialias: true });
		renderer.setSize(container.clientWidth, container.clientHeight);
		renderer.setPixelRatio(window.devicePixelRatio);
		container.appendChild(renderer.domElement);

		const controls = new OrbitControls(camera, renderer.domElement);
		controls.enableDamping = true;

		// Lighting
		const ambientLight = new THREE.AmbientLight(0x888888);
		scene.add(ambientLight);
		const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
		directionalLight.position.set(1, 1, 1);
		scene.add(directionalLight);

		// Grid
		const grid = new THREE.GridHelper(1000, 20, 0xcccccc, 0xe0e0e0);
		scene.add(grid);

		// Load 3MF
		const loader = new ThreeMFLoader();
		loader.load(fileUrl, (object: THREE.Group) => {
			// Center the model
			const box = new THREE.Box3().setFromObject(object);
			const center = box.getCenter(new THREE.Vector3());
			object.position.sub(center);

			// Set material to a visible default if missing
			object.traverse((child: THREE.Object3D) => {
				if (child instanceof THREE.Mesh && !child.material) {
					child.material = new THREE.MeshPhongMaterial({ color: 0xb88c5a });
				} else if (child instanceof THREE.Mesh) {
					const mat = child.material as THREE.Material;
					if ('color' in mat) {
						(mat as THREE.MeshPhongMaterial).color.set(0xb88c5a);
					}
				}
			});

			scene.add(object);

			// Position camera to fit model
			const size = box.getSize(new THREE.Vector3());
			const maxDim = Math.max(size.x, size.y, size.z);
			camera.position.set(maxDim, maxDim, maxDim);
			controls.target.set(0, 0, 0);
			controls.update();
		});

		function animate() {
			animationId = requestAnimationFrame(animate);
			controls.update();
			renderer.render(scene, camera);
		}
		animate();

		// Handle resize
		const resizeObserver = new ResizeObserver(() => {
			camera.aspect = container.clientWidth / container.clientHeight;
			camera.updateProjectionMatrix();
			renderer.setSize(container.clientWidth, container.clientHeight);
		});
		resizeObserver.observe(container);

		return () => {
			resizeObserver.disconnect();
		};
	});

	onDestroy(() => {
		if (animationId) cancelAnimationFrame(animationId);
		if (renderer) renderer.dispose();
	});
</script>

<div bind:this={container} class="w-full h-80 rounded-lg border border-gray-200 overflow-hidden bg-gray-50"></div>
```

- [ ] **Step 2: Verify it compiles**

```bash
cd frontend && npx svelte-check
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
cd frontend
git add src/lib/components/ModelViewer.svelte
git commit -m "feat: add 3D model viewer with Three.js and OrbitControls"
```

---

## Task 12: Configure Component

**Files:**
- Create: `frontend/src/lib/components/Configure.svelte`

- [ ] **Step 1: Create Configure component**

```svelte
<!-- frontend/src/lib/components/Configure.svelte -->
<script lang="ts">
	import { onMount } from 'svelte';
	import { getSpecies, getSheetTypes } from '$lib/api';
	import type { DisplayUnits } from '$lib/types';

	interface Props {
		onAnalyze: (config: {
			solid_species: string;
			sheet_type: string;
			all_solid: boolean;
			display_units: DisplayUnits;
		}) => void;
		analyzing: boolean;
	}

	let { onAnalyze, analyzing }: Props = $props();

	let speciesList = $state<string[]>([]);
	let sheetTypesList = $state<string[]>([]);
	let solidSpecies = $state('');
	let sheetType = $state('');
	let allSolid = $state(false);
	let displayUnits = $state<DisplayUnits>('in');
	let loading = $state(true);

	onMount(async () => {
		const [species, sheets] = await Promise.all([getSpecies(), getSheetTypes()]);
		speciesList = species;
		sheetTypesList = sheets;
		solidSpecies = species[0] || '';
		sheetType = sheets[0] || '';
		loading = false;
	});

	function handleSubmit() {
		onAnalyze({
			solid_species: solidSpecies,
			sheet_type: sheetType,
			all_solid: allSolid,
			display_units: displayUnits,
		});
	}
</script>

<div class="space-y-4">
	{#if loading}
		<p class="text-gray-500">Loading material options...</p>
	{:else}
		<div>
			<label for="species" class="block text-sm font-medium text-gray-700 mb-1">
				Solid Lumber Species
			</label>
			<select
				id="species"
				bind:value={solidSpecies}
				class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
			>
				{#each speciesList as s}
					<option value={s}>{s}</option>
				{/each}
			</select>
		</div>

		<div>
			<label for="sheet-type" class="block text-sm font-medium text-gray-700 mb-1">
				Sheet Good Type
			</label>
			<select
				id="sheet-type"
				bind:value={sheetType}
				disabled={allSolid}
				class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm
					{allSolid ? 'opacity-50' : ''}"
			>
				{#each sheetTypesList as t}
					<option value={t}>{t}</option>
				{/each}
			</select>
		</div>

		<div class="flex items-center gap-3">
			<label class="relative inline-flex items-center cursor-pointer">
				<input type="checkbox" bind:checked={allSolid} class="sr-only peer" />
				<div class="w-9 h-5 bg-gray-200 peer-focus:outline-none rounded-full peer
					peer-checked:after:translate-x-full after:content-[''] after:absolute
					after:top-[2px] after:start-[2px] after:bg-white after:rounded-full
					after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
			</label>
			<span class="text-sm text-gray-700">All solid lumber (no sheet goods)</span>
		</div>

		<div class="flex items-center gap-3">
			<span class="text-sm text-gray-700">Display Units</span>
			<div class="flex gap-1">
				<button
					class="px-3 py-1 text-sm rounded {displayUnits === 'in'
						? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-600'}"
					onclick={() => (displayUnits = 'in')}
				>
					in
				</button>
				<button
					class="px-3 py-1 text-sm rounded {displayUnits === 'mm'
						? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-600'}"
					onclick={() => (displayUnits = 'mm')}
				>
					mm
				</button>
			</div>
		</div>

		<button
			onclick={handleSubmit}
			disabled={analyzing}
			class="w-full bg-blue-600 text-white py-2 px-4 rounded-md text-sm font-medium
				hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
		>
			{analyzing ? 'Analyzing...' : 'Analyze'}
		</button>
	{/if}
</div>
```

- [ ] **Step 2: Verify it compiles**

```bash
cd frontend && npx svelte-check
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
cd frontend
git add src/lib/components/Configure.svelte
git commit -m "feat: add Configure component with species, sheet type, toggles, and units"
```

---

## Task 13: Results Component

**Files:**
- Create: `frontend/src/lib/components/Results.svelte`

- [ ] **Step 1: Create Results component**

```svelte
<!-- frontend/src/lib/components/Results.svelte -->
<script lang="ts">
	import type { AnalyzeResponse, Part, DisplayUnits } from '$lib/types';

	interface Props {
		result: AnalyzeResponse;
	}

	let { result }: Props = $props();

	let activeTab = $state<'parts' | 'shopping' | 'cost'>('parts');

	function formatDimensions(part: Part, units: DisplayUnits): string {
		if (units === 'mm') {
			return `${part.length_mm} × ${part.width_mm} × ${part.thickness_mm} mm`;
		}
		const l = (part.length_mm / 25.4).toFixed(2);
		const w = (part.width_mm / 25.4).toFixed(2);
		const t = (part.thickness_mm / 25.4).toFixed(2);
		return `${l}" × ${w}" × ${t}"`;
	}

	function formatPrice(value: number | null): string {
		if (value === null) return '—';
		return `$${value.toFixed(2)}`;
	}

	function exportCsv() {
		const lines = ['Part,Qty,Dimensions,Type,Stock,Notes'];
		for (const part of result.parts) {
			const dims = formatDimensions(part, result.display_units);
			lines.push(
				`"${part.name}",${part.quantity},"${dims}",${part.board_type},"${part.stock}","${part.notes}"`,
			);
		}
		lines.push('');
		lines.push('Material,Thickness,Qty,Unit,Unit Price,Subtotal');
		for (const item of result.shopping_list) {
			lines.push(
				`"${item.material}","${item.thickness}",${item.quantity},${item.unit},${formatPrice(item.unit_price)},${formatPrice(item.subtotal)}`,
			);
		}
		if (result.cost_estimate.total !== null) {
			lines.push(`,,,,Total,${formatPrice(result.cost_estimate.total)}`);
		}

		const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = 'cut-list.csv';
		a.click();
		URL.revokeObjectURL(url);
	}
</script>

<div>
	<!-- Tab bar -->
	<div class="flex gap-2 mb-4">
		<button
			class="px-4 py-2 text-sm rounded-t {activeTab === 'parts'
				? 'bg-white border border-b-0 border-gray-300 font-medium'
				: 'bg-gray-100 text-gray-500'}"
			onclick={() => (activeTab = 'parts')}
		>
			Parts List
		</button>
		<button
			class="px-4 py-2 text-sm rounded-t {activeTab === 'shopping'
				? 'bg-white border border-b-0 border-gray-300 font-medium'
				: 'bg-gray-100 text-gray-500'}"
			onclick={() => (activeTab = 'shopping')}
		>
			Shopping List
		</button>
		<button
			class="px-4 py-2 text-sm rounded-t {activeTab === 'cost'
				? 'bg-white border border-b-0 border-gray-300 font-medium'
				: 'bg-gray-100 text-gray-500'}"
			onclick={() => (activeTab = 'cost')}
		>
			Cost Estimate
		</button>
	</div>

	<!-- Parts List Tab -->
	{#if activeTab === 'parts'}
		<div class="overflow-x-auto">
			<table class="w-full text-sm">
				<thead>
					<tr class="border-b border-gray-300 text-left text-gray-600">
						<th class="py-2 pr-4">Part</th>
						<th class="py-2 pr-4">Qty</th>
						<th class="py-2 pr-4">Dimensions</th>
						<th class="py-2 pr-4">Type</th>
						<th class="py-2 pr-4">Stock</th>
						<th class="py-2">Notes</th>
					</tr>
				</thead>
				<tbody>
					{#each result.parts as part}
						<tr class="border-b border-gray-100">
							<td class="py-2 pr-4">{part.name}</td>
							<td class="py-2 pr-4">{part.quantity}</td>
							<td class="py-2 pr-4 font-mono text-xs">
								{formatDimensions(part, result.display_units)}
							</td>
							<td class="py-2 pr-4">
								<span class="px-2 py-0.5 rounded text-xs
									{part.board_type === 'solid' ? 'bg-green-100 text-green-700' :
									 part.board_type === 'sheet' ? 'bg-yellow-100 text-yellow-700' :
									 'bg-purple-100 text-purple-700'}">
									{part.board_type}
								</span>
							</td>
							<td class="py-2 pr-4">{part.stock}</td>
							<td class="py-2 text-gray-500 text-xs">{part.notes || '—'}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}

	<!-- Shopping List Tab -->
	{#if activeTab === 'shopping'}
		<div class="overflow-x-auto">
			<table class="w-full text-sm">
				<thead>
					<tr class="border-b border-gray-300 text-left text-gray-600">
						<th class="py-2 pr-4">Material</th>
						<th class="py-2 pr-4">Thickness</th>
						<th class="py-2 pr-4">Quantity</th>
						<th class="py-2 pr-4">Unit</th>
					</tr>
				</thead>
				<tbody>
					{#each result.shopping_list as item}
						<tr class="border-b border-gray-100">
							<td class="py-2 pr-4">{item.material}</td>
							<td class="py-2 pr-4">{item.thickness}</td>
							<td class="py-2 pr-4">{item.quantity}</td>
							<td class="py-2 pr-4">{item.unit}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}

	<!-- Cost Estimate Tab -->
	{#if activeTab === 'cost'}
		<div class="overflow-x-auto">
			<table class="w-full text-sm">
				<thead>
					<tr class="border-b border-gray-300 text-left text-gray-600">
						<th class="py-2 pr-4">Material</th>
						<th class="py-2 pr-4">Qty</th>
						<th class="py-2 pr-4">Unit Price</th>
						<th class="py-2">Subtotal</th>
					</tr>
				</thead>
				<tbody>
					{#each result.cost_estimate.items as item}
						<tr class="border-b border-gray-100">
							<td class="py-2 pr-4">{item.material}</td>
							<td class="py-2 pr-4">{item.quantity} {item.unit}</td>
							<td class="py-2 pr-4">{formatPrice(item.unit_price)}</td>
							<td class="py-2">{formatPrice(item.subtotal)}</td>
						</tr>
					{/each}
				</tbody>
				<tfoot>
					<tr class="border-t-2 border-gray-300 font-medium">
						<td colspan="3" class="py-2 text-right pr-4">Estimated Total:</td>
						<td class="py-2">{formatPrice(result.cost_estimate.total)}</td>
					</tr>
				</tfoot>
			</table>
		</div>

		{#if result.cost_estimate.total === null}
			<p class="mt-2 text-sm text-amber-600">
				Some prices are unavailable. Total cannot be calculated.
			</p>
		{/if}
	{/if}

	<!-- Action buttons -->
	<div class="flex gap-3 mt-6">
		<button
			onclick={exportCsv}
			class="bg-gray-800 text-white px-4 py-2 rounded text-sm hover:bg-gray-900"
		>
			Export CSV
		</button>
		<button
			onclick={() => window.print()}
			class="bg-gray-200 text-gray-700 px-4 py-2 rounded text-sm hover:bg-gray-300"
		>
			Print
		</button>
	</div>
</div>
```

- [ ] **Step 2: Verify it compiles**

```bash
cd frontend && npx svelte-check
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
cd frontend
git add src/lib/components/Results.svelte
git commit -m "feat: add Results component with parts list, shopping list, cost estimate tabs, and CSV export"
```

---

## Task 14: Main Page

**Files:**
- Modify: `frontend/src/routes/+page.svelte`

- [ ] **Step 1: Wire up the three-step workflow**

```svelte
<!-- frontend/src/routes/+page.svelte -->
<script lang="ts">
	import Upload from '$lib/components/Upload.svelte';
	import ModelViewer from '$lib/components/ModelViewer.svelte';
	import Configure from '$lib/components/Configure.svelte';
	import Results from '$lib/components/Results.svelte';
	import { analyze } from '$lib/api';
	import type { UploadResponse, AnalyzeResponse, DisplayUnits } from '$lib/types';

	let uploadResult = $state<UploadResponse | null>(null);
	let analyzeResult = $state<AnalyzeResponse | null>(null);
	let analyzing = $state(false);
	let error = $state('');
	let status = $state('');

	function handleUpload(result: UploadResponse) {
		uploadResult = result;
		analyzeResult = null;
		error = '';
	}

	async function handleAnalyze(config: {
		solid_species: string;
		sheet_type: string;
		all_solid: boolean;
		display_units: DisplayUnits;
	}) {
		if (!uploadResult) return;

		analyzing = true;
		error = '';
		status = 'Parsing model...';

		try {
			status = 'Analyzing geometry...';
			const result = await analyze({
				session_id: uploadResult.session_id,
				...config,
			});
			status = '';
			analyzeResult = result;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Analysis failed';
			status = '';
		} finally {
			analyzing = false;
		}
	}

	function reset() {
		uploadResult = null;
		analyzeResult = null;
		error = '';
		status = '';
	}
</script>

<div class="min-h-screen bg-gray-50">
	<header class="bg-white border-b border-gray-200 px-6 py-4">
		<div class="max-w-6xl mx-auto flex items-center justify-between">
			<h1 class="text-xl font-semibold text-gray-800">Cut List Generator</h1>
			{#if uploadResult}
				<button onclick={reset} class="text-sm text-gray-500 hover:text-gray-700">
					New Project
				</button>
			{/if}
		</div>
	</header>

	<main class="max-w-6xl mx-auto px-6 py-8">
		{#if !uploadResult}
			<!-- Step 1: Upload -->
			<div class="max-w-lg mx-auto">
				<h2 class="text-lg font-medium text-gray-700 mb-4">Upload a 3MF File</h2>
				<Upload onUpload={handleUpload} />
			</div>
		{:else}
			<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
				<!-- Left: 3D Viewer + Configure -->
				<div class="lg:col-span-1 space-y-6">
					<!-- 3D Viewer -->
					<div>
						<h3 class="text-sm font-medium text-gray-600 mb-2">Model Preview</h3>
						<ModelViewer fileUrl={uploadResult.file_url} />
						<p class="text-xs text-gray-400 mt-1">
							{uploadResult.parts_preview.length} part{uploadResult.parts_preview.length !== 1 ? 's' : ''} detected
						</p>
					</div>

					<!-- Configure -->
					<div>
						<h3 class="text-sm font-medium text-gray-600 mb-2">Material Settings</h3>
						<Configure onAnalyze={handleAnalyze} {analyzing} />
					</div>
				</div>

				<!-- Right: Results -->
				<div class="lg:col-span-2">
					{#if status}
						<div class="flex items-center gap-3 py-12 justify-center text-gray-500">
							<svg class="animate-spin h-5 w-5" viewBox="0 0 24 24">
								<circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" class="opacity-25" />
								<path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" class="opacity-75" />
							</svg>
							<span>{status}</span>
						</div>
					{:else if analyzeResult}
						<Results result={analyzeResult} />
					{:else}
						<div class="text-center py-12 text-gray-400">
							<p>Configure materials and click Analyze to see your cut list.</p>
						</div>
					{/if}

					{#if error}
						<div class="mt-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
							{error}
						</div>
					{/if}
				</div>
			</div>
		{/if}
	</main>
</div>
```

- [ ] **Step 2: Verify it compiles**

```bash
cd frontend && npx svelte-check
```

Expected: No errors.

- [ ] **Step 3: Verify it builds**

```bash
cd frontend && npm run build
```

Expected: Build completes without errors.

- [ ] **Step 4: Commit**

```bash
cd frontend
git add src/routes/+page.svelte src/routes/+layout.svelte
git commit -m "feat: add main page with three-step upload, configure, and results workflow"
```

---

## Task 15: Docker Compose + Dev Scripts

**Files:**
- Create: `docker-compose.yml`
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`

- [ ] **Step 1: Create backend Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create frontend Dockerfile**

```dockerfile
# frontend/Dockerfile
FROM node:22-slim AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:22-slim
WORKDIR /app
COPY --from=build /app/build build/
COPY --from=build /app/package.json .
COPY --from=build /app/node_modules node_modules/

EXPOSE 3000
ENV NODE_ENV=production
CMD ["node", "build"]
```

- [ ] **Step 3: Create docker-compose.yml**

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - backend-sessions:/app/sessions
    environment:
      - PYTHONUNBUFFERED=1

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - ORIGIN=http://localhost:3000
    depends_on:
      - backend

volumes:
  backend-sessions:
```

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml backend/Dockerfile frontend/Dockerfile
git commit -m "feat: add Docker Compose setup for frontend and backend services"
```

---

## Task 16: Integration Smoke Test

**Files:** None new — this verifies everything works together.

- [ ] **Step 1: Start the backend**

```bash
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000 &
```

- [ ] **Step 2: Start the frontend**

```bash
cd frontend && npm run dev &
```

- [ ] **Step 3: Open http://localhost:5173 in a browser**

Verify:
1. Upload page renders with drag-and-drop zone
2. Upload a .3mf file → 3D viewer appears, part count shows, configure panel appears
3. Select species and sheet type → click Analyze
4. Results display with parts list, shopping list, and cost estimate tabs
5. CSV export button downloads a file
6. "New Project" button resets to upload

- [ ] **Step 4: Run all backend tests one final time**

```bash
cd backend && source .venv/bin/activate && pytest -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit any final fixes**

```bash
git add -A && git commit -m "chore: integration smoke test fixes"
```

(Only if Step 3 or 4 required fixes. Skip if everything worked.)
