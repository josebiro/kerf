import asyncio
import base64
import contextlib
import logging
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel as _BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.models import (AnalyzeRequest, AnalyzeResponse, CostEstimate, Part, PartPreview, ShoppingItem, UploadResponse, ReportRequest)
from app.models import ProjectCreate, ProjectSummary, ProjectDetail
from app.models import OptimizeRequest, OptimizeResponse
from app.models import CatalogItem, UserPreferencesModel
from app.optimizer.optimize import run_optimization
from app.parser.threemf import parse_3mf
from app.analyzer.geometry import compute_dimensions, classify_board_type
from app.mapper.materials import map_part_to_stock, aggregate_shopping_list
from app.session import create_session, get_session_path, cleanup_expired_sessions, validate_filename
from app.suppliers.registry import get_supplier
from app.units import mm_to_inches
from app.report import generate_report_pdf
from app.auth import require_user
from app.supabase_client import get_user_client, get_admin_client
from app.storage import upload_file as storage_upload, get_signed_url, delete_files, download_file as storage_download
from app.database import (
    create_project, update_project, list_projects, get_project, delete_project,
    get_user_preferences, upsert_user_preferences, get_catalog as db_get_catalog, get_suppliers,
)
from app.config import ALLOWED_ORIGINS

log = logging.getLogger(__name__)

# Run cleanup every 10 minutes; sessions older than 2h are removed.
SESSION_GC_INTERVAL_SECONDS = 600


class RestoreSessionRequest(_BaseModel):
    project_id: str


def _is_safe_user_storage_path(path: str, user_id: str) -> bool:
    """Whether *path* is a Supabase Storage key the caller is allowed to access.

    Stored paths must live under the user's own user_id prefix and must not
    contain traversal segments. We deliberately do NOT require the second
    segment to match the row's project_id: legacy data uses a separately
    generated UUID for the path segment, while the row id comes from the
    database default. RLS on the projects table already ensures the caller
    owns the row, and storage RLS prevents cross-prefix writes.
    """
    if not isinstance(path, str) or not path:
        return False
    if ".." in path.split("/"):
        return False
    if "\\" in path or "\x00" in path:
        return False
    return path.startswith(f"{user_id}/")


def _rate_limit_key(request: Request) -> str:
    """Key requests by authenticated user when possible, else by IP.

    We don't verify the JWT here — that happens in require_user. A spoofed
    token just buckets the spoofer in the same per-token bucket as anyone
    using the same string, which is fine for rate limiting.
    """
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        if token:
            return f"tok:{token[-32:]}"  # tail to bound key length
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        # First IP in the list is the original client.
        return f"ip:{forwarded.split(',')[0].strip()}"
    if request.client is not None:
        return f"ip:{request.client.host}"
    return "ip:unknown"


limiter = Limiter(key_func=_rate_limit_key, default_limits=["240/minute"])


@contextlib.asynccontextmanager
async def _lifespan(app: FastAPI):
    cleanup_expired_sessions()

    async def _gc_loop():
        while True:
            try:
                await asyncio.sleep(SESSION_GC_INTERVAL_SECONDS)
                removed = cleanup_expired_sessions()
                if removed:
                    log.info("Session GC removed %d expired session(s)", removed)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("Session GC iteration failed; continuing")

    gc_task = asyncio.create_task(_gc_loop())
    try:
        yield
    finally:
        gc_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await gc_task


