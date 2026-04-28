# Project Persistence — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let authenticated users save, list, load, and delete projects using Supabase Postgres and Storage.

**Architecture:** Backend CRUD endpoints store analysis results as JSONB in a `projects` table and 3MF files + thumbnails in a `projects` Storage bucket. Frontend gets a "Save Project" button in results, a "My Projects" page with card grid, and project loading via URL query param. All project endpoints require authentication.

**Tech Stack:** supabase-py (already installed) for Postgres queries and Storage operations, SvelteKit for frontend.

**Spec:** `docs/superpowers/specs/2026-04-28-project-persistence-design.md`

**Prerequisites:** The `projects` table, Storage bucket, and RLS policies have been created in the Supabase dashboard per the spec.

---

## File Map

### Backend

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/app/supabase_client.py` | Create | Shared Supabase client singleton (extracted from auth.py) |
| `backend/app/auth.py` | Modify | Import client from supabase_client.py instead of creating its own |
| `backend/app/storage.py` | Create | Upload/delete files in Supabase Storage, generate signed URLs |
| `backend/app/database.py` | Create | CRUD queries for `projects` table |
| `backend/app/models.py` | Modify | Add ProjectCreate, ProjectSummary, ProjectDetail models |
| `backend/app/main.py` | Modify | Add 4 project CRUD endpoints |
| `backend/tests/test_storage.py` | Create | Storage module tests with mocked Supabase |
| `backend/tests/test_database.py` | Create | Database module tests with mocked Supabase |
| `backend/tests/test_routes.py` | Modify | Add project endpoint tests |

### Frontend

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/src/lib/types.ts` | Modify | Add ProjectSummary, ProjectDetail types |
| `frontend/src/lib/api.ts` | Modify | Add saveProject, listProjects, getProject, deleteProject |
| `frontend/src/lib/components/Results.svelte` | Modify | Add "Save Project" button |
| `frontend/src/routes/+page.svelte` | Modify | Save Project wiring + load from ?project={id} |
| `frontend/src/routes/projects/+page.svelte` | Create | My Projects page with card grid |
| `frontend/src/routes/+layout.svelte` | Modify | Add "My Projects" link in header |

---

## Task 1: Shared Supabase Client + Project Models

**Files:**
- Create: `backend/app/supabase_client.py`
- Modify: `backend/app/auth.py`
- Modify: `backend/app/models.py`

- [ ] **Step 1: Create shared Supabase client**

```python
# backend/app/supabase_client.py
"""Shared Supabase client singleton."""

from supabase import create_client, Client
from app.config import SUPABASE_URL, SUPABASE_SERVICE_KEY

_client: Client | None = None


def get_supabase_client() -> Client:
    """Return the Supabase admin client (uses service_role key)."""
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _client
```

- [ ] **Step 2: Update auth.py to use shared client**

Replace the `_supabase_client` variable and `_get_supabase_client` function in `backend/app/auth.py`. Change the imports and client access from:

```python
from supabase import create_client, Client
from app.config import SUPABASE_URL, SUPABASE_SERVICE_KEY

_supabase_client: Client | None = None

def _get_supabase_client() -> Client:
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _supabase_client
```

To:

```python
from app.supabase_client import get_supabase_client as _get_supabase_client
```

Remove the `from supabase import ...` and `from app.config import ...` lines (no longer needed). The rest of auth.py stays the same — `_get_supabase_client()` calls still work.

- [ ] **Step 3: Add project models to models.py**

Add these classes at the end of `backend/app/models.py`:

```python
class ProjectCreate(BaseModel):
    name: str
    filename: str
    session_id: str
    solid_species: str
    sheet_type: str
    all_solid: bool = False
    display_units: str = "in"
    analysis_result: AnalyzeResponse
    thumbnail: str | None = None  # base64 data URL


class ProjectSummary(BaseModel):
    id: str
    name: str
    filename: str
    solid_species: str
    sheet_type: str
    part_count: int
    unique_parts: int
    estimated_cost: float | None
    thumbnail_url: str | None
    created_at: str
    updated_at: str


class ProjectDetail(BaseModel):
    id: str
    name: str
    filename: str
    solid_species: str
    sheet_type: str
    all_solid: bool
    display_units: str
    analysis_result: AnalyzeResponse
    file_url: str
    thumbnail_url: str | None
    created_at: str
    updated_at: str
```

- [ ] **Step 4: Run existing tests to verify refactor didn't break anything**

```bash
cd backend && source .venv/bin/activate && pytest -v
```

Expected: All 122 tests PASS (the auth tests mock `_get_supabase_client` — need to update the mock path).

