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
    response = client.post("/api/restore-session", json={"file_url": "http://example.com/test.3mf"})
    assert response.status_code == 401
