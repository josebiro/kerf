# Supabase Foundation + Auth — Design Spec

**Date:** 2026-04-28
**Status:** Draft
**Parent:** Freemium sub-system 1 of 5

## Overview

Add user authentication to Kerf using Supabase Auth. Unauthenticated users can upload and analyze freely. High-value actions (PDF export, future: saved projects, usage beyond free tier) require sign-in. Auth uses a redirect-based flow to a `/login` page with email/password and Google OAuth.

## Goals

- Integrate Supabase Auth for user sign-up, sign-in, and session management
- "Try before you buy" — upload and analyze work without auth
- Gate PDF export behind authentication
- Redirect-based auth flow (`/login` page, return to previous context)
- Email/password + Google OAuth (more providers can be toggled on later)
- Backend JWT verification for protected endpoints

## Non-Goals (this sub-system)

- Database tables for user data or projects (sub-system 2)
- Usage counting or tier enforcement (sub-system 3)
- Stripe payments (sub-system 4)
- Visual design system (separate design pass)
- Organization/team support

---

## Architecture

### Supabase Project

- **URL:** `https://amefknuamqfppajprbjr.supabase.co`
- **Services used:** Auth only (Postgres and Storage come in sub-system 2)
- **Auth providers:** Email/password (with email verification) + Google OAuth
- **Google OAuth:** configured in Supabase dashboard → Authentication → Providers → Google

### Environment Variables

**Backend (`backend/.env`):**
```
SUPABASE_URL=https://amefknuamqfppajprbjr.supabase.co
SUPABASE_ANON_KEY=<anon key from Supabase dashboard>
SUPABASE_SERVICE_KEY=<service_role key from Supabase dashboard>
```

**Frontend (`frontend/.env`):**
```
PUBLIC_SUPABASE_URL=https://amefknuamqfppajprbjr.supabase.co
PUBLIC_SUPABASE_ANON_KEY=<anon key from Supabase dashboard>
```

Both `.env` files must be in `.gitignore`.

---

## Auth Flow

### Unauthenticated Users

- Can upload 3MF files
- Can configure materials and run analysis
- Can view parts list, shopping list, cost estimate
- Can export CSV and print
- **Cannot** download PDF → clicking "Download PDF" redirects to `/login`

### Authentication Flow

1. User clicks a gated action (e.g., "Download PDF")
2. Frontend saves the intended action in sessionStorage (e.g., `pendingAction: "downloadPdf"`)
3. Frontend redirects to `/login?redirect=/` (or current path)
4. User signs in (email/password or Google OAuth)
5. Supabase handles the auth, sets session tokens
6. Frontend redirects back to the `redirect` URL
7. On page load, frontend checks sessionStorage for pending action and resumes it

### Sign-Up Flow

1. User enters email + password → Supabase creates account + sends verification email
2. User lands on a "Check your email" message
3. User clicks verification link → Supabase confirms → redirects to app
4. User is now authenticated

### Google OAuth Flow

1. User clicks "Continue with Google"
2. Redirects to Google consent screen
3. Google redirects back to Supabase callback URL
4. Supabase creates/links account, sets session
5. Redirects back to the app

---

## Backend Changes

### Dependencies

Add to `backend/requirements.txt`:
```
supabase==2.15.0
python-dotenv==1.0.1
PyJWT==2.10.1
```

### Auth Dependency

Create a FastAPI dependency that optionally extracts the authenticated user from the `Authorization: Bearer <jwt>` header:

```python
# Conceptual — not exact code
async def get_optional_user(authorization: str | None) -> dict | None:
    """Return user dict if valid JWT, None if no auth header."""
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "")
    # Verify JWT using Supabase JWT secret or public key
    # Return user payload (id, email) or None

async def require_user(user = Depends(get_optional_user)) -> dict:
    """Require authentication — raise 401 if not authenticated."""
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
```

### Endpoint Protection

| Endpoint | Auth |
|----------|------|
| `POST /api/upload` | Optional (works without auth) |
| `POST /api/analyze` | Optional |
| `GET /api/files/{session_id}/{filename}` | Optional |
| `GET /api/species` | Optional |
| `GET /api/sheet-types` | Optional |
| `POST /api/report` | **Required** (401 if not authenticated) |

### Configuration

Load environment variables from `.env` using `python-dotenv` at app startup. Read `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` for backend JWT verification.