**If auth tests fail:** Update the mock path in `tests/test_auth.py` from `"app.auth._get_supabase_client"` to `"app.supabase_client.get_supabase_client"`. Actually, since auth.py imports it as `_get_supabase_client`, the mock path depends on where the mock is applied. Check the test and fix the patch target.

- [ ] **Step 5: Commit**

```bash
git add backend/app/supabase_client.py backend/app/auth.py backend/app/models.py
git commit -m "feat: extract shared Supabase client and add project models"
```

---

## Task 2: Storage Module

**Files:**
- Create: `backend/app/storage.py`
- Create: `backend/tests/test_storage.py`

- [ ] **Step 1: Write failing storage tests**

```python
# backend/tests/test_storage.py
import pytest
from unittest.mock import patch, MagicMock
from app.storage import upload_file, delete_files, get_signed_url


class TestUploadFile:
    def test_uploads_bytes_to_path(self):
        mock_client = MagicMock()
        mock_client.storage.from_.return_value.upload.return_value = None

        with patch("app.storage.get_supabase_client", return_value=mock_client):
            upload_file("user-1/proj-1/model.3mf", b"file-content", "application/octet-stream")

        mock_client.storage.from_.assert_called_with("projects")
        mock_client.storage.from_.return_value.upload.assert_called_once()
        call_args = mock_client.storage.from_.return_value.upload.call_args
        assert call_args[0][0] == "user-1/proj-1/model.3mf"
        assert call_args[0][1] == b"file-content"


class TestGetSignedUrl:
    def test_returns_signed_url(self):
        mock_client = MagicMock()
        mock_client.storage.from_.return_value.create_signed_url.return_value = {
            "signedURL": "https://example.com/signed"
        }

        with patch("app.storage.get_supabase_client", return_value=mock_client):
            url = get_signed_url("user-1/proj-1/model.3mf")

        assert url == "https://example.com/signed"

    def test_returns_none_on_error(self):
        mock_client = MagicMock()
        mock_client.storage.from_.return_value.create_signed_url.side_effect = Exception("fail")

        with patch("app.storage.get_supabase_client", return_value=mock_client):
            url = get_signed_url("bad/path")

        assert url is None


class TestDeleteFiles:
    def test_deletes_multiple_paths(self):
        mock_client = MagicMock()
        mock_client.storage.from_.return_value.remove.return_value = None

        with patch("app.storage.get_supabase_client", return_value=mock_client):
            delete_files(["user-1/proj-1/model.3mf", "user-1/proj-1/thumbnail.png"])

        mock_client.storage.from_.return_value.remove.assert_called_once_with(
            ["user-1/proj-1/model.3mf", "user-1/proj-1/thumbnail.png"]
        )
```

- [ ] **Step 2: Implement storage module**

```python
# backend/app/storage.py
"""Supabase Storage operations for project files."""

import logging
from app.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

BUCKET = "projects"


def upload_file(path: str, content: bytes, content_type: str) -> None:
    """Upload a file to the projects bucket."""
    client = get_supabase_client()
    client.storage.from_(BUCKET).upload(
        path, content, file_options={"content-type": content_type}
    )


def get_signed_url(path: str, expires_in: int = 3600) -> str | None:
    """Get a signed URL for a file. Returns None on error."""
    try:
        client = get_supabase_client()
        result = client.storage.from_(BUCKET).create_signed_url(path, expires_in)
        return result.get("signedURL") or result.get("signedUrl")
    except Exception as e:
        logger.warning("Failed to create signed URL for %s: %s", path, e)
        return None


def delete_files(paths: list[str]) -> None:
    """Delete files from the projects bucket."""
    client = get_supabase_client()
    client.storage.from_(BUCKET).remove(paths)
```

- [ ] **Step 3: Run tests**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_storage.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/storage.py backend/tests/test_storage.py
git commit -m "feat: add Supabase Storage module for project files"
```

---

## Task 3: Database Module

**Files:**
- Create: `backend/app/database.py`
- Create: `backend/tests/test_database.py`

- [ ] **Step 1: Write failing database tests**

```python
# backend/tests/test_database.py
import pytest
from unittest.mock import patch, MagicMock
from app.database import create_project, list_projects, get_project, delete_project


class TestCreateProject:
    def test_inserts_and_returns_id(self):
        mock_response = MagicMock()
        mock_response.data = [{"id": "proj-123"}]

        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.return_value = mock_response

        with patch("app.database.get_supabase_client", return_value=mock_client):
            result = create_project(
                user_id="user-1",
                name="Test Project",
                filename="test.3mf",
                solid_species="Red Oak",
                sheet_type="Baltic Birch",
                all_solid=False,
                display_units="in",
                analysis_result={"parts": []},
                file_path="user-1/proj-123/model.3mf",
                thumbnail_path="user-1/proj-123/thumbnail.png",
            )

        assert result == "proj-123"
        mock_client.table.assert_called_with("projects")


