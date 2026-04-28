from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.models import (AnalyzeRequest, AnalyzeResponse, CostEstimate, Part, PartPreview, ShoppingItem, UploadResponse)
from app.parser.threemf import parse_3mf
from app.analyzer.geometry import compute_dimensions, classify_board_type
from app.mapper.materials import map_part_to_stock, aggregate_shopping_list
from app.session import create_session, get_session_path, cleanup_expired_sessions
from app.suppliers.registry import get_supplier
from app.units import mm_to_inches

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
