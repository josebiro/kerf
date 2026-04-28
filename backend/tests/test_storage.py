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