class TestListProjects:
    def test_returns_project_rows(self):
        mock_response = MagicMock()
        mock_response.data = [
            {"id": "p1", "name": "Project 1", "created_at": "2026-04-28T00:00:00"},
            {"id": "p2", "name": "Project 2", "created_at": "2026-04-27T00:00:00"},
        ]

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        with patch("app.database.get_supabase_client", return_value=mock_client):
            rows = list_projects("user-1")

        assert len(rows) == 2
        assert rows[0]["id"] == "p1"


class TestGetProject:
    def test_returns_single_project(self):
        mock_response = MagicMock()
        mock_response.data = [{"id": "p1", "name": "Project 1"}]

        mock_client = MagicMock()
        (mock_client.table.return_value
         .select.return_value
         .eq.return_value
         .eq.return_value
         .execute.return_value) = mock_response

        with patch("app.database.get_supabase_client", return_value=mock_client):
            row = get_project("p1", "user-1")

        assert row is not None
        assert row["id"] == "p1"

    def test_returns_none_when_not_found(self):
        mock_response = MagicMock()
        mock_response.data = []

        mock_client = MagicMock()
        (mock_client.table.return_value
         .select.return_value
         .eq.return_value
         .eq.return_value
         .execute.return_value) = mock_response

        with patch("app.database.get_supabase_client", return_value=mock_client):
            row = get_project("nonexistent", "user-1")

        assert row is None


class TestDeleteProject:
    def test_deletes_by_id_and_user(self):
        mock_client = MagicMock()
        mock_client.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()

        with patch("app.database.get_supabase_client", return_value=mock_client):
            delete_project("p1", "user-1")

        mock_client.table.assert_called_with("projects")
```

- [ ] **Step 2: Implement database module**

```python
# backend/app/database.py
"""Supabase Postgres queries for the projects table."""

from typing import Any
from app.supabase_client import get_supabase_client


def create_project(
    user_id: str,
    name: str,
    filename: str,
    solid_species: str,
    sheet_type: str,
    all_solid: bool,
    display_units: str,
    analysis_result: dict,
    file_path: str,
    thumbnail_path: str | None = None,
) -> str:
    """Insert a project row and return the project ID."""
    client = get_supabase_client()
    response = client.table("projects").insert({
        "user_id": user_id,
        "name": name,
        "filename": filename,
        "solid_species": solid_species,
        "sheet_type": sheet_type,
        "all_solid": all_solid,
        "display_units": display_units,
        "analysis_result": analysis_result,
        "file_path": file_path,
        "thumbnail_path": thumbnail_path,
    }).execute()
    return response.data[0]["id"]


