import os
import time
from pathlib import Path
from app.session import create_session, get_session_path, cleanup_expired_sessions


def test_create_session_returns_uuid(tmp_path):
    session_id = create_session(base_dir=tmp_path)
    assert len(session_id) == 36  # UUID format
    assert (tmp_path / session_id).is_dir()


def test_get_session_path_returns_path(tmp_path):
    session_id = create_session(base_dir=tmp_path)
    path = get_session_path(session_id, base_dir=tmp_path)
    assert path is not None
    assert path.is_dir()


def test_get_session_path_returns_none_for_missing(tmp_path):
    path = get_session_path("nonexistent-id", base_dir=tmp_path)
    assert path is None


def test_cleanup_expired_sessions(tmp_path):
    session_id = create_session(base_dir=tmp_path)
    session_dir = tmp_path / session_id
    # Backdate the directory modification time by 3 hours
    old_time = time.time() - (3 * 3600)
    os.utime(session_dir, (old_time, old_time))

    removed = cleanup_expired_sessions(base_dir=tmp_path, ttl_seconds=7200)
    assert removed == 1
    assert not session_dir.exists()


def test_cleanup_keeps_fresh_sessions(tmp_path):
    session_id = create_session(base_dir=tmp_path)
    removed = cleanup_expired_sessions(base_dir=tmp_path, ttl_seconds=7200)
    assert removed == 0
    assert (tmp_path / session_id).is_dir()
