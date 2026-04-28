# Supabase Auth — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add user authentication via Supabase Auth with a "try before you buy" model — upload/analyze work without auth, PDF export requires sign-in.

**Architecture:** Frontend uses `@supabase/supabase-js` for client-side auth (email/password + Google OAuth). The access token is sent to the backend via `Authorization: Bearer` header. Backend verifies JWTs using the `supabase-py` client. Only `/api/report` is protected; all other endpoints remain open.

**Tech Stack:** supabase-py, python-dotenv, PyJWT (backend); @supabase/supabase-js (frontend); Supabase Auth (managed service).

**Spec:** `docs/superpowers/specs/2026-04-28-supabase-auth-design.md`

---

## File Map

### Backend

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/requirements.txt` | Modify | Add supabase, python-dotenv, PyJWT |
| `backend/app/config.py` | Create | Load env vars from .env, expose as settings |
| `backend/app/auth.py` | Create | JWT verification, FastAPI dependencies: `get_optional_user`, `require_user` |
| `backend/app/main.py` | Modify | Load dotenv at startup, add `require_user` to `/api/report` |
| `backend/tests/test_auth.py` | Create | Auth dependency tests with mock JWTs |
| `backend/tests/test_routes.py` | Modify | Update report tests to include auth headers |

### Frontend

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/src/lib/supabase.ts` | Create | Supabase client singleton |
| `frontend/src/lib/stores/auth.ts` | Create | Reactive auth state store (user, session, loading) |
| `frontend/src/lib/api.ts` | Modify | Add auth header to all requests when session exists |
| `frontend/src/routes/+layout.svelte` | Modify | Initialize auth listener, provide auth context |
| `frontend/src/routes/login/+page.svelte` | Create | Sign-in/sign-up form + Google OAuth |
| `frontend/src/routes/auth/callback/+page.svelte` | Create | OAuth redirect handler |
| `frontend/src/routes/+page.svelte` | Modify | Gate PDF download behind auth, pending action resume |
| `frontend/src/lib/components/Results.svelte` | Modify | Accept `isAuthenticated` prop, show auth prompt on PDF button |

---