---

## Frontend Changes

### Dependencies

```bash
npm install @supabase/supabase-js @supabase/ssr
```

### Supabase Client

Create a Supabase client initialized from environment variables. SvelteKit uses the `PUBLIC_` prefix for client-side env vars:

```typescript
import { createClient } from '@supabase/supabase-js'
const supabase = createClient(PUBLIC_SUPABASE_URL, PUBLIC_SUPABASE_ANON_KEY)
```

### Auth State

A Svelte store that tracks the current user session. The Supabase client provides `onAuthStateChange` to listen for sign-in/sign-out events. The session includes the JWT access token needed for authenticated API calls.

### New Routes

**`/login`** — Sign-in/sign-up page:
- Email input + password input + "Sign In" button
- "Don't have an account? Sign Up" toggle
- "Continue with Google" OAuth button
- "Forgot password?" link (Supabase handles reset flow)
- Reads `redirect` query param, redirects there after auth
- Minimal styling (full design pass comes later)

**`/auth/callback`** — OAuth callback handler:
- Supabase redirects here after OAuth
- Exchanges code for session
- Redirects to the stored redirect URL

### Auth Guard on Gated Actions

The "Download PDF" button checks auth state before calling the API:

```typescript
// Conceptual
function handleDownloadPdf() {
    if (!user) {
        sessionStorage.setItem('pendingAction', 'downloadPdf');
        goto(`/login?redirect=${encodeURIComponent(currentPath)}`);
        return;
    }
    // Proceed with PDF download
}
```

### API Client Auth Header

When a user is authenticated, include the JWT in API requests:

```typescript
const headers: Record<string, string> = { 'Content-Type': 'application/json' };
if (session?.access_token) {
    headers['Authorization'] = `Bearer ${session.access_token}`;
}
```

Only the `/api/report` endpoint requires this, but sending it on all requests is harmless and simplifies the client code.

### Pending Action Resume

After redirect back from `/login`, the main page checks sessionStorage:
```typescript
onMount(() => {
    const pending = sessionStorage.getItem('pendingAction');
    if (pending === 'downloadPdf') {
        sessionStorage.removeItem('pendingAction');
        handleDownloadPdf();
    }
});
```

---

## Files

### Backend

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/.env` | Create (manual, not committed) | Supabase credentials |
| `backend/requirements.txt` | Modify | Add supabase, python-dotenv, PyJWT |
| `backend/app/config.py` | Create | Load env vars, expose settings |
| `backend/app/auth.py` | Create | JWT verification, `get_optional_user`, `require_user` dependencies |
| `backend/app/main.py` | Modify | Add `require_user` dependency to `/api/report`, load dotenv |
| `backend/tests/test_auth.py` | Create | Auth dependency tests with mock JWTs |
| `backend/tests/test_routes.py` | Modify | Update report tests to include auth header |

### Frontend

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/.env` | Create (manual, not committed) | Supabase public credentials |
| `frontend/src/lib/supabase.ts` | Create | Supabase client initialization |
| `frontend/src/lib/stores/auth.ts` | Create | Auth state store (user, session) |
| `frontend/src/lib/api.ts` | Modify | Add auth header to requests |
| `frontend/src/routes/login/+page.svelte` | Create | Sign-in/sign-up page |
| `frontend/src/routes/auth/callback/+page.svelte` | Create | OAuth callback handler |
| `frontend/src/routes/+layout.svelte` | Modify | Initialize auth listener, provide auth state |
| `frontend/src/routes/+page.svelte` | Modify | Auth guard on PDF download, pending action resume |
| `frontend/src/lib/components/Results.svelte` | Modify | Pass auth state to Download PDF button |

### Config

| File | Action |
|------|--------|
| `.gitignore` | Modify — add `backend/.env`, `frontend/.env` |

---

## Testing

- Unit test: JWT verification with valid/invalid/expired tokens (mock, no Supabase call)
- Unit test: `require_user` returns 401 without auth header
- Unit test: `get_optional_user` returns None without auth header
- Integration test: `/api/report` returns 401 without auth, 200 with valid auth
- Integration test: `/api/analyze` works without auth (unchanged behavior)
- Frontend: login page renders sign-in form and Google button
- Frontend: gated button redirects to `/login` when not authenticated
