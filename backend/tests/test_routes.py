import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from tests.conftest import build_3mf_bytes
from app.auth import require_user


@pytest.fixture
def client(tmp_path):
    """Create a test client with a temp session directory."""
    from app import session as session_mod
    import app.suppliers.registry as registry_mod
    from app.suppliers.woodworkers_source import WoodworkersSourceSupplier

    original_base_dir = session_mod.DEFAULT_BASE_DIR
    session_mod.DEFAULT_BASE_DIR = tmp_path

    # Inject a static-only supplier so route tests don't hit the live scraper
    original_instances = registry_mod._instances.copy()
    registry_mod._instances["woodworkers_source"] = WoodworkersSourceSupplier(
        cache_dir=None, use_scraper=False
    )

    from app.main import app
    yield TestClient(app)

    session_mod.DEFAULT_BASE_DIR = original_base_dir
    registry_mod._instances.clear()
    registry_mod._instances.update(original_instances)


@pytest.fixture
def auth_client(tmp_path):
    """Test client with auth dependency overridden."""
    from app import session as session_mod
    import app.suppliers.registry as registry_mod
    from app.suppliers.woodworkers_source import WoodworkersSourceSupplier
    from app.main import app
    from app.auth import require_user

    original_base_dir = session_mod.DEFAULT_BASE_DIR
    session_mod.DEFAULT_BASE_DIR = tmp_path

    original_instances = registry_mod._instances.copy()
    registry_mod._instances["woodworkers_source"] = WoodworkersSourceSupplier(
        cache_dir=None, use_scraper=False
    )

    async def mock_require_user():
        return {"id": "test-user-123", "email": "test@example.com"}

    app.dependency_overrides[require_user] = mock_require_user

    yield TestClient(app)

    session_mod.DEFAULT_BASE_DIR = original_base_dir
    registry_mod._instances.clear()
    registry_mod._instances.update(original_instances)
    app.dependency_overrides.clear()


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


class TestReport:
    def _upload(self, client) -> str:
        data = build_3mf_bytes()
        resp = client.post("/api/upload", files={"file": ("test.3mf", data, "application/octet-stream")})
        return resp.json()["session_id"]

    def test_report_requires_auth(self, client):
        """Report endpoint returns 401 without authentication."""
        session_id = self._upload(client)
        response = client.post("/api/report", json={
            "session_id": session_id,
            "solid_species": "Red Oak",
            "sheet_type": "Baltic Birch",
        })
        assert response.status_code == 401

    def test_report_returns_pdf(self, auth_client):
        session_id = self._upload(auth_client)
        response = auth_client.post("/api/report", json={
            "session_id": session_id,
            "solid_species": "Red Oak",
            "sheet_type": "Baltic Birch",
        })
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content[:5] == b"%PDF-"

    def test_report_with_thumbnail(self, auth_client):
        session_id = self._upload(auth_client)
        tiny_png = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        response = auth_client.post("/api/report", json={
            "session_id": session_id,
            "solid_species": "Red Oak",
            "sheet_type": "Baltic Birch",
            "thumbnail": tiny_png,
        })
        assert response.status_code == 200
        assert response.content[:5] == b"%PDF-"

    def test_report_invalid_session(self, auth_client):
        response = auth_client.post("/api/report", json={
            "session_id": "nonexistent",
            "solid_species": "Red Oak",
            "sheet_type": "Baltic Birch",
        })
        assert response.status_code == 404
