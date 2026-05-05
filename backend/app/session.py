"""Per-user session directories on disk for in-flight 3MF uploads.

Sessions are bound to a user_id at creation. Every read/write must pass
both session_id AND user_id so handlers can't accidentally accept a
session belonging to another user (IDOR guard).

Inputs are strictly validated: session_id must be a UUID, filename must
be a single safe segment. The on-disk layout is base/{user_id}/{session_id},
which makes path traversal impossible by construction.
"""

import re
import shutil
import time
import uuid
from pathlib import Path

DEFAULT_BASE_DIR = Path(__file__).parent.parent / "sessions"
DEFAULT_TTL_SECONDS = 7200  # 2 hours

# Supabase user IDs are UUIDs in production. We allow a slightly wider
# safe charset so test fixtures with sentinel IDs ("test-user-123") work.
_USER_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_FILENAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_MAX_FILENAME_LEN = 255


def _is_valid_user_id(value: str) -> bool:
    return isinstance(value, str) and bool(_USER_ID_RE.match(value))


def _is_valid_session_id(value: str) -> bool:
    return isinstance(value, str) and bool(_UUID_RE.match(value))


def validate_filename(name: str) -> str:
    """Return name unchanged if it is a safe single path segment.

    Raises ValueError on anything that could escape the session directory
    (slashes, backslashes, '..', leading dot, control chars, oversized).
    """
    if not isinstance(name, str) or not name:
        raise ValueError("Filename required")
    if len(name) > _MAX_FILENAME_LEN:
        raise ValueError("Filename too long")
    if name.startswith(".") or name in (".", ".."):
        raise ValueError("Filename invalid")
    if not _FILENAME_RE.match(name):
        raise ValueError("Filename contains disallowed characters")
    return name


def create_session(user_id: str, base_dir: Path = DEFAULT_BASE_DIR) -> str:
    """Create a new session directory for the given user and return the session ID."""
    if not _is_valid_user_id(user_id):
        raise ValueError("Invalid user_id")
    session_id = str(uuid.uuid4())
    session_dir = base_dir / user_id / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_id


def get_session_path(
    session_id: str,
    user_id: str,
    base_dir: Path = DEFAULT_BASE_DIR,
) -> Path | None:
    """Return the session directory if it exists AND belongs to user_id, else None.

    Returns None for invalid session_id or user_id rather than raising,
    so handlers can treat this uniformly as a 404.
    """
    if not _is_valid_session_id(session_id):
        return None
    if not _is_valid_user_id(user_id):
        return None
    session_dir = base_dir / user_id / session_id
    if session_dir.is_dir():
        return session_dir
    return None


def cleanup_expired_sessions(
    base_dir: Path = DEFAULT_BASE_DIR,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> int:
    """Remove session directories older than ttl_seconds. Returns count removed."""
    if not base_dir.exists():
        return 0
    now = time.time()
    removed = 0
    for user_dir in base_dir.iterdir():
        if not user_dir.is_dir():
            continue
        for entry in user_dir.iterdir():
            if entry.is_dir():
                mtime = entry.stat().st_mtime
                if now - mtime > ttl_seconds:
                    shutil.rmtree(entry)
                    removed += 1
        try:
            user_dir.rmdir()
        except OSError:
            pass
    return removed
