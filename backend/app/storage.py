"""Supabase Storage operations for project files."""

import logging
from app.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

BUCKET = "projects"


def upload_file(path: str, content: bytes, content_type: str) -> None:
    """Upload a file to the projects bucket."""
    client = get_supabase_client()
    client.storage.from_(BUCKET).upload(
        path, content, file_options={"content-type": content_type}
    )


def get_signed_url(path: str, expires_in: int = 3600) -> str | None:
    """Get a signed URL for a file. Returns None on error."""
    try:
        client = get_supabase_client()
        result = client.storage.from_(BUCKET).create_signed_url(path, expires_in)
        return result.get("signedURL") or result.get("signedUrl")
    except Exception as e:
        logger.warning("Failed to create signed URL for %s: %s", path, e)
        return None


def delete_files(paths: list[str]) -> None:
    """Delete files from the projects bucket."""
    client = get_supabase_client()
    client.storage.from_(BUCKET).remove(paths)
