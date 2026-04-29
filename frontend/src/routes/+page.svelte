<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import Upload from '$lib/components/Upload.svelte';
	import ModelViewer, { type ModelViewerApi } from '$lib/components/ModelViewer.svelte';
	import Configure from '$lib/components/Configure.svelte';
	import Results from '$lib/components/Results.svelte';
	import { analyze, downloadReport, saveProject, getProjectDetail, optimizeCuts, restoreSession } from '$lib/api';
	import { isAuthenticated } from '$lib/stores/auth';
	import type { UploadResponse, AnalyzeResponse, DisplayUnits, OptimizeResponse, BufferConfig, BoardSizeConfig, SheetSizeConfig } from '$lib/types';

	let uploadResult = $state<UploadResponse | null>(null);
	let analyzeResult = $state<AnalyzeResponse | null>(null);
	let optimizeResult = $state<OptimizeResponse | null>(null);
	let analyzing = $state(false);
	let optimizing = $state(false);
	let downloadingPdf = $state(false);
	let savingProject = $state(false);
	let projectSaved = $state(false);
	let loadedProjectId = $state<string | null>(null);
	let error = $state('');
	let status = $state('');
	let modelApi = $state<ModelViewerApi>();
	let lastConfig = $state<{ solid_species: string; sheet_type: string; all_solid: boolean; display_units: DisplayUnits } | null>(null);

	function handleUpload(result: UploadResponse) {
		uploadResult = result;
		analyzeResult = null;
		optimizeResult = null;
		error = '';
		projectSaved = false;
	}

	async function handleAnalyze(config: { solid_species: string; sheet_type: string; all_solid: boolean; display_units: DisplayUnits; }) {
		if (!uploadResult) return;
		analyzing = true;
		error = '';
		status = 'Parsing model...';
		lastConfig = config;
		projectSaved = false;
		try {
			status = 'Analyzing geometry...';
			const result = await analyze({ session_id: uploadResult.session_id, ...config });
			status = '';
			analyzeResult = result;

			// Auto-optimize
			optimizing = true;
			try {
				optimizeResult = await optimizeCuts({
					parts: result.parts,
					shopping_list: result.shopping_list,
					solid_species: config.solid_species,
					sheet_type: config.sheet_type,
				});
			} catch (e) {
				// Optimization is optional — don't show error
				optimizeResult = null;
			} finally {
				optimizing = false;
			}
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
				analysis_result: !uploadResult.session_id ? analyzeResult : null,
				optimize_result: optimizeResult,
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

	async function handleSaveProject() {
		if (!uploadResult || !lastConfig || !analyzeResult) return;
		if (!$isAuthenticated) {
			goto(`/login?redirect=${encodeURIComponent('/')}`);
			return;
		}
		savingProject = true;
		error = '';
		try {
			const thumbnail = modelApi?.captureScreenshot() ?? null;
			const name = uploadResult.file_url.split('/').pop()?.replace('.3mf', '') || 'Untitled';
			const result = await saveProject({
				project_id: loadedProjectId,
				name,
				filename: uploadResult.file_url.split('/').pop() || 'model.3mf',
				session_id: uploadResult.session_id,
				...lastConfig,
				analysis_result: analyzeResult,
				optimize_result: optimizeResult,
				thumbnail,
			});
			loadedProjectId = result.id;
			projectSaved = true;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Save failed';
		} finally {
			savingProject = false;
		}
	}

	async function handleReoptimize(bufferConfig: BufferConfig, boardSizes: Record<string, BoardSizeConfig>, sheetSize?: SheetSizeConfig) {
		if (!analyzeResult || !lastConfig) return;
		optimizing = true;
		try {
			optimizeResult = await optimizeCuts({
				parts: analyzeResult.parts,
				shopping_list: analyzeResult.shopping_list,
				solid_species: lastConfig.solid_species,
				sheet_type: lastConfig.sheet_type,
				buffer_config: bufferConfig,
				board_sizes: boardSizes,
				sheet_size: sheetSize,
			});
			projectSaved = false; // mark unsaved after re-optimization
		} catch (e) {
			error = e instanceof Error ? e.message : 'Optimization failed';
		} finally {
			optimizing = false;
		}
	}

	function reset() {
		uploadResult = null;
		analyzeResult = null;
		optimizeResult = null;
		error = '';
		status = '';
		lastConfig = null;
		projectSaved = false;
		loadedProjectId = null;
		if (page.url.searchParams.has('project')) {
			goto('/', { replaceState: true });
		}
	}

	onMount(async () => {
		const projectId = page.url.searchParams.get('project');
		if (projectId && $isAuthenticated) {
			try {
				status = 'Loading project...';
				const project = await getProjectDetail(projectId);
				analyzeResult = project.analysis_result;
				lastConfig = {
					solid_species: project.solid_species,
					sheet_type: project.sheet_type,
					all_solid: project.all_solid,
					display_units: project.display_units,
				};

				// Restore a local session so analyze/report endpoints work
				status = 'Restoring session...';
				const restored = await restoreSession(project.file_url, project.filename);
				uploadResult = restored;
				optimizeResult = project.optimize_result;
				loadedProjectId = project.id;

				projectSaved = true;
				status = '';
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to load project';
				status = '';
			}
		}

		const pending = sessionStorage.getItem('pendingAction');
		if (pending === 'downloadPdf' && $isAuthenticated) {
			sessionStorage.removeItem('pendingAction');
		}
	});
</script>

<div class="min-h-screen bg-[var(--color-bg)]">
	<header class="bg-[var(--color-surface)] border-b border-[var(--color-border)] px-6 py-4">
		<div class="max-w-6xl mx-auto flex items-center justify-between">
			<h1 class="text-xl text-[var(--color-primary)] font-['DM_Serif_Display',serif]">Kerf</h1>
			<div class="flex items-center gap-4">
				{#if $isAuthenticated}
					<a href="/projects" class="text-sm text-[var(--color-foreground-muted)] hover:text-[var(--color-foreground)] transition-colors duration-150">My Projects</a>
				{/if}
				{#if uploadResult}
					<button onclick={reset} class="text-sm text-[var(--color-foreground-muted)] hover:text-[var(--color-foreground)] transition-colors duration-150">New Project</button>
				{/if}
				{#if $isAuthenticated}
					<button onclick={() => { import('$lib/supabase').then(m => m.supabase.auth.signOut()); }} class="text-sm text-[var(--color-foreground-muted)] hover:text-[var(--color-foreground)] transition-colors duration-150">Sign Out</button>
				{:else}
					<a href="/login" class="text-sm text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] transition-colors duration-150">Sign In</a>
				{/if}
			</div>
		</div>
	</header>

	<main class="max-w-6xl mx-auto px-6 py-8">
		{#if !uploadResult}
			<div class="max-w-lg mx-auto">
				<h2 class="text-lg font-medium text-[var(--color-foreground)] mb-4">Upload a 3MF File</h2>
				<Upload onUpload={handleUpload} />
			</div>
		{:else}
			<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
				<div class="lg:col-span-1 space-y-6">
					<div>
						<h3 class="text-sm font-medium text-[var(--color-foreground-muted)] mb-2">Model Preview</h3>
						<ModelViewer fileUrl={uploadResult.file_url} bind:api={modelApi} />
						<p class="text-xs text-[var(--color-foreground-muted)] opacity-60 mt-1">{uploadResult.parts_preview.length} part{uploadResult.parts_preview.length !== 1 ? 's' : ''} detected</p>
					</div>
					<div>
						<h3 class="text-sm font-medium text-[var(--color-foreground-muted)] mb-2">Material Settings</h3>
						<Configure onAnalyze={handleAnalyze} {analyzing} initialConfig={lastConfig} />
					</div>
				</div>
				<div class="lg:col-span-2">
					{#if status}
						<div class="flex items-center gap-3 py-12 justify-center text-[var(--color-foreground-muted)]">
							<svg class="animate-spin h-5 w-5" viewBox="0 0 24 24">
								<circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" class="opacity-25" />
								<path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" class="opacity-75" />
							</svg>
							<span>{status}</span>
						</div>
					{:else if analyzeResult}
						<Results result={analyzeResult} onDownloadPdf={handleDownloadPdf} {downloadingPdf} isAuthenticated={$isAuthenticated} onSaveProject={handleSaveProject} {savingProject} {projectSaved} {optimizeResult} onReoptimize={handleReoptimize} {optimizing} />
					{:else}
						<div class="text-center py-12 text-[var(--color-foreground-muted)]">
							<p>Configure materials and click Analyze to see your cut list.</p>
						</div>
					{/if}
					{#if error}
						<div class="mt-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-[var(--color-destructive)]">{error}</div>
					{/if}
				</div>
			</div>
		{/if}
	</main>
</div>
