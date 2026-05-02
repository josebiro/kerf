<script lang="ts">
	import type { CatalogItem } from '$lib/types';

	interface Props {
		label: string;
		placeholder?: string;
		items: CatalogItem[];
		value: string;
		onSelect: (value: string) => void;
		onBrowseCatalog?: () => void;
		disabled?: boolean;
	}

	let { label, placeholder = 'Search...', items, value, onSelect, onBrowseCatalog, disabled = false }: Props = $props();

	let query = $state('');
	let open = $state(false);
	let highlightIndex = $state(-1);
	let inputEl: HTMLInputElement;

	const filtered = $derived(() => {
		if (!query) return items;
		const q = query.toLowerCase();
		return items.filter(item =>
			item.species_or_name.toLowerCase().includes(q)
		);
	});

	const displayValue = $derived(() => {
		if (open) return query;
		return value || '';
	});

	function handleFocus() {
		open = true;
		query = '';
		highlightIndex = -1;
	}

	function handleBlur() {
		setTimeout(() => { open = false; }, 150);
	}

	function handleInput(e: Event) {
		query = (e.target as HTMLInputElement).value;
		open = true;
		highlightIndex = -1;
	}

	function handleKeydown(e: KeyboardEvent) {
		const list = filtered();
		if (e.key === 'ArrowDown') {
			e.preventDefault();
			highlightIndex = Math.min(highlightIndex + 1, list.length - 1);
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			highlightIndex = Math.max(highlightIndex - 1, 0);
		} else if (e.key === 'Enter' && highlightIndex >= 0 && highlightIndex < list.length) {
			e.preventDefault();
			selectItem(list[highlightIndex]);
		} else if (e.key === 'Escape') {
			open = false;
			inputEl?.blur();
		}
	}

	function selectItem(item: CatalogItem) {
		onSelect(item.species_or_name);
		open = false;
		query = '';
	}

	function supplierBadge(supplierId: string): string {
		const map: Record<string, string> = {
			woodworkers_source: 'WS',
			knotty_lumber: 'KL',
			makerstock: 'MS',
		};
		return map[supplierId] || supplierId.substring(0, 2).toUpperCase();
	}

	function formatPrice(item: CatalogItem): string {
		const unitLabel = item.unit === 'board_foot' ? '/bf' : '/sheet';
		return `$${item.price.toFixed(2)}${unitLabel}`;
	}
</script>

<div class="relative">
	<label class="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider mb-1.5">{label}</label>
	<input
		bind:this={inputEl}
		type="text"
		value={displayValue()}
		{placeholder}
		{disabled}
		onfocus={handleFocus}
		onblur={handleBlur}
		oninput={handleInput}
		onkeydown={handleKeydown}
		class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-md px-3 py-2 text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20 focus:outline-none transition-colors duration-150 disabled:opacity-50"
	/>

	{#if open && !disabled}
		<div class="absolute top-full left-0 right-0 mt-1 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-md shadow-lg shadow-black/40 z-40 max-h-60 overflow-y-auto">
			{#each filtered() as item, i}
				<button
					onmousedown={() => selectItem(item)}
					class="w-full text-left px-3 py-2 text-sm flex items-center justify-between transition-colors duration-75
						{i === highlightIndex ? 'bg-[var(--color-surface-hover)]' : 'hover:bg-[var(--color-surface-hover)]'}"
				>
					<span class="text-[var(--color-text)]">{item.species_or_name}</span>
					<span class="flex items-center gap-2">
						<span class="text-[var(--color-text-muted)] text-xs">{formatPrice(item)}</span>
						<span class="text-[10px] bg-[var(--color-border-strong)] text-[var(--color-text-muted)] px-1.5 py-0.5 rounded">{supplierBadge(item.supplier_id)}</span>
					</span>
				</button>
			{/each}
			{#if filtered().length === 0}
				<div class="px-3 py-2 text-sm text-[var(--color-text-muted)]">No matches</div>
			{/if}
			{#if onBrowseCatalog}
				<div class="border-t border-[var(--color-border)]">
					<button
						onmousedown={onBrowseCatalog}
						class="w-full text-left px-3 py-2 text-xs text-[var(--color-primary)] hover:bg-[var(--color-surface-hover)] transition-colors duration-75"
					>
						Browse Full Catalog
					</button>
				</div>
			{/if}
		</div>
	{/if}
</div>
