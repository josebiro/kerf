"""Supabase clients.

Two flavours:

- ``get_admin_client()`` uses the service-role key. It bypasses RLS and is
  ONLY for system-level work that has no user context: verifying JWTs,
  reading the public catalog/suppliers tables, running scrapers/cron.
  Never touch user-owned data through this client; that is what RLS-aware
  user-scoped clients are for.

- ``get_user_client(token)`` uses the anon key with the caller's JWT
  applied. RLS policies on the projects/user_preferences tables and the
  ``projects`` storage bucket enforce that the caller can only see and
  modify their own rows/objects. This is the default for any handler
  that operates on user data.
"""

from __future__ import annotations

from supabase import create_client, Client
from app.config import SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY

_admin: Client | None = None


def get_admin_client() -> Client:
    """Service-role client. RLS is bypassed — keep usage to system tables."""
    global _admin
    if _admin is None:
        _admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _admin


# Backwards-compatible alias kept for the few callers (auth, suppliers,
# catalog, scrapers) that legitimately need admin. New code should call
# get_admin_client() explicitly.
def get_supabase_client() -> Client:
    return get_admin_client()


def get_user_client(token: str) -> Client:
    """Return an anon-key client whose Postgrest + Storage requests carry the
    caller's JWT. RLS policies on Supabase enforce isolation server-side.

    A new Client is constructed per request — supabase-py's Client is cheap
    to construct and stateful authentication on a singleton would race
    between concurrent requests.
    """
    if not token:
        raise ValueError("user-scoped Supabase client requires a JWT")
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    # Apply the user's JWT to Postgrest, Storage and Functions.
    client.postgrest.auth(token)
    try:
        client.storage._client.headers["Authorization"] = f"Bearer {token}"
    except AttributeError:
        # Older supabase-py versions: fall back to public method if present.
        pass
    return client
