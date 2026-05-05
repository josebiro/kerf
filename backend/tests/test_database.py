from unittest.mock import patch, MagicMock

from app.database import create_project, list_projects, get_project, delete_project


class TestCreateProject:
    def test_inserts_and_returns_id(self):
        mock_response = MagicMock()
        mock_response.data = [{"id": "proj-123"}]

        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.return_value = mock_response

        result = create_project(
            mock_client,
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

        rows = list_projects(mock_client, "user-1")

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

        row = get_project(mock_client, "p1", "user-1")

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

        row = get_project(mock_client, "nonexistent", "user-1")

        assert row is None


class TestDeleteProject:
    def test_deletes_by_id_and_user(self):
        mock_client = MagicMock()
        mock_client.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()

        delete_project(mock_client, "p1", "user-1")

        mock_client.table.assert_called_with("projects")
