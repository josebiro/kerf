"""Supabase JWT authentication for FastAPI."""

from typing import Optional
from fastapi import Header, HTTPException, Depends
from supabase import create_client, Client

from app.config import SUPABASE_URL, SUPABASE_SERVICE_KEY

_supabase_client: Client | None = None


def _get_supabase_client() -> Client:
    """Lazy-initialize the Supabase admin client."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _supabase_client


async def get_optional_user(
    authorization: Optional[str] = Header(None),
) -> dict | None:
    """Extract user from Authorization header if present and valid.

    Returns a dict with 'id' and 'email', or None if not authenticated.
    """
    if not authorization:
        return None

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        return None

    try:
        client = _get_supabase_client()
        response = client.auth.get_user(token)
        return {
            "id": response.user.id,
            "email": response.user.email,
        }
    except Exception:
        return None


async def require_user(
    user: dict | None = Depends(get_optional_user),
) -> dict:
    """Require an authenticated user. Raises 401 if not authenticated."""
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )
    return user
