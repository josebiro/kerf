import type { UploadResponse, AnalyzeRequest, AnalyzeResponse, ProjectSummary, ProjectDetail, OptimizeRequest, OptimizeResponse, CatalogItem, UserPreferences, Supplier } from './types';
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

export async function restoreSession(projectId: string): Promise<UploadResponse> {
	const response = await fetch(`${BASE}/restore-session`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', ...authHeaders() },
		body: JSON.stringify({ project_id: projectId }),
	});
	if (!response.ok) {
		const detail = await response.json().catch(() => ({ detail: 'Failed to restore session' }));
		throw new Error(detail.detail || 'Failed to restore session');
	}
	return response.json();
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
	analysis_result?: AnalyzeResponse | null;
	optimize_result?: OptimizeResponse | null;
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

export async function saveProject(request: {
	project_id?: string | null;
	name: string;
	filename: string;
	session_id: string;
	solid_species: string;
	sheet_type: string;
	all_solid?: boolean;
	display_units?: string;
	analysis_result: AnalyzeResponse;
	optimize_result?: OptimizeResponse | null;
	thumbnail?: string | null;
}): Promise<{ id: string }> {
	const response = await fetch(`${BASE}/projects`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', ...authHeaders() },
		body: JSON.stringify(request),
	});
	if (!response.ok) {
		if (response.status === 401) throw new Error('AUTH_REQUIRED');
		const detail = await response.json().catch(() => ({ detail: 'Save failed' }));
		throw new Error(detail.detail || 'Save failed');
	}
	return response.json();
}

export async function listProjects(): Promise<ProjectSummary[]> {
	const response = await fetch(`${BASE}/projects`, { headers: authHeaders() });
	if (!response.ok) {
		if (response.status === 401) throw new Error('AUTH_REQUIRED');
		throw new Error('Failed to load projects');
	}
	return response.json();
}

export async function getProjectDetail(id: string): Promise<ProjectDetail> {
	const response = await fetch(`${BASE}/projects/${id}`, { headers: authHeaders() });
	if (!response.ok) {
		if (response.status === 401) throw new Error('AUTH_REQUIRED');
		if (response.status === 404) throw new Error('Project not found');
		throw new Error('Failed to load project');
	}
	return response.json();
}

export async function deleteProject(id: string): Promise<void> {
	const response = await fetch(`${BASE}/projects/${id}`, {
		method: 'DELETE',
		headers: authHeaders(),
	});
	if (!response.ok) {
		if (response.status === 401) throw new Error('AUTH_REQUIRED');
		throw new Error('Failed to delete project');
	}
}

export async function optimizeCuts(request: OptimizeRequest): Promise<OptimizeResponse> {
	const response = await fetch(`${BASE}/optimize`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', ...authHeaders() },
		body: JSON.stringify(request),
	});
	if (!response.ok) {
		const detail = await response.json().catch(() => ({ detail: 'Optimization failed' }));
		throw new Error(detail.detail || 'Optimization failed');
	}
	return response.json();
}

export async function getCatalog(params?: { type?: string; search?: string }): Promise<CatalogItem[]> {
	const searchParams = new URLSearchParams();
	if (params?.type) searchParams.set('type', params.type);
	if (params?.search) searchParams.set('search', params.search);
	const qs = searchParams.toString();
	const response = await fetch(`${BASE}/catalog${qs ? '?' + qs : ''}`, { headers: authHeaders() });
	if (!response.ok) throw new Error('Failed to fetch catalog');
	return response.json();
}

export async function getPreferences(): Promise<UserPreferences> {
	const response = await fetch(`${BASE}/preferences`, { headers: authHeaders() });
	if (!response.ok) throw new Error('Failed to fetch preferences');
	return response.json();
}

export async function updatePreferences(prefs: UserPreferences): Promise<void> {
	const response = await fetch(`${BASE}/preferences`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json', ...authHeaders() },
		body: JSON.stringify(prefs),
	});
	if (!response.ok) throw new Error('Failed to update preferences');
}

export async function getSuppliers(): Promise<Supplier[]> {
	const response = await fetch(`${BASE}/suppliers`, { headers: authHeaders() });
	if (!response.ok) throw new Error('Failed to fetch suppliers');
	return response.json();
}
