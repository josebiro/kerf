"""Supabase JWT authentication for FastAPI.

The bearer token is verified via Supabase Auth and the resulting user
identity (id, email, raw token) is returned. Handlers then use the raw
token to construct a user-scoped Supabase client whose Postgrest and
Storage requests honour RLS policies.
"""

from fastapi import Header, HTTPException

from app.supabase_client import get_admin_client


async def require_user(
    authorization: str | None = Header(None),
) -> dict:
    """Require an authenticated user. Raises 401 if not authenticated.

    Returns a dict with ``id``, ``email`` and ``token`` (the raw JWT).
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        client = get_admin_client()
        response = client.auth.get_user(token)
        return {
            "id": response.user.id,
            "email": response.user.email,
            "token": token,
        }
    except Exception:
        raise HTTPException(status_code=401, detail="Authentication required")
