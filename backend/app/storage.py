"""Supabase Storage operations for project files.

User data operations take a user-scoped client; storage RLS on the
``projects`` bucket enforces that callers can only touch objects under
their own user_id prefix. Signed-URL generation is the one exception —
it uses the admin client so the URL is signed without needing the
caller's JWT. The path is still verified by the route handler against
the user's prefix before signing.
"""

from __future__ import annotations

import logging
from supabase import Client

from app.supabase_client import get_admin_client

logger = logging.getLogger(__name__)

BUCKET = "projects"


def upload_file(client: Client, path: str, content: bytes, content_type: str) -> None:
    """Upload a file to the projects bucket."""
    client.storage.from_(BUCKET).upload(
        path, content, file_options={"content-type": content_type}
    )


def get_signed_url(path: str, expires_in: int = 3600) -> str | None:
    """Generate a signed URL for a stored object.

    Uses admin to sign — callers MUST verify the path belongs to the user
    BEFORE calling this. Without that check, a tampered DB row could be
    used to mint URLs for other users' objects.
    """
    try:
        client = get_admin_client()
        result = client.storage.from_(BUCKET).create_signed_url(path, expires_in)
        return result.get("signedURL") or result.get("signedUrl")
    except Exception as e:
        logger.warning("Failed to create signed URL for %s: %s", path, e)
        return None


def delete_files(client: Client, paths: list[str]) -> None:
    """Delete files from the projects bucket."""
    client.storage.from_(BUCKET).remove(paths)


def download_file(client: Client, path: str) -> bytes:
    """Download a file from the projects bucket as bytes."""
    return client.storage.from_(BUCKET).download(path)
