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
