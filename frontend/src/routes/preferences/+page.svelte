<script lang="ts">
	import { onMount } from 'svelte';
	import { getPreferences, updatePreferences, getSuppliers, getCatalog } from '$lib/api';
	import Combobox from '$lib/components/Combobox.svelte';
	import type { UserPreferences, Supplier, CatalogItem, DisplayUnits } from '$lib/types';

	let suppliers = $state<Supplier[]>([]);
	let prefs = $state<UserPreferences>({
		enabled_suppliers: ['woodworkers_source'],
		default_species: null,
		default_sheet_type: null,
		default_units: 'in',
	});
	let catalogItems = $state<CatalogItem[]>([]);
	let loading = $state(true);
	let saving = $state(false);
	let saved = $state(false);

	const solidItems = $derived(() => {
		const seen = new Map<string, CatalogItem>();
		for (const item of catalogItems.filter(i => i.product_type === 'solid')) {
			if (!seen.has(item.species_or_name)) seen.set(item.species_or_name, item);
		}
		return Array.from(seen.values());
	});

	const sheetItems = $derived(() => {
		const seen = new Map<string, CatalogItem>();
		for (const item of catalogItems.filter(i => i.product_type === 'sheet')) {
			if (!seen.has(item.species_or_name)) seen.set(item.species_or_name, item);
		}
		return Array.from(seen.values());
	});

	onMount(async () => {
		try {
			const [p, s, c] = await Promise.all([getPreferences(), getSuppliers(), getCatalog()]);
			prefs = p;
			suppliers = s;
			catalogItems = c;
		} catch (e) {
			// Use defaults
		} finally {
			loading = false;
		}
	});

	function toggleSupplier(supplierId: string) {
		if (prefs.enabled_suppliers.includes(supplierId)) {
			prefs.enabled_suppliers = prefs.enabled_suppliers.filter(s => s !== supplierId);
		} else {
			prefs.enabled_suppliers = [...prefs.enabled_suppliers, supplierId];
		}
		saved = false;
	}

	async function handleSave() {
		saving = true;
		try {
			await updatePreferences(prefs);
			saved = true;
			setTimeout(() => (saved = false), 2000);
		} catch (e) {
			// Handle error
		} finally {
			saving = false;
		}
	}
</script>

<div class="max-w-2xl">
	<h2 class="text-lg font-semibold text-[var(--color-text)] mb-6">Preferences</h2>

	{#if loading}
		<p class="text-[var(--color-text-secondary)]">Loading...</p>
	{:else}
		<div class="mb-8">
			<h3 class="text-sm font-semibold text-[var(--color-text)] mb-3">Lumber Suppliers</h3>
			<div class="space-y-2">
				{#each suppliers as supplier}
					<div class="flex items-center justify-between bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-4 py-3">
						<div>
							<div class="text-sm font-medium text-[var(--color-text)]">{supplier.name}</div>
							<div class="text-xs text-[var(--color-text-muted)]">{supplier.base_url}</div>
						</div>
						<label class="relative inline-flex items-center cursor-pointer">
							<input
								type="checkbox"
								checked={prefs.enabled_suppliers.includes(supplier.supplier_id)}
								onchange={() => toggleSupplier(supplier.supplier_id)}
								class="sr-only peer"
							/>
							<div class="w-9 h-5 bg-[var(--color-border)] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[var(--color-primary)]"></div>
						</label>
					</div>
				{/each}
			</div>
		</div>

		<div class="mb-8">
			<h3 class="text-sm font-semibold text-[var(--color-text)] mb-3">Default Materials</h3>
			<div class="space-y-4">
				<Combobox
					label="Default Species"
					placeholder="Select default species..."
					items={solidItems()}
					value={prefs.default_species || ''}
					onSelect={(v) => { prefs.default_species = v; saved = false; }}
				/>
				<Combobox
					label="Default Sheet Type"
					placeholder="Select default sheet type..."
					items={sheetItems()}
					value={prefs.default_sheet_type || ''}
					onSelect={(v) => { prefs.default_sheet_type = v; saved = false; }}
				/>
				<div>
					<label class="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider mb-1.5">Display Units</label>
					<div class="flex gap-1">
						<button
							class="px-3 py-1 text-sm rounded transition-colors duration-150 {prefs.default_units === 'in' ? 'bg-[var(--color-primary)] text-white' : 'bg-[var(--color-border-strong)] text-[var(--color-text-secondary)]'}"
							onclick={() => { prefs.default_units = 'in'; saved = false; }}
						>in</button>
						<button
							class="px-3 py-1 text-sm rounded transition-colors duration-150 {prefs.default_units === 'mm' ? 'bg-[var(--color-primary)] text-white' : 'bg-[var(--color-border-strong)] text-[var(--color-text-secondary)]'}"
							onclick={() => { prefs.default_units = 'mm'; saved = false; }}
						>mm</button>
					</div>
				</div>
			</div>
		</div>

		<button
			onclick={handleSave}
			disabled={saving}
			class="bg-[var(--color-primary)] text-white px-6 py-2 rounded-md text-sm font-medium hover:bg-[var(--color-primary-hover)] disabled:opacity-50 transition-colors duration-150"
		>
			{#if saving}
				Saving...
			{:else if saved}
				Saved
			{:else}
				Save Preferences
			{/if}
		</button>
	{/if}
</div>
