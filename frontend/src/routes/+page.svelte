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

	onMount(() => {
		const pending = sessionStorage.getItem('pendingAction');
		if (pending === 'downloadPdf' && $isAuthenticated) {
			sessionStorage.removeItem('pendingAction');
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