## Task 1: Backend Dependencies and Config

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/app/config.py`

- [ ] **Step 1: Add dependencies to requirements.txt**

Add these lines to the end of `backend/requirements.txt`:

```
supabase==2.15.0
python-dotenv==1.0.1
PyJWT==2.10.1
```

- [ ] **Step 2: Install dependencies**

```bash
cd backend && source .venv/bin/activate && pip install supabase==2.15.0 python-dotenv==1.0.1 PyJWT==2.10.1
```

- [ ] **Step 3: Create config module**

```python
# backend/app/config.py
"""Application configuration loaded from environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend directory
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path)

SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY: str = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_KEY: str = os.environ.get("SUPABASE_SERVICE_KEY", "")
```

- [ ] **Step 4: Verify config loads**

```bash
cd backend && source .venv/bin/activate
python3 -c "from app.config import SUPABASE_URL; print(f'URL: {SUPABASE_URL}')"
```

Expected: Prints the Supabase URL from `.env`.

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/app/config.py
git commit -m "feat: add Supabase dependencies and config module"
```

---

## Task 2: Backend Auth Module

**Files:**
- Create: `backend/app/auth.py`
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: Write failing auth tests**

```python
# backend/tests/test_auth.py
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException
from app.auth import get_optional_user, require_user


class TestGetOptionalUser:
    @pytest.mark.asyncio
    async def test_returns_none_without_header(self):
        user = await get_optional_user(authorization=None)
        assert user is None

    @pytest.mark.asyncio
    async def test_returns_none_with_empty_header(self):
        user = await get_optional_user(authorization="")
        assert user is None

    @pytest.mark.asyncio
    async def test_returns_user_with_valid_token(self):
        mock_response = MagicMock()
        mock_response.user = MagicMock()
        mock_response.user.id = "user-123"
        mock_response.user.email = "test@example.com"

        with patch("app.auth._get_supabase_client") as mock_client:
            mock_client.return_value.auth.get_user = MagicMock(return_value=mock_response)
            user = await get_optional_user(authorization="Bearer fake-jwt-token")
            assert user is not None
            assert user["id"] == "user-123"
            assert user["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_returns_none_with_invalid_token(self):
        with patch("app.auth._get_supabase_client") as mock_client:
            mock_client.return_value.auth.get_user = MagicMock(side_effect=Exception("Invalid token"))
            user = await get_optional_user(authorization="Bearer bad-token")
            assert user is None


class TestRequireUser:
    @pytest.mark.asyncio
    async def test_returns_user_when_authenticated(self):
        user = {"id": "user-123", "email": "test@example.com"}
        result = await require_user(user=user)
        assert result == user

    @pytest.mark.asyncio
    async def test_raises_401_when_no_user(self):
        with pytest.raises(HTTPException) as exc_info:
            await require_user(user=None)
        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_auth.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.auth'`

- [ ] **Step 3: Implement auth module**

```python
# backend/app/auth.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_auth.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/auth.py tests/test_auth.py
git commit -m "feat: add Supabase auth module with JWT verification"
```

---

## Task 3: Protect Report Endpoint

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_routes.py`

- [ ] **Step 1: Add auth import and dependency to main.py**

Add this import near the top of `backend/app/main.py`:

```python
from fastapi import Depends
from app.auth import require_user
```

Note: `Depends` needs to be added to the existing `from fastapi import ...` line.

Then change the `/api/report` endpoint signature from:

```python
@app.post("/api/report")
async def download_report(request: ReportRequest):
```

To:

```python
@app.post("/api/report")
async def download_report(request: ReportRequest, user: dict = Depends(require_user)):
```

The rest of the endpoint body stays the same.

- [ ] **Step 2: Update report route tests**

In `backend/tests/test_routes.py`, update the `TestReport` class. The tests need to mock the auth dependency since we can't get real Supabase tokens in tests.

Add this import at the top of the file:

```python
from app.auth import require_user
```

Add a helper fixture for authenticated requests. Add this after the existing `client` fixture:

```python
@pytest.fixture
def auth_client(tmp_path):
    """Test client with auth dependency overridden."""
    from app import session as session_mod
    import app.suppliers.registry as registry_mod
    from app.suppliers.woodworkers_source import WoodworkersSourceSupplier
    from app.main import app
    from app.auth import require_user

    original_base_dir = session_mod.DEFAULT_BASE_DIR
    session_mod.DEFAULT_BASE_DIR = tmp_path

    original_instances = registry_mod._instances.copy()
    registry_mod._instances["woodworkers_source"] = WoodworkersSourceSupplier(
        cache_dir=None, use_scraper=False
    )

    # Override auth dependency to return a fake user
    async def mock_require_user():
        return {"id": "test-user-123", "email": "test@example.com"}

    app.dependency_overrides[require_user] = mock_require_user

    yield TestClient(app)

    session_mod.DEFAULT_BASE_DIR = original_base_dir
    registry_mod._instances.clear()
    registry_mod._instances.update(original_instances)
    app.dependency_overrides.clear()
```

Update the `TestReport` class to use `auth_client` and add a 401 test:

```python
class TestReport:
    def _upload(self, client) -> str:
        data = build_3mf_bytes()
        resp = client.post("/api/upload", files={"file": ("test.3mf", data, "application/octet-stream")})
        return resp.json()["session_id"]

    def test_report_requires_auth(self, client):
        """Report endpoint returns 401 without authentication."""
        session_id = self._upload(client)
        response = client.post("/api/report", json={
            "session_id": session_id,
            "solid_species": "Red Oak",
            "sheet_type": "Baltic Birch",
        })
        assert response.status_code == 401

    def test_report_returns_pdf(self, auth_client):
        session_id = self._upload(auth_client)
        response = auth_client.post("/api/report", json={
            "session_id": session_id,
            "solid_species": "Red Oak",
            "sheet_type": "Baltic Birch",
        })
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content[:5] == b"%PDF-"

    def test_report_with_thumbnail(self, auth_client):
        session_id = self._upload(auth_client)
        tiny_png = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        response = auth_client.post("/api/report", json={
            "session_id": session_id,
            "solid_species": "Red Oak",
            "sheet_type": "Baltic Birch",
            "thumbnail": tiny_png,
        })
        assert response.status_code == 200
        assert response.content[:5] == b"%PDF-"

    def test_report_invalid_session(self, auth_client):
        response = auth_client.post("/api/report", json={
            "session_id": "nonexistent",
            "solid_species": "Red Oak",
            "sheet_type": "Baltic Birch",
        })
        assert response.status_code == 404
```

- [ ] **Step 3: Run tests**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_routes.py -v
```

Expected: All route tests PASS including the new `test_report_requires_auth`.

- [ ] **Step 4: Run full suite**

```bash
cd backend && source .venv/bin/activate && pytest -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/main.py tests/test_routes.py
git commit -m "feat: protect /api/report endpoint with auth requirement"
```

---

## Task 4: Frontend Supabase Client and Auth Store

**Files:**
- Create: `frontend/src/lib/supabase.ts`
- Create: `frontend/src/lib/stores/auth.ts`

- [ ] **Step 1: Install Supabase JS client**

```bash
cd frontend && npm install @supabase/supabase-js
```

- [ ] **Step 2: Create Supabase client**

```typescript
// frontend/src/lib/supabase.ts
import { createClient } from '@supabase/supabase-js';
import { PUBLIC_SUPABASE_URL, PUBLIC_SUPABASE_ANON_KEY } from '$env/static/public';

export const supabase = createClient(PUBLIC_SUPABASE_URL, PUBLIC_SUPABASE_ANON_KEY);
```

- [ ] **Step 3: Create auth store**

```typescript
// frontend/src/lib/stores/auth.ts
import { writable, derived } from 'svelte/store';
import type { User, Session } from '@supabase/supabase-js';

export const user = writable<User | null>(null);
export const session = writable<Session | null>(null);
export const authLoading = writable(true);
export const isAuthenticated = derived(user, ($user) => $user !== null);
```

- [ ] **Step 4: Verify build**

```bash
cd frontend && npx svelte-check
```

Expected: No errors.

- [ ] **Step 5: Commit**

```bash
cd frontend
git add src/lib/supabase.ts src/lib/stores/auth.ts package.json package-lock.json
git commit -m "feat: add Supabase client and auth state store"
```

---

## Task 5: Login Page and OAuth Callback

**Files:**
- Create: `frontend/src/routes/login/+page.svelte`
- Create: `frontend/src/routes/auth/callback/+page.svelte`

- [ ] **Step 1: Create login page**

```svelte
<!-- frontend/src/routes/login/+page.svelte -->
<script lang="ts">
	import { supabase } from '$lib/supabase';
	import { isAuthenticated } from '$lib/stores/auth';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';

	let email = $state('');
	let password = $state('');
	let error = $state('');
	let loading = $state(false);
	let isSignUp = $state(false);
	let checkEmail = $state(false);

	const redirectTo = $derived(page.url.searchParams.get('redirect') || '/');

	// If already authenticated, redirect
	$effect(() => {
		if ($isAuthenticated) {
			goto(redirectTo);
		}
	});

	async function handleEmailAuth() {
		error = '';
		loading = true;
		try {
			if (isSignUp) {
				const { error: signUpError } = await supabase.auth.signUp({
					email,
					password,
					options: {
						emailRedirectTo: `${window.location.origin}/auth/callback?redirect=${encodeURIComponent(redirectTo)}`,
					},
				});
				if (signUpError) throw signUpError;
				checkEmail = true;
			} else {
				const { error: signInError } = await supabase.auth.signInWithPassword({
					email,
					password,
				});
				if (signInError) throw signInError;
				goto(redirectTo);
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Authentication failed';
		} finally {
			loading = false;
		}
	}

	async function handleGoogleAuth() {
		error = '';
		const { error: oauthError } = await supabase.auth.signInWithOAuth({
			provider: 'google',
			options: {
				redirectTo: `${window.location.origin}/auth/callback?redirect=${encodeURIComponent(redirectTo)}`,
			},
		});
		if (oauthError) {
			error = oauthError.message;
		}
	}
</script>

<div class="min-h-screen bg-gray-50 flex items-center justify-center px-4">
	<div class="max-w-sm w-full">
		<div class="text-center mb-8">
			<h1 class="text-2xl font-semibold text-gray-800">Kerf</h1>
			<p class="text-sm text-gray-500 mt-1">Sign in to download PDF reports and save projects</p>
		</div>

		{#if checkEmail}
			<div class="bg-white rounded-lg border border-gray-200 p-6 text-center">
				<h2 class="text-lg font-medium text-gray-800 mb-2">Check your email</h2>
				<p class="text-sm text-gray-500">We sent a verification link to <strong>{email}</strong>. Click the link to finish signing up.</p>
			</div>
		{:else}
			<div class="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
				<button
					onclick={handleGoogleAuth}
					class="w-full flex items-center justify-center gap-2 border border-gray-300 rounded-md px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
				>
					<svg class="w-4 h-4" viewBox="0 0 24 24">
						<path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
						<path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
						<path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
						<path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
					</svg>
					Continue with Google
				</button>

				<div class="relative">
					<div class="absolute inset-0 flex items-center"><div class="w-full border-t border-gray-200"></div></div>
					<div class="relative flex justify-center text-xs"><span class="bg-white px-2 text-gray-400">or</span></div>
				</div>

				<form onsubmit={(e) => { e.preventDefault(); handleEmailAuth(); }} class="space-y-3">
					<div>
						<input
							type="email"
							bind:value={email}
							placeholder="Email"
							required
							class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
						/>
					</div>
					<div>
						<input
							type="password"
							bind:value={password}
							placeholder="Password"
							required
							minlength="6"
							class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
						/>
					</div>
					<button
						type="submit"
						disabled={loading}
						class="w-full bg-blue-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
					>
						{loading ? 'Please wait...' : isSignUp ? 'Sign Up' : 'Sign In'}
					</button>
				</form>

				{#if error}
					<p class="text-sm text-red-600">{error}</p>
				{/if}

				<p class="text-center text-xs text-gray-500">
					{#if isSignUp}
						Already have an account? <button class="text-blue-600 hover:underline" onclick={() => (isSignUp = false)}>Sign In</button>
					{:else}
						Don't have an account? <button class="text-blue-600 hover:underline" onclick={() => (isSignUp = true)}>Sign Up</button>
					{/if}
				</p>
			</div>
		{/if}

		<p class="text-center mt-4">
			<a href="/" class="text-sm text-gray-400 hover:text-gray-600">Back to app</a>
		</p>
	</div>
</div>
```

- [ ] **Step 2: Create OAuth callback page**

```svelte
<!-- frontend/src/routes/auth/callback/+page.svelte -->
<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { supabase } from '$lib/supabase';

	let error = $state('');

	onMount(async () => {
		// Supabase handles the token exchange via URL hash/params
		const { error: authError } = await supabase.auth.getSession();
		if (authError) {
			error = authError.message;
			return;
		}

		const redirectTo = page.url.searchParams.get('redirect') || '/';
		goto(redirectTo);
	});
</script>

<div class="min-h-screen bg-gray-50 flex items-center justify-center">
	{#if error}
		<div class="text-center">
			<p class="text-red-600 mb-4">{error}</p>
			<a href="/login" class="text-blue-600 hover:underline text-sm">Try again</a>
		</div>
	{:else}
		<p class="text-gray-500">Completing sign in...</p>
	{/if}
</div>
```

- [ ] **Step 3: Verify build**

```bash
cd frontend && npx svelte-check && npm run build
```

Expected: No errors, build succeeds.

- [ ] **Step 4: Commit**

```bash
cd frontend
git add src/routes/login/+page.svelte src/routes/auth/callback/+page.svelte
git commit -m "feat: add login page with email/password and Google OAuth"
```

---

## Task 6: Wire Auth Into the App

**Files:**
- Modify: `frontend/src/routes/+layout.svelte`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/routes/+page.svelte`
- Modify: `frontend/src/lib/components/Results.svelte`

- [ ] **Step 1: Initialize auth listener in layout**

Replace `frontend/src/routes/+layout.svelte`:

```svelte
<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { supabase } from '$lib/supabase';
	import { user, session, authLoading } from '$lib/stores/auth';

	let { children } = $props();

	onMount(() => {
		// Get initial session
		supabase.auth.getSession().then(({ data }) => {
			session.set(data.session);
			user.set(data.session?.user ?? null);
			authLoading.set(false);
		});

		// Listen for auth changes
		const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, newSession) => {
			session.set(newSession);
			user.set(newSession?.user ?? null);
		});

		return () => subscription.unsubscribe();
	});
</script>

{@render children()}
```

- [ ] **Step 2: Add auth header to API client**

Replace `frontend/src/lib/api.ts`:

```typescript
import type { UploadResponse, AnalyzeRequest, AnalyzeResponse } from './types';
import { get } from 'svelte/store';
import { session } from './stores/auth';

const BASE = '/api';

function authHeaders(): Record<string, string> {
	const headers: Record<string, string> = {};
	const s = get(session);
	if (s?.access_token) {
		headers['Authorization'] = `Bearer ${s.access_token}`;
	}
	return headers;
}

export async function uploadFile(file: File): Promise<UploadResponse> {
	const formData = new FormData();
	formData.append('file', file);
	const response = await fetch(`${BASE}/upload`, {
		method: 'POST',
		body: formData,
		headers: authHeaders(),
	});
	if (!response.ok) {
		const detail = await response.json().catch(() => ({ detail: 'Upload failed' }));
		throw new Error(detail.detail || 'Upload failed');
	}
	return response.json();
}

export async function analyze(request: AnalyzeRequest): Promise<AnalyzeResponse> {
	const response = await fetch(`${BASE}/analyze`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', ...authHeaders() },
		body: JSON.stringify(request),
	});
	if (!response.ok) {
		const detail = await response.json().catch(() => ({ detail: 'Analysis failed' }));
		throw new Error(detail.detail || 'Analysis failed');
	}
	return response.json();
}

export async function getSpecies(): Promise<string[]> {
	const response = await fetch(`${BASE}/species`, { headers: authHeaders() });
	if (!response.ok) throw new Error('Failed to fetch species');
	return response.json();
}

export async function getSheetTypes(): Promise<string[]> {
	const response = await fetch(`${BASE}/sheet-types`, { headers: authHeaders() });
	if (!response.ok) throw new Error('Failed to fetch sheet types');
	return response.json();
}

export async function downloadReport(request: {
	session_id: string;
	solid_species: string;
	sheet_type: string;
	all_solid?: boolean;
	display_units?: string;
	thumbnail?: string | null;
}): Promise<void> {
	const response = await fetch(`${BASE}/report`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', ...authHeaders() },
		body: JSON.stringify(request),
	});
	if (!response.ok) {
		if (response.status === 401) {
			throw new Error('AUTH_REQUIRED');
		}
		const detail = await response.json().catch(() => ({ detail: 'Report generation failed' }));
		throw new Error(detail.detail || 'Report generation failed');
	}
	const blob = await response.blob();
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = 'cut-list-report.pdf';
	a.click();
	URL.revokeObjectURL(url);
}
```

- [ ] **Step 3: Update Results component to show auth state on PDF button**

Update the Props interface and PDF button in `frontend/src/lib/components/Results.svelte`.

Change the Props interface from:

```typescript
interface Props {
    result: AnalyzeResponse;
    onDownloadPdf?: () => void;
    downloadingPdf?: boolean;
}
let { result, onDownloadPdf, downloadingPdf = false }: Props = $props();
```

To:

```typescript
interface Props {
    result: AnalyzeResponse;
    onDownloadPdf?: () => void;
    downloadingPdf?: boolean;
    isAuthenticated?: boolean;
}
let { result, onDownloadPdf, downloadingPdf = false, isAuthenticated = false }: Props = $props();
```

Update the PDF button section (the `{#if onDownloadPdf}` block) to:

```svelte
		{#if onDownloadPdf}
			<button
				onclick={onDownloadPdf}
				disabled={downloadingPdf}
				class="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed">
				{#if downloadingPdf}
					Generating PDF...
				{:else if !isAuthenticated}
					Sign in to Download PDF
				{:else}
					Download PDF
				{/if}
			</button>
		{/if}
```

- [ ] **Step 4: Wire auth into main page**

Replace `frontend/src/routes/+page.svelte`:

```svelte
<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import Upload from '$lib/components/Upload.svelte';
	import ModelViewer, { type ModelViewerApi } from '$lib/components/ModelViewer.svelte';
	import Configure from '$lib/components/Configure.svelte';
	import Results from '$lib/components/Results.svelte';
	import { analyze, downloadReport } from '$lib/api';
	import { isAuthenticated } from '$lib/stores/auth';
	import type { UploadResponse, AnalyzeResponse, DisplayUnits } from '$lib/types';

	let uploadResult = $state<UploadResponse | null>(null);
	let analyzeResult = $state<AnalyzeResponse | null>(null);
	let analyzing = $state(false);
	let downloadingPdf = $state(false);
	let error = $state('');
	let status = $state('');
	let modelApi = $state<ModelViewerApi>();
	let lastConfig = $state<{ solid_species: string; sheet_type: string; all_solid: boolean; display_units: DisplayUnits } | null>(null);

	function handleUpload(result: UploadResponse) {
		uploadResult = result;
		analyzeResult = null;
		error = '';
	}

	async function handleAnalyze(config: { solid_species: string; sheet_type: string; all_solid: boolean; display_units: DisplayUnits; }) {
		if (!uploadResult) return;
		analyzing = true;
		error = '';
		status = 'Parsing model...';
		lastConfig = config;
		try {
			status = 'Analyzing geometry...';
			const result = await analyze({ session_id: uploadResult.session_id, ...config });
			status = '';
			analyzeResult = result;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Analysis failed';
			status = '';
		} finally {
			analyzing = false;
		}
	}

	async function handleDownloadPdf() {
		if (!uploadResult || !lastConfig) return;

		// If not authenticated, redirect to login
		if (!$isAuthenticated) {
			sessionStorage.setItem('pendingAction', 'downloadPdf');
			goto(`/login?redirect=${encodeURIComponent('/')}`);
			return;
		}

		downloadingPdf = true;
		error = '';
		try {
			const thumbnail = modelApi?.captureScreenshot() ?? null;
			await downloadReport({
				session_id: uploadResult.session_id,
				...lastConfig,
				thumbnail,
			});
		} catch (e) {
			const msg = e instanceof Error ? e.message : 'PDF generation failed';
			if (msg === 'AUTH_REQUIRED') {
				sessionStorage.setItem('pendingAction', 'downloadPdf');
				goto(`/login?redirect=${encodeURIComponent('/')}`);
				return;
			}
			error = msg;
		} finally {
			downloadingPdf = false;
		}
	}

	function reset() {
		uploadResult = null;
		analyzeResult = null;
		error = '';
		status = '';
		lastConfig = null;
	}

	// Resume pending action after auth redirect
	onMount(() => {
		const pending = sessionStorage.getItem('pendingAction');
		if (pending === 'downloadPdf' && $isAuthenticated) {
			sessionStorage.removeItem('pendingAction');
			// The user needs to re-analyze first since the session may have expired
			// Just clear the pending action — they'll click PDF again
		}
	});
</script>

<div class="min-h-screen bg-gray-50">
	<header class="bg-white border-b border-gray-200 px-6 py-4">
		<div class="max-w-6xl mx-auto flex items-center justify-between">
			<h1 class="text-xl font-semibold text-gray-800">Kerf</h1>
			<div class="flex items-center gap-4">
				{#if uploadResult}
					<button onclick={reset} class="text-sm text-gray-500 hover:text-gray-700">New Project</button>
				{/if}
				{#if $isAuthenticated}
					<button onclick={() => { import('$lib/supabase').then(m => m.supabase.auth.signOut()); }} class="text-sm text-gray-500 hover:text-gray-700">Sign Out</button>
				{:else}
					<a href="/login" class="text-sm text-blue-600 hover:text-blue-800">Sign In</a>
				{/if}
			</div>
		</div>
	</header>

	<main class="max-w-6xl mx-auto px-6 py-8">
		{#if !uploadResult}
			<div class="max-w-lg mx-auto">
				<h2 class="text-lg font-medium text-gray-700 mb-4">Upload a 3MF File</h2>
				<Upload onUpload={handleUpload} />
			</div>
		{:else}
			<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
				<div class="lg:col-span-1 space-y-6">
					<div>
						<h3 class="text-sm font-medium text-gray-600 mb-2">Model Preview</h3>
						<ModelViewer fileUrl={uploadResult.file_url} bind:api={modelApi} />
						<p class="text-xs text-gray-400 mt-1">{uploadResult.parts_preview.length} part{uploadResult.parts_preview.length !== 1 ? 's' : ''} detected</p>
					</div>
					<div>
						<h3 class="text-sm font-medium text-gray-600 mb-2">Material Settings</h3>
						<Configure onAnalyze={handleAnalyze} {analyzing} />
					</div>
				</div>
				<div class="lg:col-span-2">
					{#if status}
						<div class="flex items-center gap-3 py-12 justify-center text-gray-500">
							<svg class="animate-spin h-5 w-5" viewBox="0 0 24 24">
								<circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" class="opacity-25" />
								<path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" class="opacity-75" />
							</svg>
							<span>{status}</span>
						</div>
					{:else if analyzeResult}
						<Results result={analyzeResult} onDownloadPdf={handleDownloadPdf} {downloadingPdf} isAuthenticated={$isAuthenticated} />
					{:else}
						<div class="text-center py-12 text-gray-400">
							<p>Configure materials and click Analyze to see your cut list.</p>
						</div>
					{/if}
					{#if error}
						<div class="mt-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>
					{/if}
				</div>
			</div>
		{/if}
	</main>
</div>
```

Key changes from previous version:
- Import `isAuthenticated` store and `goto`
- Header now shows "Sign In" / "Sign Out" based on auth state
- App title changed to "Kerf"
- `handleDownloadPdf` checks auth before calling API, redirects to `/login` if needed
- `AUTH_REQUIRED` error from API triggers login redirect
- `onMount` checks for pending action after auth redirect
- Passes `isAuthenticated` prop to Results component

- [ ] **Step 5: Verify frontend builds**

```bash
cd frontend && npx svelte-check && npm run build
```

Expected: No TypeScript errors, build succeeds.

- [ ] **Step 6: Commit**

```bash
cd /home/josebiro/gt/mayor
git add frontend/src/routes/+layout.svelte frontend/src/lib/api.ts \
  frontend/src/routes/+page.svelte frontend/src/lib/components/Results.svelte
git commit -m "feat: wire auth into app — gated PDF, login redirect, auth header, sign in/out"
```

---

## Task 7: End-to-End Verification

**Files:** None — verification only.

- [ ] **Step 1: Run full backend test suite**

```bash
cd backend && source .venv/bin/activate && pytest -v
```

Expected: All tests PASS.

- [ ] **Step 2: Verify frontend builds**

```bash
cd frontend && npm run build
```

Expected: Build succeeds.

- [ ] **Step 3: Enable Google OAuth in Supabase**

In the Supabase dashboard:
1. Go to **Authentication → Providers → Google**
2. Enable it
3. Add Google OAuth credentials (Client ID + Client Secret from Google Cloud Console)
4. Set the redirect URL to `https://amefknuamqfppajprbjr.supabase.co/auth/v1/callback`

This step is manual — no code changes needed.

- [ ] **Step 4: Manual smoke test**

Start both services:
```bash
# Terminal 1
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000

# Terminal 2
cd frontend && npm run dev
```

Test these flows:
1. Upload + analyze works without sign-in
2. Click "Sign in to Download PDF" → redirected to `/login`
3. Sign up with email/password → check email verification works
4. After sign-in, redirected back → "Download PDF" button now says "Download PDF"
5. Click "Download PDF" → PDF downloads
6. "Sign Out" in header → returns to unauthenticated state
7. Header shows "Sign In" link when logged out

- [ ] **Step 5: Commit any fixes and push**

```bash
git add -A && git commit -m "chore: auth integration fixes" && git push
```

(Only if needed.)