def list_projects(user_id: str) -> list[dict[str, Any]]:
    """List all projects for a user, newest first."""
    client = get_supabase_client()
    response = (
        client.table("projects")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data


def get_project(project_id: str, user_id: str) -> dict[str, Any] | None:
    """Get a single project by ID, only if owned by user_id."""
    client = get_supabase_client()
    response = (
        client.table("projects")
        .select("*")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not response.data:
        return None
    return response.data[0]


def delete_project(project_id: str, user_id: str) -> None:
    """Delete a project row (ownership enforced by user_id filter)."""
    client = get_supabase_client()
    (
        client.table("projects")
        .delete()
        .eq("id", project_id)
        .eq("user_id", user_id)
        .execute()
    )
```

- [ ] **Step 3: Run tests**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_database.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/database.py backend/tests/test_database.py
git commit -m "feat: add database module for project CRUD queries"
```

---

## Task 4: Project API Endpoints

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_routes.py`

- [ ] **Step 1: Add project endpoints to main.py**

Add these imports to `backend/app/main.py`:

```python
from app.models import ProjectCreate, ProjectSummary, ProjectDetail
from app.storage import upload_file as storage_upload, get_signed_url, delete_files
from app.database import create_project, list_projects, get_project, delete_project
from app.auth import require_user, get_optional_user
import base64
import uuid
```

Add these endpoints after the existing `/api/report` route:

```python
@app.post("/api/projects", status_code=201)
async def save_project(request: ProjectCreate, user: dict = Depends(require_user)):
    # Verify session has a 3MF file
    session_dir = get_session_path(request.session_id)
    if session_dir is None:
        raise HTTPException(status_code=404, detail="Session not found")
    threemf_files = list(session_dir.glob("*.3mf"))
    if not threemf_files:
        raise HTTPException(status_code=404, detail="No 3MF file in session")

    project_id = str(uuid.uuid4())
    user_id = user["id"]

    # Upload 3MF to storage
    file_path = f"{user_id}/{project_id}/model.3mf"
    file_bytes = threemf_files[0].read_bytes()
    storage_upload(file_path, file_bytes, "application/octet-stream")

    # Upload thumbnail if provided
    thumbnail_path = None
    if request.thumbnail:
        thumbnail_path = f"{user_id}/{project_id}/thumbnail.png"
        # Strip data URL prefix: "data:image/png;base64,..."
        b64_data = request.thumbnail.split(",", 1)[-1]
        thumb_bytes = base64.b64decode(b64_data)
        storage_upload(thumbnail_path, thumb_bytes, "image/png")

    # Save to database
    analysis_dict = request.analysis_result.model_dump(mode="json")
    create_project(
        user_id=user_id,
        name=request.name,
        filename=request.filename,
        solid_species=request.solid_species,
        sheet_type=request.sheet_type,
        all_solid=request.all_solid,
        display_units=request.display_units,
        analysis_result=analysis_dict,
        file_path=file_path,
        thumbnail_path=thumbnail_path,
    )

    return {"id": project_id, "message": "Project saved"}


@app.get("/api/projects")
async def list_user_projects(user: dict = Depends(require_user)):
    rows = list_projects(user["id"])
    summaries = []
    for row in rows:
        analysis = row.get("analysis_result", {})
        parts = analysis.get("parts", [])
        cost_est = analysis.get("cost_estimate", {})

        total_parts = sum(p.get("quantity", 1) for p in parts)
        unique_parts = len(parts)
        estimated_cost = cost_est.get("total")

        thumbnail_url = None
        if row.get("thumbnail_path"):
            thumbnail_url = get_signed_url(row["thumbnail_path"])

        summaries.append(ProjectSummary(
            id=row["id"],
            name=row["name"],
            filename=row["filename"],
            solid_species=row["solid_species"],
            sheet_type=row["sheet_type"],
            part_count=total_parts,
            unique_parts=unique_parts,
            estimated_cost=estimated_cost,
            thumbnail_url=thumbnail_url,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        ))
    return summaries


@app.get("/api/projects/{project_id}")
async def get_user_project(project_id: str, user: dict = Depends(require_user)):
    row = get_project(project_id, user["id"])
    if row is None:
        raise HTTPException(status_code=404, detail="Project not found")

    file_url = get_signed_url(row["file_path"]) or ""
    thumbnail_url = None
    if row.get("thumbnail_path"):
        thumbnail_url = get_signed_url(row["thumbnail_path"])

    analysis = AnalyzeResponse(**row["analysis_result"])

    return ProjectDetail(
        id=row["id"],
        name=row["name"],
        filename=row["filename"],
        solid_species=row["solid_species"],
        sheet_type=row["sheet_type"],
        all_solid=row["all_solid"],
        display_units=row["display_units"],
        analysis_result=analysis,
        file_url=file_url,
        thumbnail_url=thumbnail_url,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@app.delete("/api/projects/{project_id}", status_code=204)
async def delete_user_project(project_id: str, user: dict = Depends(require_user)):
    row = get_project(project_id, user["id"])
    if row is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Delete storage files
    paths_to_delete = [row["file_path"]]
    if row.get("thumbnail_path"):
        paths_to_delete.append(row["thumbnail_path"])
    delete_files(paths_to_delete)

    # Delete database row
    delete_project(project_id, user["id"])
```

- [ ] **Step 2: Add project route tests**

Add to `backend/tests/test_routes.py` (uses the existing `auth_client` fixture which overrides auth):

```python
class TestProjects:
    def _upload_and_analyze(self, client) -> tuple[str, dict]:
        """Upload a 3MF and return (session_id, analysis_result)."""
        data = build_3mf_bytes()
        resp = client.post("/api/upload", files={"file": ("test.3mf", data, "application/octet-stream")})
        session_id = resp.json()["session_id"]
        resp2 = client.post("/api/analyze", json={
            "session_id": session_id, "solid_species": "Red Oak", "sheet_type": "Baltic Birch"
        })
        return session_id, resp2.json()

    @patch("app.main.storage_upload")
    @patch("app.main.create_project")
    def test_save_project(self, mock_create, mock_upload, auth_client):
        mock_create.return_value = "proj-123"
        session_id, analysis = self._upload_and_analyze(auth_client)
        response = auth_client.post("/api/projects", json={
            "name": "Test Project",
            "filename": "test.3mf",
            "session_id": session_id,
            "solid_species": "Red Oak",
            "sheet_type": "Baltic Birch",
            "analysis_result": analysis,
        })
        assert response.status_code == 201
        assert "id" in response.json()

    def test_save_project_requires_auth(self, client):
        response = client.post("/api/projects", json={
            "name": "Test", "filename": "test.3mf", "session_id": "x",
            "solid_species": "Red Oak", "sheet_type": "Baltic Birch",
            "analysis_result": {"parts": [], "shopping_list": [], "cost_estimate": {"items": []}, "display_units": "in"},
        })
        assert response.status_code == 401

    @patch("app.main.list_projects")
    @patch("app.main.get_signed_url")
    def test_list_projects(self, mock_signed, mock_list, auth_client):
        mock_list.return_value = [{
            "id": "p1", "name": "Test", "filename": "test.3mf",
            "solid_species": "Red Oak", "sheet_type": "Baltic Birch",
            "analysis_result": {"parts": [{"name": "A", "quantity": 2, "length_mm": 100, "width_mm": 50, "thickness_mm": 19, "board_type": "solid", "stock": "4/4 Red Oak", "notes": ""}], "shopping_list": [], "cost_estimate": {"items": []}, "display_units": "in"},
            "thumbnail_path": "u/p/thumb.png",
            "created_at": "2026-04-28T00:00:00", "updated_at": "2026-04-28T00:00:00",
        }]
        mock_signed.return_value = "https://signed-url"

        response = auth_client.get("/api/projects")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test"
        assert data[0]["part_count"] == 2
        assert data[0]["thumbnail_url"] == "https://signed-url"

    def test_list_projects_requires_auth(self, client):
        response = client.get("/api/projects")
        assert response.status_code == 401

    @patch("app.main.get_project")
    @patch("app.main.get_signed_url")
    def test_get_project_detail(self, mock_signed, mock_get, auth_client):
        mock_get.return_value = {
            "id": "p1", "name": "Test", "filename": "test.3mf",
            "solid_species": "Red Oak", "sheet_type": "Baltic Birch",
            "all_solid": False, "display_units": "in",
            "analysis_result": {"parts": [], "shopping_list": [], "cost_estimate": {"items": []}, "display_units": "in"},
            "file_path": "u/p/model.3mf", "thumbnail_path": "u/p/thumb.png",
            "created_at": "2026-04-28T00:00:00", "updated_at": "2026-04-28T00:00:00",
        }
        mock_signed.return_value = "https://signed-url"

        response = auth_client.get("/api/projects/p1")
        assert response.status_code == 200
        assert response.json()["name"] == "Test"

    @patch("app.main.get_project")
    def test_get_project_not_found(self, mock_get, auth_client):
        mock_get.return_value = None
        response = auth_client.get("/api/projects/nonexistent")
        assert response.status_code == 404

    @patch("app.main.get_project")
    @patch("app.main.delete_files")
    @patch("app.main.delete_project")
    def test_delete_project(self, mock_del_db, mock_del_files, mock_get, auth_client):
        mock_get.return_value = {
            "id": "p1", "file_path": "u/p/model.3mf", "thumbnail_path": "u/p/thumb.png"
        }
        response = auth_client.delete("/api/projects/p1")
        assert response.status_code == 204
        mock_del_files.assert_called_once()
        mock_del_db.assert_called_once()
```

Add `from unittest.mock import patch` to the imports at the top of `test_routes.py`.

- [ ] **Step 3: Run tests**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_routes.py -v
```

Expected: All route tests PASS.

- [ ] **Step 4: Run full suite**

```bash
pytest -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py backend/tests/test_routes.py
git commit -m "feat: add project CRUD API endpoints"
```

---

## Task 5: Frontend Types and API Client

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Add project types**

Add to the end of `frontend/src/lib/types.ts`:

```typescript
export interface ProjectSummary {
	id: string;
	name: string;
	filename: string;
	solid_species: string;
	sheet_type: string;
	part_count: number;
	unique_parts: number;
	estimated_cost: number | null;
	thumbnail_url: string | null;
	created_at: string;
	updated_at: string;
}

export interface ProjectDetail {
	id: string;
	name: string;
	filename: string;
	solid_species: string;
	sheet_type: string;
	all_solid: boolean;
	display_units: DisplayUnits;
	analysis_result: AnalyzeResponse;
	file_url: string;
	thumbnail_url: string | null;
	created_at: string;
	updated_at: string;
}
```

- [ ] **Step 2: Add project API functions**

Add to the end of `frontend/src/lib/api.ts`:

```typescript
import type { ProjectSummary, ProjectDetail } from './types';

export async function saveProject(request: {
	name: string;
	filename: string;
	session_id: string;
	solid_species: string;
	sheet_type: string;
	all_solid?: boolean;
	display_units?: string;
	analysis_result: AnalyzeResponse;
	thumbnail?: string | null;
}): Promise<{ id: string }> {
	const response = await fetch(`${BASE}/projects`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', ...authHeaders() },
		body: JSON.stringify(request),
	});
	if (!response.ok) {
		if (response.status === 401) throw new Error('AUTH_REQUIRED');
		const detail = await response.json().catch(() => ({ detail: 'Save failed' }));
		throw new Error(detail.detail || 'Save failed');
	}
	return response.json();
}

export async function listProjects(): Promise<ProjectSummary[]> {
	const response = await fetch(`${BASE}/projects`, { headers: authHeaders() });
	if (!response.ok) {
		if (response.status === 401) throw new Error('AUTH_REQUIRED');
		throw new Error('Failed to load projects');
	}
	return response.json();
}

export async function getProjectDetail(id: string): Promise<ProjectDetail> {
	const response = await fetch(`${BASE}/projects/${id}`, { headers: authHeaders() });
	if (!response.ok) {
		if (response.status === 401) throw new Error('AUTH_REQUIRED');
		if (response.status === 404) throw new Error('Project not found');
		throw new Error('Failed to load project');
	}
	return response.json();
}

export async function deleteProject(id: string): Promise<void> {
	const response = await fetch(`${BASE}/projects/${id}`, {
		method: 'DELETE',
		headers: authHeaders(),
	});
	if (!response.ok) {
		if (response.status === 401) throw new Error('AUTH_REQUIRED');
		throw new Error('Failed to delete project');
	}
}
```

Note: The `import type` for `ProjectSummary` and `ProjectDetail` should be added to the existing import at the top of the file. Update the first import line from:
```typescript
import type { UploadResponse, AnalyzeRequest, AnalyzeResponse } from './types';
```
To:
```typescript
import type { UploadResponse, AnalyzeRequest, AnalyzeResponse, ProjectSummary, ProjectDetail } from './types';
```

- [ ] **Step 3: Verify build**

```bash
cd frontend && npx svelte-check && npm run build
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts
git commit -m "feat: add project types and API client functions"
```

---

## Task 6: Frontend UI — Save, List, Load Projects

**Files:**
- Modify: `frontend/src/lib/components/Results.svelte`
- Modify: `frontend/src/routes/+page.svelte`
- Create: `frontend/src/routes/projects/+page.svelte`
- Modify: `frontend/src/routes/+layout.svelte`

This is the final frontend task — it ties everything together. Create ALL files, then verify the build.

- [ ] **Step 1: Add Save Project button to Results.svelte**

Update the Props interface in `frontend/src/lib/components/Results.svelte`:

```typescript
interface Props {
    result: AnalyzeResponse;
    onDownloadPdf?: () => void;
    downloadingPdf?: boolean;
    isAuthenticated?: boolean;
    onSaveProject?: () => void;
    savingProject?: boolean;
    projectSaved?: boolean;
}
let { result, onDownloadPdf, downloadingPdf = false, isAuthenticated = false, onSaveProject, savingProject = false, projectSaved = false }: Props = $props();
```

Update the action buttons div to include Save Project:

```svelte
	<div class="flex gap-3 mt-6">
		{#if onSaveProject && isAuthenticated}
			<button
				onclick={onSaveProject}
				disabled={savingProject || projectSaved}
				class="bg-green-600 text-white px-4 py-2 rounded text-sm hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed">
				{#if projectSaved}
					Saved
				{:else if savingProject}
					Saving...
				{:else}
					Save Project
				{/if}
			</button>
		{/if}
		{#if onDownloadPdf}
			<button
				onclick={onDownloadPdf}
				disabled={downloadingPdf}
				class="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed">
				{#if downloadingPdf}
					Generating PDF...
				{:else if !isAuthenticated}
					Sign in to Download PDF
				{:else}
					Download PDF
				{/if}
			</button>
		{/if}
		<button onclick={exportCsv} class="bg-gray-800 text-white px-4 py-2 rounded text-sm hover:bg-gray-900">Export CSV</button>
		<button onclick={() => window.print()} class="bg-gray-200 text-gray-700 px-4 py-2 rounded text-sm hover:bg-gray-300">Print</button>
	</div>
```

- [ ] **Step 2: Create My Projects page**

Create `frontend/src/routes/projects/+page.svelte`:

```svelte
<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { listProjects, deleteProject } from '$lib/api';
	import { isAuthenticated } from '$lib/stores/auth';
	import type { ProjectSummary } from '$lib/types';

	let projects = $state<ProjectSummary[]>([]);
	let loading = $state(true);
	let error = $state('');

	$effect(() => {
		if (!$isAuthenticated) {
			goto(`/login?redirect=${encodeURIComponent('/projects')}`);
		}
	});

	onMount(async () => {
		if (!$isAuthenticated) return;
		try {
			projects = await listProjects();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load projects';
		} finally {
			loading = false;
		}
	});

	function formatDate(iso: string): string {
		return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
	}

	function formatCost(cost: number | null): string {
		if (cost === null) return 'N/A';
		return `$${cost.toFixed(2)}`;
	}

	async function handleDelete(id: string, name: string) {
		if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;
		try {
			await deleteProject(id);
			projects = projects.filter(p => p.id !== id);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to delete';
		}
	}
</script>

<div class="min-h-screen bg-gray-50">
	<header class="bg-white border-b border-gray-200 px-6 py-4">
		<div class="max-w-6xl mx-auto flex items-center justify-between">
			<h1 class="text-xl font-semibold text-gray-800">Kerf</h1>
			<div class="flex items-center gap-4">
				<a href="/" class="text-sm text-blue-600 hover:text-blue-800">New Project</a>
				<button onclick={() => { import('$lib/supabase').then(m => m.supabase.auth.signOut().then(() => goto('/'))); }} class="text-sm text-gray-500 hover:text-gray-700">Sign Out</button>
			</div>
		</div>
	</header>

	<main class="max-w-6xl mx-auto px-6 py-8">
		<h2 class="text-lg font-medium text-gray-700 mb-6">My Projects</h2>

		{#if loading}
			<p class="text-gray-500">Loading projects...</p>
		{:else if error}
			<p class="text-red-600">{error}</p>
		{:else if projects.length === 0}
			<div class="text-center py-16 text-gray-400">
				<p class="text-lg mb-2">No saved projects yet</p>
				<p class="text-sm">Upload a 3MF file and click "Save Project" to get started.</p>
				<a href="/" class="inline-block mt-4 text-blue-600 hover:text-blue-800 text-sm">Upload a file</a>
			</div>
		{:else}
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
				{#each projects as project}
					<div class="bg-white rounded-lg border border-gray-200 overflow-hidden hover:shadow-md transition-shadow">
						<button
							onclick={() => goto(`/?project=${project.id}`)}
							class="w-full text-left"
						>
							{#if project.thumbnail_url}
								<img src={project.thumbnail_url} alt={project.name} class="w-full h-40 object-cover bg-gray-100" />
							{:else}
								<div class="w-full h-40 bg-gray-100 flex items-center justify-center text-gray-300 text-sm">No preview</div>
							{/if}
							<div class="p-4">
								<h3 class="font-medium text-gray-800 truncate">{project.name}</h3>
								<p class="text-xs text-gray-400 mt-1">{formatDate(project.created_at)}</p>
								<div class="flex gap-3 mt-2 text-xs text-gray-500">
									<span>{project.part_count} parts</span>
									<span>{project.solid_species}</span>
									<span>{formatCost(project.estimated_cost)}</span>
								</div>
							</div>
						</button>
						<div class="px-4 pb-3">
							<button
								onclick={() => handleDelete(project.id, project.name)}
								class="text-xs text-red-500 hover:text-red-700"
							>
								Delete
							</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</main>
</div>
```

- [ ] **Step 3: Update main page to support save + load**

Update `frontend/src/routes/+page.svelte`. The key changes:
- Add `saveProject` and `getProjectDetail` imports
- Add `savingProject`, `projectSaved` state
- Add `handleSaveProject()` function
- Add `onMount` logic to detect `?project={id}` and load the project
- Pass new props to `<Results>`

This is a substantial update. Replace the entire file with the version that adds save/load support. The new additions vs the current file:

Add imports:
```typescript
import { page } from '$app/state';
import { saveProject, getProjectDetail } from '$lib/api';
```

Add state:
```typescript
let savingProject = $state(false);
let projectSaved = $state(false);
```

Add save handler:
```typescript
async function handleSaveProject() {
    if (!uploadResult || !lastConfig || !analyzeResult) return;
    if (!$isAuthenticated) {
        goto(`/login?redirect=${encodeURIComponent('/')}`);
        return;
    }
    savingProject = true;
    error = '';
    try {
        const thumbnail = modelApi?.captureScreenshot() ?? null;
        const name = uploadResult.parts_preview.length > 0
            ? uploadResult.file_url.split('/').pop()?.replace('.3mf', '') || 'Untitled'
            : 'Untitled';
        await saveProject({
            name,
            filename: uploadResult.file_url.split('/').pop() || 'model.3mf',
            session_id: uploadResult.session_id,
            ...lastConfig,
            analysis_result: analyzeResult,
            thumbnail,
        });
        projectSaved = true;
    } catch (e) {
        error = e instanceof Error ? e.message : 'Save failed';
    } finally {
        savingProject = false;
    }
}
```

Update `onMount` to handle `?project={id}`:
```typescript
onMount(async () => {
    const projectId = page.url.searchParams.get('project');
    if (projectId && $isAuthenticated) {
        try {
            status = 'Loading project...';
            const project = await getProjectDetail(projectId);
            analyzeResult = project.analysis_result;
            lastConfig = {
                solid_species: project.solid_species,
                sheet_type: project.sheet_type,
                all_solid: project.all_solid,
                display_units: project.display_units,
            };
            // Create a synthetic uploadResult for the viewer
            uploadResult = {
                session_id: '',
                file_url: project.file_url,
                parts_preview: project.analysis_result.parts.map(p => ({ name: p.name, vertex_count: 0 })),
            };
            projectSaved = true;
            status = '';
        } catch (e) {
            error = e instanceof Error ? e.message : 'Failed to load project';
            status = '';
        }
    }

    const pending = sessionStorage.getItem('pendingAction');
    if (pending === 'downloadPdf' && $isAuthenticated) {
        sessionStorage.removeItem('pendingAction');
    }
});
```

Update reset to clear project state:
```typescript
function reset() {
    uploadResult = null;
    analyzeResult = null;
    error = '';
    status = '';
    lastConfig = null;
    projectSaved = false;
    // Clear project query param
    if (page.url.searchParams.has('project')) {
        goto('/', { replaceState: true });
    }
}
```

Pass new props to Results:
```svelte
<Results result={analyzeResult} onDownloadPdf={handleDownloadPdf} {downloadingPdf} isAuthenticated={$isAuthenticated} onSaveProject={handleSaveProject} {savingProject} {projectSaved} />
```

- [ ] **Step 4: Add My Projects link to layout header**

Update `frontend/src/routes/+layout.svelte`. This is tricky because the layout currently has no header — the header is in each page. Instead, we'll leave the layout as-is and rely on individual page headers. The My Projects link is already in `+page.svelte` (via the header) and in the projects page.

Actually, let's just update `+page.svelte`'s header to include a "My Projects" link:

In the header section of `+page.svelte`, add a My Projects link when authenticated:

```svelte
<div class="flex items-center gap-4">
    {#if $isAuthenticated}
        <a href="/projects" class="text-sm text-gray-500 hover:text-gray-700">My Projects</a>
    {/if}
    {#if uploadResult}
        <button onclick={reset} class="text-sm text-gray-500 hover:text-gray-700">New Project</button>
    {/if}
    {#if $isAuthenticated}
        <button onclick={() => { import('$lib/supabase').then(m => m.supabase.auth.signOut()); }} class="text-sm text-gray-500 hover:text-gray-700">Sign Out</button>
    {:else}
        <a href="/login" class="text-sm text-blue-600 hover:text-blue-800">Sign In</a>
    {/if}
</div>
```

- [ ] **Step 5: Verify frontend builds**

```bash
cd frontend && npx svelte-check && npm run build
```

Expected: No errors, build succeeds.

- [ ] **Step 6: Commit**

```bash
cd /home/josebiro/gt/mayor
git add frontend/src/lib/components/Results.svelte \
  frontend/src/routes/+page.svelte \
  frontend/src/routes/projects/+page.svelte
git commit -m "feat: add Save Project, My Projects page, and project loading"
```

---

## Task 7: End-to-End Verification

- [ ] **Step 1: Run full backend test suite**

```bash
cd backend && source .venv/bin/activate && pytest -v
```

Expected: All tests PASS.

- [ ] **Step 2: Verify frontend builds**

```bash
cd frontend && npm run build
```

Expected: Build succeeds.

- [ ] **Step 3: Manual smoke test**

Start both services and test:
1. Upload a 3MF file, analyze
2. Click "Save Project" → should save (requires sign-in)
3. Go to `/projects` → should show the saved project card with thumbnail
4. Click the card → should load the project with 3D viewer + results
5. Delete a project → should remove the card
6. Upload without signing in → save button should not appear

- [ ] **Step 4: Commit and push**

```bash
git add -A && git commit -m "chore: project persistence fixes" && git push
```
