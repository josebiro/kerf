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

<div class="min-h-screen bg-gray-50">
	<header class="bg-white border-b border-gray-200 px-6 py-4">
		<div class="max-w-6xl mx-auto flex items-center justify-between">
			<h1 class="text-xl font-semibold text-gray-800">Kerf</h1>
			<div class="flex items-center gap-4">
				<a href="/" class="text-sm text-blue-600 hover:text-blue-800">New Project</a>
				<button onclick={() => { import('$lib/supabase').then(m => m.supabase.auth.signOut().then(() => goto('/'))); }} class="text-sm text-gray-500 hover:text-gray-700">Sign Out</button>
			</div>
		</div>
	</header>

	<main class="max-w-6xl mx-auto px-6 py-8">
		<h2 class="text-lg font-medium text-gray-700 mb-6">My Projects</h2>

		{#if loading}
			<p class="text-gray-500">Loading projects...</p>
		{:else if error}
			<p class="text-red-600">{error}</p>
		{:else if projects.length === 0}
			<div class="text-center py-16 text-gray-400">
				<p class="text-lg mb-2">No saved projects yet</p>
				<p class="text-sm">Upload a 3MF file and click "Save Project" to get started.</p>
				<a href="/" class="inline-block mt-4 text-blue-600 hover:text-blue-800 text-sm">Upload a file</a>
			</div>
		{:else}
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
				{#each projects as project}
					<div class="bg-white rounded-lg border border-gray-200 overflow-hidden hover:shadow-md transition-shadow">
						<button onclick={() => goto(`/?project=${project.id}`)} class="w-full text-left">
							{#if project.thumbnail_url}
								<img src={project.thumbnail_url} alt={project.name} class="w-full h-40 object-cover bg-gray-100" />
							{:else}
								<div class="w-full h-40 bg-gray-100 flex items-center justify-center text-gray-300 text-sm">No preview</div>
							{/if}
							<div class="p-4">
								<h3 class="font-medium text-gray-800 truncate">{project.name}</h3>
								<p class="text-xs text-gray-400 mt-1">{formatDate(project.created_at)}</p>
								<div class="flex gap-3 mt-2 text-xs text-gray-500">
									<span>{project.part_count} parts</span>
									<span>{project.solid_species}</span>
									<span>{formatCost(project.estimated_cost)}</span>
								</div>
							</div>
						</button>
						<div class="px-4 pb-3">
							<button onclick={() => handleDelete(project.id, project.name)} class="text-xs text-red-500 hover:text-red-700">Delete</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</main>
</div>
