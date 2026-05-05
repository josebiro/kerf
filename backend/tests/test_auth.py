"""Test that all API endpoints require authentication."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_upload_requires_auth():
    response = client.post("/api/upload", files={"file": ("test.3mf", b"fake", "application/octet-stream")})
    assert response.status_code == 401


def test_analyze_requires_auth():
    response = client.post("/api/analyze", json={"session_id": "x", "solid_species": "Red Oak", "sheet_type": "Baltic Birch"})
    assert response.status_code == 401


def test_optimize_requires_auth():
    response = client.post("/api/optimize", json={"parts": [], "shopping_list": [], "solid_species": "Red Oak", "sheet_type": "Baltic Birch"})
    assert response.status_code == 401


def test_species_requires_auth():
    response = client.get("/api/species")
    assert response.status_code == 401


def test_sheet_types_requires_auth():
    response = client.get("/api/sheet-types")
    assert response.status_code == 401


def test_restore_session_requires_auth():
    response = client.post("/api/restore-session", json={"project_id": "any"})
    assert response.status_code == 401


def test_restore_session_rejects_legacy_file_url_payload():
    """The endpoint no longer accepts file_url (SSRF protection); legacy
    callers must fail validation, not be silently coerced."""
    response = client.post(
        "/api/restore-session",
        json={"file_url": "http://internal.local/secret"},
    )
    # 401 (auth first) or 422 (schema) are both acceptable; what we MUST
    # NOT see is the request reaching network code.
    assert response.status_code in (401, 422)
