# Project Persistence — Design Spec

**Date:** 2026-04-28
**Status:** Draft
**Parent:** Freemium sub-system 2 of 5

## Overview

Add the ability for authenticated users to save and reload projects. The original 3MF file and thumbnail are stored in Supabase Storage, analysis config and results are stored in Supabase Postgres. A "My Projects" page shows saved projects as cards with thumbnails.

## Goals

- Save projects (3MF file, thumbnail, analysis config, results) with explicit "Save Project" button
- "My Projects" page with card grid showing thumbnail, name, date, materials, part count, cost
- Load a saved project back into the main app (3D viewer + results)
- Delete projects
- RLS: users can only access their own projects

## Non-Goals

- Sharing projects with other users
- Project versioning or history
- Auto-save
- Renaming projects after creation (use filename as default name)

---

## Database

### Table: `projects`

Created via Supabase SQL editor or migration:

```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    filename TEXT NOT NULL,
    solid_species TEXT NOT NULL,
    sheet_type TEXT NOT NULL,
    all_solid BOOLEAN NOT NULL DEFAULT false,
    display_units TEXT NOT NULL DEFAULT 'in',
    analysis_result JSONB NOT NULL,
    thumbnail_path TEXT,
    file_path TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RLS: users can only access their own projects
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own projects"
    ON projects FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own projects"
    ON projects FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own projects"
    ON projects FOR DELETE
    USING (auth.uid() = user_id);

-- Index for listing user's projects
CREATE INDEX idx_projects_user_id ON projects(user_id, created_at DESC);
```

### Column: `analysis_result`

Stores the complete `AnalyzeResponse` as JSONB:

```json
{
    "parts": [...],
    "shopping_list": [...],
    "cost_estimate": {...},
    "display_units": "in"
}
```

This is denormalized by design — we want instant loading without re-running the analysis pipeline. Users can re-analyze from the stored 3MF file if they want updated prices or different materials.

---

## Storage

### Bucket: `projects`

Created in Supabase dashboard → Storage → New bucket.

- **Public:** No (private bucket, accessed via signed URLs or service key)
- **File size limit:** 50MB (matches the frontend upload validation)
- **Allowed MIME types:** `application/octet-stream`, `image/png`

### File layout:

```
projects/
  {user_id}/
    {project_id}/
      model.3mf
      thumbnail.png
```

### RLS policies for storage:

```sql
-- Users can upload to their own folder
CREATE POLICY "Users can upload to own folder"
    ON storage.objects FOR INSERT
    WITH CHECK (bucket_id = 'projects' AND auth.uid()::text = (storage.foldername(name))[1]);

-- Users can read from their own folder
CREATE POLICY "Users can read own files"
    ON storage.objects FOR SELECT
    USING (bucket_id = 'projects' AND auth.uid()::text = (storage.foldername(name))[1]);

-- Users can delete from their own folder
CREATE POLICY "Users can delete own files"
    ON storage.objects FOR DELETE
    USING (bucket_id = 'projects' AND auth.uid()::text = (storage.foldername(name))[1]);
```

---

## API

All project endpoints require authentication (`require_user` dependency).

### POST /api/projects

Save a new project.

**Request body:**
```json
{
    "name": "Record Player Cabinet",
    "filename": "record-player-cabinet.3mf",
    "session_id": "uuid-of-current-session",
    "solid_species": "Red Oak",
    "sheet_type": "Red Oak Ply",
    "all_solid": false,
    "display_units": "in",
    "analysis_result": { "parts": [...], "shopping_list": [...], "cost_estimate": {...}, "display_units": "in" },
    "thumbnail": "data:image/png;base64,..."
}
```

**Backend flow:**
1. Verify session exists and has a 3MF file
2. Generate project UUID
3. Upload 3MF file from session dir to Supabase Storage at `{user_id}/{project_id}/model.3mf`
4. If thumbnail provided, decode base64 and upload to `{user_id}/{project_id}/thumbnail.png`
5. Insert row into `projects` table
6. Return the created project

**Response:** `201 Created` with the project object.

### GET /api/projects

List the current user's projects.

**Response:**
```json
[
    {
        "id": "uuid",
        "name": "Record Player Cabinet",
        "filename": "record-player-cabinet.3mf",
        "solid_species": "Red Oak",
        "sheet_type": "Red Oak Ply",
        "part_count": 14,
        "unique_parts": 5,
        "estimated_cost": 355.45,
        "thumbnail_url": "https://...supabase.co/storage/v1/object/sign/...",
        "created_at": "2026-04-28T...",
        "updated_at": "2026-04-28T..."
    }
]
```

