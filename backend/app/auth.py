"""Supabase JWT authentication for FastAPI."""

from fastapi import Header, HTTPException

from app.supabase_client import get_supabase_client as _get_supabase_client


async def require_user(
    authorization: str | None = Header(None),
) -> dict:
    """Require an authenticated user. Raises 401 if not authenticated."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        client = _get_supabase_client()
        response = client.auth.get_user(token)
        return {
            "id": response.user.id,
            "email": response.user.email,
        }
    except Exception:
        raise HTTPException(status_code=401, detail="Authentication required")
