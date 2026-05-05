import os
import time
import uuid
from pathlib import Path

import pytest

from app.session import (
    create_session,
    get_session_path,
    cleanup_expired_sessions,
    validate_filename,
)


USER_A = "11111111-1111-1111-1111-111111111111"
USER_B = "22222222-2222-2222-2222-222222222222"


def test_create_session_returns_uuid(tmp_path):
    session_id = create_session(USER_A, base_dir=tmp_path)
    assert len(session_id) == 36  # UUID format
    assert (tmp_path / USER_A / session_id).is_dir()


def test_create_session_rejects_invalid_user(tmp_path):
    with pytest.raises(ValueError):
        create_session("../etc/passwd", base_dir=tmp_path)


def test_get_session_path_returns_path(tmp_path):
    session_id = create_session(USER_A, base_dir=tmp_path)
    path = get_session_path(session_id, USER_A, base_dir=tmp_path)
    assert path is not None
    assert path.is_dir()


def test_get_session_path_returns_none_for_missing(tmp_path):
    fake_id = str(uuid.uuid4())
    assert get_session_path(fake_id, USER_A, base_dir=tmp_path) is None


def test_get_session_path_isolates_users(tmp_path):
    """User A's session must not be visible to user B."""
    session_id = create_session(USER_A, base_dir=tmp_path)
    assert get_session_path(session_id, USER_B, base_dir=tmp_path) is None


def test_get_session_path_rejects_traversal_session_id(tmp_path):
    """Path-traversal session_id values must not resolve."""
    create_session(USER_A, base_dir=tmp_path)
    assert get_session_path("../../etc", USER_A, base_dir=tmp_path) is None
    assert get_session_path("..", USER_A, base_dir=tmp_path) is None
    assert get_session_path("not-a-uuid", USER_A, base_dir=tmp_path) is None


def test_get_session_path_rejects_traversal_user_id(tmp_path):
    session_id = create_session(USER_A, base_dir=tmp_path)
    assert get_session_path(session_id, "../etc", base_dir=tmp_path) is None
    assert get_session_path(session_id, "/", base_dir=tmp_path) is None


def test_validate_filename_accepts_safe_names():
    assert validate_filename("model.3mf") == "model.3mf"
    assert validate_filename("My_File-1.3mf") == "My_File-1.3mf"


def test_validate_filename_rejects_traversal():
    for bad in ["../escape.3mf", "/etc/passwd", "..", ".", "a/b.3mf",
                "a\\b.3mf", ".hidden", "", "a" * 300, "x\x00y"]:
        with pytest.raises(ValueError):
            validate_filename(bad)


def test_cleanup_expired_sessions(tmp_path):
    session_id = create_session(USER_A, base_dir=tmp_path)
    session_dir = tmp_path / USER_A / session_id
    # Backdate the directory modification time by 3 hours
    old_time = time.time() - (3 * 3600)
    os.utime(session_dir, (old_time, old_time))

    removed = cleanup_expired_sessions(base_dir=tmp_path, ttl_seconds=7200)
    assert removed == 1
    assert not session_dir.exists()


def test_cleanup_keeps_fresh_sessions(tmp_path):
    session_id = create_session(USER_A, base_dir=tmp_path)
    removed = cleanup_expired_sessions(base_dir=tmp_path, ttl_seconds=7200)
    assert removed == 0
    assert (tmp_path / USER_A / session_id).is_dir()
