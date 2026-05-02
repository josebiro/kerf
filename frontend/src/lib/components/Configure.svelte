<script lang="ts">
	import { onMount } from 'svelte';
	import { getCatalog } from '$lib/api';
	import Combobox from './Combobox.svelte';
	import CatalogBrowser from './CatalogBrowser.svelte';
	import type { DisplayUnits, CatalogItem } from '$lib/types';

	interface Props {
		onAnalyze: (config: { solid_species: string; sheet_type: string; all_solid: boolean; display_units: DisplayUnits; }) => void;
		analyzing: boolean;
		initialConfig?: { solid_species: string; sheet_type: string; all_solid: boolean; display_units: DisplayUnits } | null;
	}

	let { onAnalyze, analyzing, initialConfig = null }: Props = $props();

	let allItems = $state<CatalogItem[]>([]);
	let solidSpecies = $state(initialConfig?.solid_species || '');
	let sheetType = $state(initialConfig?.sheet_type || '');
	let allSolid = $state(initialConfig?.all_solid || false);
	let displayUnits = $state<DisplayUnits>(initialConfig?.display_units || 'in');
	let loading = $state(true);
	let catalogOpen = $state(false);
	let catalogTab = $state<'solid' | 'sheet'>('solid');

	const solidItems = $derived(allItems.filter(i => i.product_type === 'solid'));
	const sheetItems = $derived(allItems.filter(i => i.product_type === 'sheet'));

	const uniqueSolidItems = $derived(() => {
		const seen = new Map<string, CatalogItem>();
		for (const item of solidItems) {
			if (!seen.has(item.species_or_name) || item.price < seen.get(item.species_or_name)!.price) {
				seen.set(item.species_or_name, item);
			}
		}
		return Array.from(seen.values());
	});

	const uniqueSheetItems = $derived(() => {
		const seen = new Map<string, CatalogItem>();
		for (const item of sheetItems) {
			if (!seen.has(item.species_or_name) || item.price < seen.get(item.species_or_name)!.price) {
				seen.set(item.species_or_name, item);
			}
		}
		return Array.from(seen.values());
	});

	onMount(async () => {
		try {
			allItems = await getCatalog();
			if (!solidSpecies && solidItems.length > 0) {
				solidSpecies = solidItems[0].species_or_name;
			}
			if (!sheetType && sheetItems.length > 0) {
				sheetType = sheetItems[0].species_or_name;
			}
		} catch (e) {
			// Fallback to empty
		} finally {
			loading = false;
		}
	});

	function handleSubmit() {
		onAnalyze({ solid_species: solidSpecies, sheet_type: sheetType, all_solid: allSolid, display_units: displayUnits });
	}

	function openCatalog(tab: 'solid' | 'sheet') {
		catalogTab = tab;
		catalogOpen = true;
	}
</script>

<div class="space-y-4">
	{#if loading}
		<p class="text-[var(--color-text-secondary)] text-sm">Loading materials...</p>
	{:else}
		<Combobox
			label="Solid Lumber Species"
			placeholder="Search species..."
			items={uniqueSolidItems()}
			value={solidSpecies}
			onSelect={(v) => (solidSpecies = v)}
			onBrowseCatalog={() => openCatalog('solid')}
		/>

		<Combobox
			label="Sheet Goods"
			placeholder="Search sheets..."
			items={uniqueSheetItems()}
			value={sheetType}
			onSelect={(v) => (sheetType = v)}
			onBrowseCatalog={() => openCatalog('sheet')}
			disabled={allSolid}
		/>

		<div class="flex items-center gap-3">
			<label class="relative inline-flex items-center cursor-pointer">
				<input type="checkbox" bind:checked={allSolid} class="sr-only peer" />
				<div class="w-9 h-5 bg-[var(--color-border)] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[var(--color-primary)]"></div>
			</label>
			<span class="text-sm text-[var(--color-text)]">All solid lumber (no sheet goods)</span>
		</div>

		<div class="flex items-center gap-3">
			<span class="text-sm text-[var(--color-text)]">Display Units</span>
			<div class="flex gap-1">
				<button class="px-3 py-1 text-sm rounded transition-colors duration-150 {displayUnits === 'in' ? 'bg-[var(--color-primary)] text-white' : 'bg-[var(--color-border-strong)] text-[var(--color-text-secondary)]'}" onclick={() => (displayUnits = 'in')}>in</button>
				<button class="px-3 py-1 text-sm rounded transition-colors duration-150 {displayUnits === 'mm' ? 'bg-[var(--color-primary)] text-white' : 'bg-[var(--color-border-strong)] text-[var(--color-text-secondary)]'}" onclick={() => (displayUnits = 'mm')}>mm</button>
			</div>
		</div>

		<button onclick={handleSubmit} disabled={analyzing}
			class="w-full bg-[var(--color-primary)] text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-[var(--color-primary-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150">
			{analyzing ? 'Analyzing...' : 'Analyze'}
		</button>
	{/if}
</div>

<CatalogBrowser
	items={allItems}
	open={catalogOpen}
	onClose={() => (catalogOpen = false)}
	onSelect={(v) => {
		if (catalogTab === 'solid') solidSpecies = v;
		else sheetType = v;
	}}
	initialTab={catalogTab}
/>