The `part_count`, `unique_parts`, and `estimated_cost` are extracted from the stored `analysis_result` JSONB. `thumbnail_url` is a signed URL from Supabase Storage (1 hour expiry).

### GET /api/projects/{id}

Get a single project with full analysis results.

**Response:**
```json
{
    "id": "uuid",
    "name": "Record Player Cabinet",
    "filename": "record-player-cabinet.3mf",
    "solid_species": "Red Oak",
    "sheet_type": "Red Oak Ply",
    "all_solid": false,
    "display_units": "in",
    "analysis_result": { "parts": [...], "shopping_list": [...], "cost_estimate": {...} },
    "file_url": "https://...signed-url.../model.3mf",
    "thumbnail_url": "https://...signed-url.../thumbnail.png",
    "created_at": "...",
    "updated_at": "..."
}
```

`file_url` is a signed Storage URL for the 3MF file (for the Three.js viewer).

### DELETE /api/projects/{id}

Delete a project and its storage files.

**Backend flow:**
1. Verify project exists and belongs to the user
2. Delete storage files: `{user_id}/{project_id}/model.3mf` and `thumbnail.png`
3. Delete the database row
4. Return `204 No Content`

---

## Backend Implementation

### Dependencies

Add to `backend/requirements.txt`:
```
supabase
```

(Already installed from auth task — no new dependency needed.)

### Files

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/app/models.py` | Modify | Add `ProjectCreate`, `ProjectSummary`, `ProjectDetail` models |
| `backend/app/storage.py` | Create | Supabase Storage upload/download/delete + signed URL generation |
| `backend/app/database.py` | Create | Supabase Postgres queries for projects table |
| `backend/app/main.py` | Modify | Add project CRUD endpoints |
| `backend/tests/test_projects.py` | Create | Project endpoint tests |

### Supabase Client Usage

The backend uses the `supabase-py` client (already initialized in `auth.py`) with the service_role key. This bypasses RLS, so the backend must enforce ownership checks in code. The RLS policies are a safety net for direct Supabase client access from the frontend (which we don't do for writes, but it protects against bugs).

---

## Frontend Implementation

### Files

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/src/lib/types.ts` | Modify | Add `ProjectSummary`, `ProjectDetail` types |
| `frontend/src/lib/api.ts` | Modify | Add `saveProject`, `listProjects`, `getProject`, `deleteProject` |
| `frontend/src/routes/projects/+page.svelte` | Create | My Projects page with card grid |
| `frontend/src/routes/+page.svelte` | Modify | Add "Save Project" button, support loading from `?project={id}` |
| `frontend/src/lib/components/Results.svelte` | Modify | Add "Save Project" button (requires auth) |
| `frontend/src/routes/+layout.svelte` | Modify | Add "My Projects" link in header when authenticated |

### Save Project Flow

1. User analyzes a model and sees results
2. Clicks "Save Project" (visible only when authenticated)
3. Frontend captures thumbnail, sends project data to `POST /api/projects`
4. Shows success message
5. Button changes to "Saved ✓" (disabled)

### Load Project Flow

1. User clicks a card on `/projects`
2. Navigates to `/?project={id}`
3. Main page detects `project` query param
4. Fetches project detail from `GET /api/projects/{id}`
5. Loads the 3MF file URL into ModelViewer
6. Displays the stored analysis results
7. Configure panel pre-fills with saved material choices
8. User can re-analyze with different materials if desired

### My Projects Page

- Requires auth — redirects to `/login?redirect=/projects` if not signed in
- Grid of cards (responsive: 1 column mobile, 2 tablet, 3 desktop)
- Each card: thumbnail (or placeholder), project name, date, species + sheet type, part count, estimated cost
- Click card → loads project
- Delete button (trash icon) with confirmation dialog
- Empty state: "No saved projects yet. Upload a 3MF file to get started."

---

## Supabase Setup (Manual Steps)

These are done in the Supabase dashboard before running the implementation:

1. **Create `projects` table** — run the SQL from the Database section above in Supabase SQL Editor
2. **Create `projects` storage bucket** — Storage → New bucket → name: `projects`, private
3. **Add storage RLS policies** — run the storage policy SQL from the Storage section above

---

## Testing

- Unit test: storage upload/download/delete with mocked Supabase client
- Unit test: database queries with mocked Supabase client
- Integration test: `POST /api/projects` creates project and returns it
- Integration test: `GET /api/projects` returns only the current user's projects
- Integration test: `GET /api/projects/{id}` returns 404 for other user's project
- Integration test: `DELETE /api/projects/{id}` removes project and storage files
- Frontend: My Projects page renders cards
- Frontend: Save Project button saves and shows confirmation
- Frontend: Loading a project restores the viewer and results
