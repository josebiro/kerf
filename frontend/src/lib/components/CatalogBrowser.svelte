<script lang="ts">
	import type { CatalogItem } from '$lib/types';

	interface Props {
		items: CatalogItem[];
		open: boolean;
		onClose: () => void;
		onSelect: (species: string) => void;
		initialTab?: 'solid' | 'sheet';
	}

	let { items, open, onClose, onSelect, initialTab = 'solid' }: Props = $props();

	let activeTab = $state<'solid' | 'sheet'>(initialTab);
	let search = $state('');
	let supplierFilter = $state<string>('');

	const filteredItems = $derived(() => {
		let result = items.filter(i => i.product_type === activeTab);
		if (supplierFilter) {
			result = result.filter(i => i.supplier_id === supplierFilter);
		}
		if (search) {
			const q = search.toLowerCase();
			result = result.filter(i => i.species_or_name.toLowerCase().includes(q));
		}
		return result;
	});

	const uniqueSuppliers = $derived(() => {
		const seen = new Map<string, string>();
		for (const item of items) {
			if (!seen.has(item.supplier_id)) {
				seen.set(item.supplier_id, item.supplier_name);
			}
		}
		return Array.from(seen.entries()).map(([id, name]) => ({ id, name }));
	});

	function supplierBadge(supplierId: string): string {
		const map: Record<string, string> = {
			woodworkers_source: 'WS',
			knotty_lumber: 'KL',
			makerstock: 'MS',
		};
		return map[supplierId] || supplierId.substring(0, 2).toUpperCase();
	}

	function handleSelect(species: string) {
		onSelect(species);
		onClose();
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') onClose();
	}
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
	<div class="fixed inset-0 bg-black/50 z-40" onclick={onClose}></div>

	<div class="fixed inset-y-0 right-0 w-full max-w-lg bg-[var(--color-bg)] border-l border-[var(--color-border-strong)] shadow-2xl z-50 flex flex-col">
		<div class="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border-strong)]">
			<h2 class="text-sm font-semibold text-[var(--color-text)]">Material Catalog</h2>
			<button onclick={onClose} class="text-[var(--color-text-muted)] hover:text-[var(--color-text)] text-lg">&times;</button>
		</div>

		<div class="px-4 py-3 border-b border-[var(--color-border-strong)] flex items-center gap-3">
			<div class="flex gap-1">
				<button
					onclick={() => (activeTab = 'solid')}
					class="px-3 py-1 text-xs font-medium rounded transition-colors duration-150
						{activeTab === 'solid' ? 'bg-[var(--color-primary)] text-white' : 'bg-[var(--color-border-strong)] text-[var(--color-text-secondary)]'}"
				>Solid</button>
				<button
					onclick={() => (activeTab = 'sheet')}
					class="px-3 py-1 text-xs font-medium rounded transition-colors duration-150
						{activeTab === 'sheet' ? 'bg-[var(--color-primary)] text-white' : 'bg-[var(--color-border-strong)] text-[var(--color-text-secondary)]'}"
				>Sheet</button>
			</div>
			<input
				type="text"
				bind:value={search}
				placeholder="Filter..."
				class="flex-1 bg-[var(--color-surface)] border border-[var(--color-border)] rounded px-2 py-1 text-xs text-[var(--color-text)] placeholder:text-[var(--color-text-muted)]"
			/>
			<select
				bind:value={supplierFilter}
				class="bg-[var(--color-surface)] border border-[var(--color-border)] rounded px-2 py-1 text-xs text-[var(--color-text)]"
			>
				<option value="">All suppliers</option>
				{#each uniqueSuppliers() as s}
					<option value={s.id}>{s.name}</option>
				{/each}
			</select>
		</div>

		<div class="flex-1 overflow-y-auto">
			<table class="w-full text-xs">
				<thead class="sticky top-0 bg-[var(--color-bg-deep)]">
					<tr class="border-b border-[var(--color-border-strong)]">
						<th class="text-left px-4 py-2 text-[var(--color-text-muted)] uppercase tracking-wider font-medium">Species</th>
						<th class="text-left px-2 py-2 text-[var(--color-text-muted)] uppercase tracking-wider font-medium">Price</th>
						<th class="text-left px-2 py-2 text-[var(--color-text-muted)] uppercase tracking-wider font-medium">Thickness</th>
						<th class="text-left px-2 py-2 text-[var(--color-text-muted)] uppercase tracking-wider font-medium">Supplier</th>
					</tr>
				</thead>
				<tbody>
					{#each filteredItems() as item}
						<tr
							onclick={() => handleSelect(item.species_or_name)}
							class="border-b border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-surface-hover)] transition-colors duration-75"
						>
							<td class="px-4 py-2.5 text-[var(--color-text)] font-medium">{item.species_or_name}</td>
							<td class="px-2 py-2.5 text-[var(--color-text-secondary)]">${item.price.toFixed(2)}</td>
							<td class="px-2 py-2.5 text-[var(--color-text-secondary)]">{item.thickness}</td>
							<td class="px-2 py-2.5">
								<span class="text-[10px] bg-[var(--color-border-strong)] text-[var(--color-text-muted)] px-1.5 py-0.5 rounded">{supplierBadge(item.supplier_id)}</span>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
			{#if filteredItems().length === 0}
				<div class="text-center py-8 text-[var(--color-text-muted)] text-sm">No materials found</div>
			{/if}
		</div>
	</div>
{/if}
