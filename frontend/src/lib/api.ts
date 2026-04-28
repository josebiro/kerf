import type { UploadResponse, AnalyzeRequest, AnalyzeResponse } from './types';

const BASE = '/api';

export async function uploadFile(file: File): Promise<UploadResponse> {
	const formData = new FormData();
	formData.append('file', file);
	const response = await fetch(`${BASE}/upload`, { method: 'POST', body: formData });
	if (!response.ok) {
		const detail = await response.json().catch(() => ({ detail: 'Upload failed' }));
		throw new Error(detail.detail || 'Upload failed');
	}
	return response.json();
}

export async function analyze(request: AnalyzeRequest): Promise<AnalyzeResponse> {
	const response = await fetch(`${BASE}/analyze`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(request),
	});
	if (!response.ok) {
		const detail = await response.json().catch(() => ({ detail: 'Analysis failed' }));
		throw new Error(detail.detail || 'Analysis failed');
	}
	return response.json();
}

export async function getSpecies(): Promise<string[]> {
	const response = await fetch(`${BASE}/species`);
	if (!response.ok) throw new Error('Failed to fetch species');
	return response.json();
}

export async function getSheetTypes(): Promise<string[]> {
	const response = await fetch(`${BASE}/sheet-types`);
	if (!response.ok) throw new Error('Failed to fetch sheet types');
	return response.json();
}
