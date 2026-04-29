<script lang="ts">
	import { onMount } from 'svelte';
	import { getSpecies, getSheetTypes } from '$lib/api';
	import type { DisplayUnits } from '$lib/types';

	interface Props {
		onAnalyze: (config: { solid_species: string; sheet_type: string; all_solid: boolean; display_units: DisplayUnits; }) => void;
		analyzing: boolean;
		initialConfig?: { solid_species: string; sheet_type: string; all_solid: boolean; display_units: DisplayUnits } | null;
	}

	let { onAnalyze, analyzing, initialConfig = null }: Props = $props();
	let speciesList = $state<string[]>([]);
	let sheetTypesList = $state<string[]>([]);
	let solidSpecies = $state(initialConfig?.solid_species || '');
	let sheetType = $state(initialConfig?.sheet_type || '');
	let allSolid = $state(initialConfig?.all_solid || false);
	let displayUnits = $state<DisplayUnits>(initialConfig?.display_units || 'in');
	let loading = $state(true);

	onMount(async () => {
		const [species, sheets] = await Promise.all([getSpecies(), getSheetTypes()]);
		speciesList = species;
		sheetTypesList = sheets;
		// Only use defaults if no initial config was provided
		if (!solidSpecies) solidSpecies = species[0] || '';
		if (!sheetType) sheetType = sheets[0] || '';
		loading = false;
	});

	function handleSubmit() {
		onAnalyze({ solid_species: solidSpecies, sheet_type: sheetType, all_solid: allSolid, display_units: displayUnits });
	}
</script>

<div class="space-y-4">
	{#if loading}
		<p class="text-gray-500">Loading material options...</p>
	{:else}
		<div>
			<label for="species" class="block text-sm font-medium text-gray-700 mb-1">Solid Lumber Species</label>
			<select id="species" bind:value={solidSpecies} class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm">
				{#each speciesList as s}
					<option value={s}>{s}</option>
				{/each}
			</select>
		</div>
		<div>
			<label for="sheet-type" class="block text-sm font-medium text-gray-700 mb-1">Sheet Good Type</label>
			<select id="sheet-type" bind:value={sheetType} disabled={allSolid}
				class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm {allSolid ? 'opacity-50' : ''}">
				{#each sheetTypesList as t}
					<option value={t}>{t}</option>
				{/each}
			</select>
		</div>
		<div class="flex items-center gap-3">
			<label class="relative inline-flex items-center cursor-pointer">
				<input type="checkbox" bind:checked={allSolid} class="sr-only peer" />
				<div class="w-9 h-5 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
			</label>
			<span class="text-sm text-gray-700">All solid lumber (no sheet goods)</span>
		</div>
		<div class="flex items-center gap-3">
			<span class="text-sm text-gray-700">Display Units</span>
			<div class="flex gap-1">
				<button class="px-3 py-1 text-sm rounded {displayUnits === 'in' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-600'}" onclick={() => (displayUnits = 'in')}>in</button>
				<button class="px-3 py-1 text-sm rounded {displayUnits === 'mm' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-600'}" onclick={() => (displayUnits = 'mm')}>mm</button>
			</div>
		</div>
		<button onclick={handleSubmit} disabled={analyzing}
			class="w-full bg-blue-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed">
			{analyzing ? 'Analyzing...' : 'Analyze'}
		</button>
	{/if}
</div>
