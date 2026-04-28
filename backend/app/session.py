import shutil
import time
import uuid
from pathlib import Path

DEFAULT_BASE_DIR = Path(__file__).parent.parent / "sessions"
DEFAULT_TTL_SECONDS = 7200  # 2 hours


def create_session(base_dir: Path = DEFAULT_BASE_DIR) -> str:
    """Create a new session directory and return the session ID."""
    session_id = str(uuid.uuid4())
    session_dir = base_dir / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_id


def get_session_path(session_id: str, base_dir: Path = DEFAULT_BASE_DIR) -> Path | None:
    """Return the session directory path, or None if it doesn't exist."""
    session_dir = base_dir / session_id
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
    for entry in base_dir.iterdir():
        if entry.is_dir():
            mtime = entry.stat().st_mtime
            if now - mtime > ttl_seconds:
                shutil.rmtree(entry)
                removed += 1
    return removed