app = FastAPI(title="Cut List Generator API", lifespan=_lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.post("/api/upload", response_model=UploadResponse)
@limiter.limit("30/minute")
async def upload_file(request: Request, file: UploadFile = File(...), user: dict = Depends(require_user)):
    if not file.filename or not file.filename.lower().endswith(".3mf"):
        raise HTTPException(status_code=400, detail="Only .3mf files are accepted")
    # Always store with a fixed safe name; never trust client-provided filename
    # for the on-disk path (defense against traversal).
    safe_name = "model.3mf"
    session_id = create_session(user_id=user["id"])
    session_dir = get_session_path(session_id, user_id=user["id"])
    if session_dir is None:
        raise HTTPException(status_code=500, detail="Session directory missing")
    file_path = session_dir / safe_name
    content = await file.read()
    file_path.write_bytes(content)
    try:
        result = parse_3mf(file_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    previews = [PartPreview(name=body.name, vertex_count=body.vertices.shape[0]) for body in result.bodies]
    return UploadResponse(session_id=session_id, file_url=f"/api/files/{session_id}/{safe_name}", parts_preview=previews)


@app.post("/api/restore-session", response_model=UploadResponse)
@limiter.limit("30/minute")
async def restore_session(request: Request, payload: RestoreSessionRequest, user: dict = Depends(require_user)):
    """Restore a fresh local session from a saved project's stored 3MF.

    Looks up the project by ID, verifies it belongs to the caller, then
    downloads the 3MF directly from Supabase Storage. Never accepts a URL
    from the client — that would be SSRF.
    """
    db = get_user_client(user["token"])
    project = get_project(db, payload.project_id, user["id"])
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    file_path_str: str = project["file_path"]
    if not _is_safe_user_storage_path(file_path_str, user["id"]):
        log.warning(
            "restore_session: project %s has unsafe file_path %r",
            payload.project_id, file_path_str,
        )
        raise HTTPException(status_code=403, detail="Project file path is invalid")

    # Path was just verified to live under the caller's prefix, so storage
    # access is authorised. Use the admin client to side-step storage RLS,
    # which is configured separately in Supabase Studio.
    storage_client = get_admin_client()
    try:
        content = storage_download(storage_client, file_path_str)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to load project file: {e}")

    session_id = create_session(user_id=user["id"])
    session_dir = get_session_path(session_id, user_id=user["id"])
    if session_dir is None:
        raise HTTPException(status_code=500, detail="Session directory missing")
    filename = "model.3mf"
    file_path = session_dir / filename
    file_path.write_bytes(content)

    try:
        result = parse_3mf(file_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    previews = [PartPreview(name=body.name, vertex_count=body.vertices.shape[0]) for body in result.bodies]
    return UploadResponse(session_id=session_id, file_url=f"/api/files/{session_id}/{filename}", parts_preview=previews)


@app.post("/api/analyze", response_model=AnalyzeResponse)
@limiter.limit("60/minute")
async def analyze(request: Request, payload: AnalyzeRequest, user: dict = Depends(require_user)):
    session_dir = get_session_path(payload.session_id, user_id=user["id"])
    if session_dir is None:
        raise HTTPException(status_code=404, detail="Session not found")
    threemf_files = list(session_dir.glob("*.3mf"))
    if not threemf_files:
        raise HTTPException(status_code=404, detail="No 3MF file in session")
    result = parse_3mf(threemf_files[0])
    parts: list[Part] = []
    seen_geometries: dict[str, int] = {}
    for body in result.bodies:
        length_mm, width_mm, thickness_mm = compute_dimensions(body.vertices)
        length_in = mm_to_inches(length_mm)
        width_in = mm_to_inches(width_mm)
        thickness_in = mm_to_inches(thickness_mm)
        board_type, notes = classify_board_type(length_in, width_in, thickness_in, all_solid=payload.all_solid)
        geo_key = f"{round(length_mm, 1)}x{round(width_mm, 1)}x{round(thickness_mm, 1)}"
        if geo_key in seen_geometries:
            idx = seen_geometries[geo_key]
            parts[idx] = parts[idx].model_copy(update={"quantity": parts[idx].quantity + 1})
            continue
        part = Part(name=body.name, quantity=1, length_mm=round(length_mm, 2), width_mm=round(width_mm, 2),
                    thickness_mm=round(thickness_mm, 2), board_type=board_type, stock="", notes=notes)
        part = map_part_to_stock(part, species=payload.solid_species, sheet_type=payload.sheet_type)
        seen_geometries[geo_key] = len(parts)
        parts.append(part)
    shopping_list = aggregate_shopping_list(parts)
    supplier = get_supplier("woodworkers_source")
    for i, item in enumerate(shopping_list):
        updates: dict = {}
        if item.unit == "BF":
            price = supplier.get_price(payload.solid_species, item.thickness, item.quantity)
            if price is not None:
                updates["unit_price"] = price / item.quantity if item.quantity > 0 else 0
            url = supplier.get_product_url(payload.solid_species, item.thickness)
            if url is not None:
                updates["url"] = url
        else:
            price = supplier.get_sheet_price(payload.sheet_type, item.thickness)
            if price is not None:
                updates["unit_price"] = price
            url = supplier.get_sheet_url(payload.sheet_type, item.thickness)
            if url is not None:
                updates["url"] = url
        if updates:
            shopping_list[i] = item.model_copy(update=updates)
    cost_estimate = CostEstimate(items=shopping_list)
    return AnalyzeResponse(parts=parts, shopping_list=shopping_list, cost_estimate=cost_estimate, display_units=payload.display_units)

@app.get("/api/files/{session_id}/{filename}")
async def serve_file(session_id: str, filename: str, user: dict = Depends(require_user)):
    try:
        safe_name = validate_filename(filename)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid filename")
    session_dir = get_session_path(session_id, user_id=user["id"])
    if session_dir is None:
        raise HTTPException(status_code=404, detail="Session not found")
    file_path = session_dir / safe_name
    # Defense in depth: confirm the resolved path is still inside the session dir.
    try:
        file_path.resolve(strict=True).relative_to(session_dir.resolve(strict=True))
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

@app.get("/api/species")
async def get_species(user: dict = Depends(require_user)):
    supplier = get_supplier("woodworkers_source")
    return supplier.get_species_list()

@app.get("/api/sheet-types")
async def get_sheet_types(user: dict = Depends(require_user)):
    supplier = get_supplier("woodworkers_source")
    return supplier.get_sheet_types()

@app.post("/api/report")
@limiter.limit("30/minute")
async def download_report(request: Request, payload: ReportRequest, user: dict = Depends(require_user)):
    from app.optimizer.optimize import run_optimization as _run_optimization

    # Use pre-computed results if provided (e.g., from a saved project)
    if payload.analysis_result is not None:
        analyze_response = payload.analysis_result
        filename = "project.3mf"
    else:
        # Run the analysis pipeline from session
        session_dir = get_session_path(payload.session_id, user_id=user["id"])
        if session_dir is None:
            raise HTTPException(status_code=404, detail="Session not found")
        threemf_files = list(session_dir.glob("*.3mf"))
        if not threemf_files:
            raise HTTPException(status_code=404, detail="No 3MF file in session")

        result = parse_3mf(threemf_files[0])
        parts: list[Part] = []
        seen_geometries: dict[str, int] = {}
        for body in result.bodies:
            length_mm, width_mm, thickness_mm = compute_dimensions(body.vertices)
            length_in = mm_to_inches(length_mm)
            width_in = mm_to_inches(width_mm)
            thickness_in = mm_to_inches(thickness_mm)
            board_type, notes = classify_board_type(length_in, width_in, thickness_in, all_solid=payload.all_solid)
            geo_key = f"{round(length_mm, 1)}x{round(width_mm, 1)}x{round(thickness_mm, 1)}"
            if geo_key in seen_geometries:
                idx = seen_geometries[geo_key]
                parts[idx] = parts[idx].model_copy(update={"quantity": parts[idx].quantity + 1})
                continue
            part = Part(name=body.name, quantity=1, length_mm=round(length_mm, 2), width_mm=round(width_mm, 2),
                        thickness_mm=round(thickness_mm, 2), board_type=board_type, stock="", notes=notes)
            part = map_part_to_stock(part, species=payload.solid_species, sheet_type=payload.sheet_type)
            seen_geometries[geo_key] = len(parts)
            parts.append(part)

        shopping_list = aggregate_shopping_list(parts)
        supplier = get_supplier("woodworkers_source")
        for i, item in enumerate(shopping_list):
            updates: dict = {}
            if item.unit == "BF":
                price = supplier.get_price(payload.solid_species, item.thickness, item.quantity)
                if price is not None:
                    updates["unit_price"] = price / item.quantity if item.quantity > 0 else 0
                url = supplier.get_product_url(payload.solid_species, item.thickness)
                if url is not None:
                    updates["url"] = url
            else:
                price = supplier.get_sheet_price(payload.sheet_type, item.thickness)
                if price is not None:
                    updates["unit_price"] = price
                url = supplier.get_sheet_url(payload.sheet_type, item.thickness)
                if url is not None:
                    updates["url"] = url
            if updates:
                shopping_list[i] = item.model_copy(update=updates)

        cost_estimate = CostEstimate(items=shopping_list)
        analyze_response = AnalyzeResponse(
            parts=parts, shopping_list=shopping_list,
            cost_estimate=cost_estimate, display_units=payload.display_units,
        )
        filename = threemf_files[0].name

    # Use provided optimization result, or run with defaults as fallback
    if payload.optimize_result is not None:
        opt_result = payload.optimize_result
    else:
        try:
            opt_result = _run_optimization(
                parts=analyze_response.parts,
                shopping_list=analyze_response.shopping_list,
                solid_species=payload.solid_species,
                sheet_type=payload.sheet_type,
            )
        except Exception:
            opt_result = None

    pdf_bytes = generate_report_pdf(
        analyze_response, filename,
        payload.solid_species, payload.sheet_type,
        thumbnail_data_url=payload.thumbnail,
        optimize_result=opt_result,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="cut-list-report.pdf"'},
    )


@app.post("/api/projects", status_code=201)
async def save_project(request: ProjectCreate, user: dict = Depends(require_user)):
    user_id = user["id"]
    db = get_user_client(user["token"])
    # Storage paths are constructed below with the user_id prefix, so any
    # access goes through the admin client without storage RLS plumbing.
    storage_client = get_admin_client()
    analysis_dict = request.analysis_result.model_dump(mode="json")
    optimize_dict = request.optimize_result.model_dump(mode="json") if request.optimize_result else None

    # Update existing project
    if request.project_id:
        existing = get_project(db, request.project_id, user_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Project not found")

        # Update thumbnail if provided
        thumbnail_path = existing.get("thumbnail_path")
        if request.thumbnail:
            thumbnail_path = thumbnail_path or f"{user_id}/{request.project_id}/thumbnail.png"
            b64_data = request.thumbnail.split(",", 1)[-1]
            thumb_bytes = base64.b64decode(b64_data)
            try:
                storage_upload(storage_client, thumbnail_path, thumb_bytes, "image/png")
            except Exception:
                pass  # thumbnail update is best-effort (may already exist)

        update_project(
            db,
            project_id=request.project_id,
            user_id=user_id,
            analysis_result=analysis_dict,
            solid_species=request.solid_species,
            sheet_type=request.sheet_type,
            all_solid=request.all_solid,
            display_units=request.display_units,
            optimize_result=optimize_dict,
            thumbnail_path=thumbnail_path,
        )
        return {"id": request.project_id, "message": "Project updated"}

    # Create new project
    session_dir = get_session_path(request.session_id, user_id=user_id)
    if session_dir is None:
        raise HTTPException(status_code=404, detail="Session not found")
    threemf_files = list(session_dir.glob("*.3mf"))
    if not threemf_files:
        raise HTTPException(status_code=404, detail="No 3MF file in session")

    project_id = str(uuid.uuid4())

    file_path = f"{user_id}/{project_id}/model.3mf"
    file_bytes = threemf_files[0].read_bytes()
    storage_upload(storage_client, file_path, file_bytes, "application/octet-stream")

    thumbnail_path = None
    if request.thumbnail:
        thumbnail_path = f"{user_id}/{project_id}/thumbnail.png"
        b64_data = request.thumbnail.split(",", 1)[-1]
        thumb_bytes = base64.b64decode(b64_data)
        storage_upload(storage_client, thumbnail_path, thumb_bytes, "image/png")

    create_project(
        db,
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
        optimize_result=optimize_dict,
    )

    return {"id": project_id, "message": "Project saved"}


@app.get("/api/projects")
async def list_user_projects(user: dict = Depends(require_user)):
    db = get_user_client(user["token"])
    rows = list_projects(db, user["id"])
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
    db = get_user_client(user["token"])
    row = get_project(db, project_id, user["id"])
    if row is None:
        raise HTTPException(status_code=404, detail="Project not found")

    file_path_str = row.get("file_path") or ""
    if not _is_safe_user_storage_path(file_path_str, user["id"]):
        log.warning(
            "get_user_project: project %s has unsafe file_path %r",
            project_id, file_path_str,
        )
        raise HTTPException(status_code=403, detail="Project file path is invalid")
    file_url = get_signed_url(file_path_str) or ""
    thumbnail_url = None
    thumb_path = row.get("thumbnail_path")
    if thumb_path and _is_safe_user_storage_path(thumb_path, user["id"]):
        thumbnail_url = get_signed_url(thumb_path)

    analysis = AnalyzeResponse(**row["analysis_result"])
    optimize = OptimizeResponse(**row["optimize_result"]) if row.get("optimize_result") else None

    return ProjectDetail(
        id=row["id"],
        name=row["name"],
        filename=row["filename"],
        solid_species=row["solid_species"],
        sheet_type=row["sheet_type"],
        all_solid=row["all_solid"],
        display_units=row["display_units"],
        analysis_result=analysis,
        optimize_result=optimize,
        file_url=file_url,
        thumbnail_url=thumbnail_url,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@app.delete("/api/projects/{project_id}", status_code=204)
async def delete_user_project(project_id: str, user: dict = Depends(require_user)):
    db = get_user_client(user["token"])
    row = get_project(db, project_id, user["id"])
    if row is None:
        raise HTTPException(status_code=404, detail="Project not found")

    paths_to_delete: list[str] = []
    file_path = row.get("file_path")
    if file_path and _is_safe_user_storage_path(file_path, user["id"]):
        paths_to_delete.append(file_path)
    thumb_path = row.get("thumbnail_path")
    if thumb_path and _is_safe_user_storage_path(thumb_path, user["id"]):
        paths_to_delete.append(thumb_path)
    if paths_to_delete:
        delete_files(get_admin_client(), paths_to_delete)

    delete_project(db, project_id, user["id"])


@app.post("/api/optimize", response_model=OptimizeResponse)
@limiter.limit("60/minute")
async def optimize_cuts(request: Request, payload: OptimizeRequest, user: dict = Depends(require_user)):
    return run_optimization(
        parts=payload.parts,
        shopping_list=payload.shopping_list,
        solid_species=payload.solid_species,
        sheet_type=payload.sheet_type,
        buffer_config=payload.buffer_config,
        board_sizes=payload.board_sizes,
        sheet_size=payload.sheet_size,
    )


@app.get("/api/catalog")
async def get_catalog_endpoint(
    type: str | None = None,
    search: str | None = None,
    user: dict = Depends(require_user),
):
    db = get_user_client(user["token"])
    prefs = get_user_preferences(db, user["id"])
    enabled = prefs["enabled_suppliers"] if prefs else ["woodworkers_source"]
    rows = db_get_catalog(product_type=type, search=search, supplier_ids=enabled)
    items = []
    for row in rows:
        supplier_name = ""
        if row.get("suppliers") and isinstance(row["suppliers"], dict):
            supplier_name = row["suppliers"].get("name", "")
        items.append(CatalogItem(
            supplier_id=row["supplier_id"],
            supplier_name=supplier_name,
            product_type=row["product_type"],
            species_or_name=row["species_or_name"],
            thickness=row["thickness"],
            price=float(row["price"]),
            unit=row["unit"],
            url=row.get("url"),
        ))
    return items


@app.get("/api/preferences")
async def get_preferences(user: dict = Depends(require_user)):
    db = get_user_client(user["token"])
    prefs = get_user_preferences(db, user["id"])
    if prefs is None:
        return UserPreferencesModel()
    return UserPreferencesModel(
        enabled_suppliers=prefs.get("enabled_suppliers", ["woodworkers_source"]),
        default_species=prefs.get("default_species"),
        default_sheet_type=prefs.get("default_sheet_type"),
        default_units=prefs.get("default_units", "in"),
    )


@app.put("/api/preferences")
async def update_preferences(
    prefs: UserPreferencesModel,
    user: dict = Depends(require_user),
):
    db = get_user_client(user["token"])
    upsert_user_preferences(
        db,
        user_id=user["id"],
        enabled_suppliers=prefs.enabled_suppliers,
        default_species=prefs.default_species,
        default_sheet_type=prefs.default_sheet_type,
        default_units=prefs.default_units,
    )
    return {"message": "Preferences updated"}


@app.get("/api/suppliers")
async def list_suppliers_endpoint(user: dict = Depends(require_user)):
    return get_suppliers()
