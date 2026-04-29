from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from app.models import (AnalyzeRequest, AnalyzeResponse, CostEstimate, Part, PartPreview, ShoppingItem, UploadResponse, ReportRequest)
from app.models import ProjectCreate, ProjectSummary, ProjectDetail
from app.models import OptimizeRequest, OptimizeResponse
from app.optimizer.optimize import run_optimization
from app.parser.threemf import parse_3mf
from app.analyzer.geometry import compute_dimensions, classify_board_type
from app.mapper.materials import map_part_to_stock, aggregate_shopping_list
from app.session import create_session, get_session_path, cleanup_expired_sessions
from app.suppliers.registry import get_supplier
from app.units import mm_to_inches
from app.report import generate_report_pdf
from app.auth import require_user
from app.storage import upload_file as storage_upload, get_signed_url, delete_files
from app.database import create_project, update_project, list_projects, get_project, delete_project
import base64
import uuid
import requests as http_requests
from pydantic import BaseModel as _BaseModel


class RestoreSessionRequest(_BaseModel):
    file_url: str
    filename: str = "model.3mf"

app = FastAPI(title="Cut List Generator API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

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
    previews = [PartPreview(name=body.name, vertex_count=body.vertices.shape[0]) for body in result.bodies]
    return UploadResponse(session_id=session_id, file_url=f"/api/files/{session_id}/{file.filename}", parts_preview=previews)


@app.post("/api/restore-session", response_model=UploadResponse)
async def restore_session(request: RestoreSessionRequest):
    """Download a 3MF file from a URL into a fresh local session.

    Used when loading a saved project — the 3MF is in Supabase Storage
    but we need a local session for analyze/report endpoints.
    """
    try:
        resp = http_requests.get(request.file_url, timeout=30)
        resp.raise_for_status()
        content = resp.content
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download file: {e}")

    session_id = create_session()
    session_dir = get_session_path(session_id)
    file_path = session_dir / request.filename
    file_path.write_bytes(content)

    try:
        result = parse_3mf(file_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    previews = [PartPreview(name=body.name, vertex_count=body.vertices.shape[0]) for body in result.bodies]
    return UploadResponse(session_id=session_id, file_url=f"/api/files/{session_id}/{request.filename}", parts_preview=previews)


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    session_dir = get_session_path(request.session_id)
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
        board_type, notes = classify_board_type(length_in, width_in, thickness_in, all_solid=request.all_solid)
        geo_key = f"{round(length_mm, 1)}x{round(width_mm, 1)}x{round(thickness_mm, 1)}"
        if geo_key in seen_geometries:
            idx = seen_geometries[geo_key]
            parts[idx] = parts[idx].model_copy(update={"quantity": parts[idx].quantity + 1})
            continue
        part = Part(name=body.name, quantity=1, length_mm=round(length_mm, 2), width_mm=round(width_mm, 2),
                    thickness_mm=round(thickness_mm, 2), board_type=board_type, stock="", notes=notes)
        part = map_part_to_stock(part, species=request.solid_species, sheet_type=request.sheet_type)
        seen_geometries[geo_key] = len(parts)
        parts.append(part)
    shopping_list = aggregate_shopping_list(parts)
    supplier = get_supplier("woodworkers_source")
    for i, item in enumerate(shopping_list):
        updates: dict = {}
        if item.unit == "BF":
            price = supplier.get_price(request.solid_species, item.thickness, item.quantity)
            if price is not None:
                updates["unit_price"] = price / item.quantity if item.quantity > 0 else 0
            url = supplier.get_product_url(request.solid_species, item.thickness)
            if url is not None:
                updates["url"] = url
        else:
            price = supplier.get_sheet_price(request.sheet_type, item.thickness)
            if price is not None:
                updates["unit_price"] = price
            url = supplier.get_sheet_url(request.sheet_type, item.thickness)
            if url is not None:
                updates["url"] = url
        if updates:
            shopping_list[i] = item.model_copy(update=updates)
    cost_estimate = CostEstimate(items=shopping_list)
    return AnalyzeResponse(parts=parts, shopping_list=shopping_list, cost_estimate=cost_estimate, display_units=request.display_units)

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

@app.post("/api/report")
async def download_report(request: ReportRequest, user: dict = Depends(require_user)):
    from app.optimizer.optimize import run_optimization as _run_optimization

    # Use pre-computed results if provided (e.g., from a saved project)
    if request.analysis_result is not None:
        analyze_response = request.analysis_result
        filename = "project.3mf"
    else:
        # Run the analysis pipeline from session
        session_dir = get_session_path(request.session_id)
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
            board_type, notes = classify_board_type(length_in, width_in, thickness_in, all_solid=request.all_solid)
            geo_key = f"{round(length_mm, 1)}x{round(width_mm, 1)}x{round(thickness_mm, 1)}"
            if geo_key in seen_geometries:
                idx = seen_geometries[geo_key]
                parts[idx] = parts[idx].model_copy(update={"quantity": parts[idx].quantity + 1})
                continue
            part = Part(name=body.name, quantity=1, length_mm=round(length_mm, 2), width_mm=round(width_mm, 2),
                        thickness_mm=round(thickness_mm, 2), board_type=board_type, stock="", notes=notes)
            part = map_part_to_stock(part, species=request.solid_species, sheet_type=request.sheet_type)
            seen_geometries[geo_key] = len(parts)
            parts.append(part)

        shopping_list = aggregate_shopping_list(parts)
        supplier = get_supplier("woodworkers_source")
        for i, item in enumerate(shopping_list):
            updates: dict = {}
            if item.unit == "BF":
                price = supplier.get_price(request.solid_species, item.thickness, item.quantity)
                if price is not None:
                    updates["unit_price"] = price / item.quantity if item.quantity > 0 else 0
                url = supplier.get_product_url(request.solid_species, item.thickness)
                if url is not None:
                    updates["url"] = url
            else:
                price = supplier.get_sheet_price(request.sheet_type, item.thickness)
                if price is not None:
                    updates["unit_price"] = price
                url = supplier.get_sheet_url(request.sheet_type, item.thickness)
                if url is not None:
                    updates["url"] = url
            if updates:
                shopping_list[i] = item.model_copy(update=updates)

        cost_estimate = CostEstimate(items=shopping_list)
        analyze_response = AnalyzeResponse(
            parts=parts, shopping_list=shopping_list,
            cost_estimate=cost_estimate, display_units=request.display_units,
        )
        filename = threemf_files[0].name

    # Run optimizer for PDF
    try:
        opt_result = _run_optimization(
            parts=analyze_response.parts,
            shopping_list=analyze_response.shopping_list,
            solid_species=request.solid_species,
            sheet_type=request.sheet_type,
        )
    except Exception:
        opt_result = None

    pdf_bytes = generate_report_pdf(
        analyze_response, filename,
        request.solid_species, request.sheet_type,
        thumbnail_data_url=request.thumbnail,
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
    analysis_dict = request.analysis_result.model_dump(mode="json")
    optimize_dict = request.optimize_result.model_dump(mode="json") if request.optimize_result else None

    # Update existing project
    if request.project_id:
        existing = get_project(request.project_id, user_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Project not found")

        # Update thumbnail if provided
        thumbnail_path = existing.get("thumbnail_path")
        if request.thumbnail:
            thumbnail_path = thumbnail_path or f"{user_id}/{request.project_id}/thumbnail.png"
            b64_data = request.thumbnail.split(",", 1)[-1]
            thumb_bytes = base64.b64decode(b64_data)
            try:
                storage_upload(thumbnail_path, thumb_bytes, "image/png")
            except Exception:
                pass  # thumbnail update is best-effort (may already exist)

        update_project(
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
    session_dir = get_session_path(request.session_id)
    if session_dir is None:
        raise HTTPException(status_code=404, detail="Session not found")
    threemf_files = list(session_dir.glob("*.3mf"))
    if not threemf_files:
        raise HTTPException(status_code=404, detail="No 3MF file in session")

    project_id = str(uuid.uuid4())

    file_path = f"{user_id}/{project_id}/model.3mf"
    file_bytes = threemf_files[0].read_bytes()
    storage_upload(file_path, file_bytes, "application/octet-stream")

    thumbnail_path = None
    if request.thumbnail:
        thumbnail_path = f"{user_id}/{project_id}/thumbnail.png"
        b64_data = request.thumbnail.split(",", 1)[-1]
        thumb_bytes = base64.b64decode(b64_data)
        storage_upload(thumbnail_path, thumb_bytes, "image/png")

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
        optimize_result=optimize_dict,
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
    row = get_project(project_id, user["id"])
    if row is None:
        raise HTTPException(status_code=404, detail="Project not found")

    paths_to_delete = [row["file_path"]]
    if row.get("thumbnail_path"):
        paths_to_delete.append(row["thumbnail_path"])
    delete_files(paths_to_delete)

    delete_project(project_id, user["id"])


@app.post("/api/optimize", response_model=OptimizeResponse)
async def optimize_cuts(request: OptimizeRequest):
    return run_optimization(
        parts=request.parts,
        shopping_list=request.shopping_list,
        solid_species=request.solid_species,
        sheet_type=request.sheet_type,
        buffer_config=request.buffer_config,
        board_sizes=request.board_sizes,
        sheet_size=request.sheet_size,
    )
