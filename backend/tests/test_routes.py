import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from tests.conftest import build_3mf_bytes


@pytest.fixture
def client(tmp_path):
    """Create a test client with a temp session directory."""
    from app import session as session_mod
    original = session_mod.DEFAULT_BASE_DIR
    session_mod.DEFAULT_BASE_DIR = tmp_path
    from app.main import app
    yield TestClient(app)
    session_mod.DEFAULT_BASE_DIR = original


class TestUpload:
    def test_upload_valid_3mf(self, client):
        data = build_3mf_bytes()
        response = client.post("/api/upload", files={"file": ("test.3mf", data, "application/octet-stream")})
        assert response.status_code == 200
        body = response.json()
        assert "session_id" in body
        assert "file_url" in body
        assert len(body["parts_preview"]) == 1
        assert body["parts_preview"][0]["name"] == "TestBox"

    def test_upload_invalid_file(self, client):
        response = client.post("/api/upload", files={"file": ("test.3mf", b"not a zip", "application/octet-stream")})
        assert response.status_code == 400

    def test_upload_wrong_extension(self, client):
        data = build_3mf_bytes()
        response = client.post("/api/upload", files={"file": ("test.stl", data, "application/octet-stream")})
        assert response.status_code == 400


class TestAnalyze:
    def _upload(self, client) -> str:
        data = build_3mf_bytes()
        resp = client.post("/api/upload", files={"file": ("test.3mf", data, "application/octet-stream")})
        return resp.json()["session_id"]

    def test_analyze_returns_parts(self, client):
        session_id = self._upload(client)
        response = client.post("/api/analyze", json={
            "session_id": session_id, "solid_species": "Red Oak", "sheet_type": "Baltic Birch"})
        assert response.status_code == 200
        body = response.json()
        assert len(body["parts"]) == 1
        assert body["parts"][0]["name"] == "TestBox"
        assert body["parts"][0]["board_type"] == "solid"

    def test_analyze_returns_shopping_list(self, client):
        session_id = self._upload(client)
        response = client.post("/api/analyze", json={
            "session_id": session_id, "solid_species": "Red Oak", "sheet_type": "Baltic Birch"})
        body = response.json()
        assert len(body["shopping_list"]) > 0

    def test_analyze_returns_cost_estimate(self, client):
        session_id = self._upload(client)
        response = client.post("/api/analyze", json={
            "session_id": session_id, "solid_species": "Red Oak", "sheet_type": "Baltic Birch"})
        body = response.json()
        assert "cost_estimate" in body
        assert "total" in body["cost_estimate"]

    def test_analyze_invalid_session(self, client):
        response = client.post("/api/analyze", json={
            "session_id": "nonexistent", "solid_species": "Red Oak", "sheet_type": "Baltic Birch"})
        assert response.status_code == 404

    def test_analyze_with_display_units_mm(self, client):
        session_id = self._upload(client)
        response = client.post("/api/analyze", json={
            "session_id": session_id, "solid_species": "Red Oak", "sheet_type": "Baltic Birch", "display_units": "mm"})
        assert response.status_code == 200
        body = response.json()
        assert body["display_units"] == "mm"


class TestFileServing:
    def test_serve_uploaded_file(self, client):
        data = build_3mf_bytes()
        resp = client.post("/api/upload", files={"file": ("test.3mf", data, "application/octet-stream")})
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
        assert "Red Oak" in response.json()

    def test_get_sheet_types(self, client):
        response = client.get("/api/sheet-types")
        assert response.status_code == 200
        assert "Baltic Birch" in response.json()
