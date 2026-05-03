<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { listProjects, deleteProject } from '$lib/api';
	import { isAuthenticated } from '$lib/stores/auth';
	import type { ProjectSummary } from '$lib/types';

	let projects = $state<ProjectSummary[]>([]);
	let loading = $state(true);
	let error = $state('');

	$effect(() => {
		if (!$isAuthenticated) {
			goto(`/login?redirect=${encodeURIComponent('/projects')}`);
		}
	});

	onMount(async () => {
		if (!$isAuthenticated) return;
		try {
			projects = await listProjects();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load projects';
		} finally {
			loading = false;
		}
	});

	function formatDate(iso: string): string {
		return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
	}

	function formatCost(cost: number | null): string {
		if (cost === null) return 'N/A';
		return `$${cost.toFixed(2)}`;
	}

	async function handleDelete(id: string, name: string) {
		if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;
		try {
			await deleteProject(id);
			projects = projects.filter(p => p.id !== id);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to delete';
		}
	}
</script>

<main class="max-w-6xl mx-auto px-6 py-8">
	<div class="flex items-center justify-between mb-6">
		<h2 class="text-lg font-semibold text-[var(--color-text)]">Projects</h2>
		<a href="/" class="bg-[var(--color-primary)] text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-[var(--color-primary-hover)] transition-colors duration-150">+ New Project</a>
	</div>

	{#if loading}
		<p class="text-[var(--color-text-secondary)]">Loading projects...</p>
	{:else if error}
		<p class="text-[var(--color-destructive)]">{error}</p>
	{:else if projects.length === 0}
		<div class="text-center py-16 text-[var(--color-text-secondary)]">
			<p class="text-lg mb-2">No saved projects yet</p>
			<p class="text-sm">Upload a 3MF file and click "Save Project" to get started.</p>
			<a href="/" class="inline-block mt-4 text-[var(--color-primary)] hover:text-[var(--color-primary-hover)] text-sm transition-colors duration-150">Upload a file</a>
		</div>
	{:else}
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
			{#each projects as project}
				<div class="bg-[var(--color-surface)] rounded-lg border border-[var(--color-border)] overflow-hidden hover:shadow-lg transition-shadow duration-150">
					<button onclick={() => goto(`/?project=${project.id}`)} class="w-full text-left">
						{#if project.thumbnail_url}
							<img src={project.thumbnail_url} alt={project.name} class="w-full h-40 object-cover bg-[var(--color-bg-deep)]" />
						{:else}
							<div class="w-full h-40 bg-[var(--color-bg-deep)] flex items-center justify-center text-[var(--color-text-secondary)] opacity-40 text-sm">No preview</div>
						{/if}
						<div class="p-4">
							<h3 class="font-medium text-[var(--color-text)] truncate">{project.name}</h3>
							<p class="text-xs text-[var(--color-text-secondary)] mt-1">{formatDate(project.created_at)}</p>
							<div class="flex gap-3 mt-2 text-xs text-[var(--color-text-secondary)]">
								<span>{project.part_count} parts</span>
								<span>{project.solid_species}</span>
								<span>{formatCost(project.estimated_cost)}</span>
							</div>
						</div>
					</button>
					<div class="px-4 pb-3">
						<button onclick={() => handleDelete(project.id, project.name)} class="text-xs text-[var(--color-destructive)] hover:opacity-80 transition-colors duration-150">Delete</button>
					</div>
				</div>
			{/each}
			<a href="/" class="bg-[var(--color-surface)] rounded-lg border border-dashed border-[var(--color-border)] flex items-center justify-center min-h-[240px] hover:border-[var(--color-primary)]/50 transition-all duration-150">
				<div class="text-center">
					<div class="text-[var(--color-primary)] text-2xl mb-1">+</div>
					<div class="text-sm text-[var(--color-text-muted)]">New Project</div>
				</div>
			</a>
		</div>
	{/if}
</main>
