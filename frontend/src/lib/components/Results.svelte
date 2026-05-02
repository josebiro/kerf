<script lang="ts">
	import type { AnalyzeResponse, Part, DisplayUnits, OptimizeResponse, BufferConfig, BoardSizeConfig, SheetSizeConfig } from '$lib/types';
	import CutLayout from './CutLayout.svelte';

	interface Props {
		result: AnalyzeResponse;
		onDownloadPdf?: () => void;
		downloadingPdf?: boolean;
		isAuthenticated?: boolean;
		onSaveProject?: () => void;
		savingProject?: boolean;
		projectSaved?: boolean;
		optimizeResult?: OptimizeResponse | null;
		onReoptimize?: (config: BufferConfig, sizes: Record<string, BoardSizeConfig>, sheetSize?: SheetSizeConfig) => void;
		optimizing?: boolean;
	}
	let { result, onDownloadPdf, downloadingPdf = false, isAuthenticated = false, onSaveProject, savingProject = false, projectSaved = false, optimizeResult = null, onReoptimize, optimizing = false }: Props = $props();
	let activeTab = $state<'parts' | 'shopping' | 'cost' | 'cutlayout'>('parts');

	const costItems = $derived(optimizeResult?.updated_shopping_list ?? result.cost_estimate.items);
	const costTotal = $derived(() => {
		const subtotals = costItems.filter(i => i.subtotal !== null).map(i => i.subtotal!);
		return subtotals.length > 0 ? subtotals.reduce((a, b) => a + b, 0) : null;
	});
	const hasMissingPrices = $derived(costItems.some(i => i.subtotal === null));

	function formatDimensions(part: Part, units: DisplayUnits): string {
		if (units === 'mm') return `${part.length_mm} × ${part.width_mm} × ${part.thickness_mm} mm`;
		const l = (part.length_mm / 25.4).toFixed(2);
		const w = (part.width_mm / 25.4).toFixed(2);
		const t = (part.thickness_mm / 25.4).toFixed(2);
		return `${l}" × ${w}" × ${t}"`;
	}

	function formatPrice(value: number | null): string {
		if (value === null) return '—';
		return `$${value.toFixed(2)}`;
	}

	function exportCsv() {
		const lines = ['Part,Qty,Dimensions,Type,Stock,Notes'];
		for (const part of result.parts) {
			const dims = formatDimensions(part, result.display_units);
			lines.push(`"${part.name}",${part.quantity},"${dims}",${part.board_type},"${part.stock}","${part.notes}"`);
		}
		lines.push('');
		lines.push('Material,Thickness,Qty,Unit,Unit Price,Subtotal');
		for (const item of result.shopping_list) {
			lines.push(`"${item.material}","${item.thickness}",${item.quantity},${item.unit},${formatPrice(item.unit_price)},${formatPrice(item.subtotal)}`);
		}
		if (result.cost_estimate.total !== null) {
			lines.push(`,,,,Total,${formatPrice(result.cost_estimate.total)}`);
		}
		const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = 'cut-list.csv';
		a.click();
		URL.revokeObjectURL(url);
	}
</script>

<div>
	<div class="flex gap-1 mb-4 border-b border-[var(--color-border)]">
		<button class="px-4 py-2 text-sm transition-colors duration-150 {activeTab === 'parts' ? 'border-b-2 border-[var(--color-primary)] text-[var(--color-primary)] font-medium' : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'}" onclick={() => (activeTab = 'parts')}>Parts List</button>
		<button class="px-4 py-2 text-sm transition-colors duration-150 {activeTab === 'shopping' ? 'border-b-2 border-[var(--color-primary)] text-[var(--color-primary)] font-medium' : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'}" onclick={() => (activeTab = 'shopping')}>Shopping List</button>
		<button class="px-4 py-2 text-sm transition-colors duration-150 {activeTab === 'cost' ? 'border-b-2 border-[var(--color-primary)] text-[var(--color-primary)] font-medium' : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'}" onclick={() => (activeTab = 'cost')}>Cost Estimate</button>
		{#if optimizeResult}
			<button class="px-4 py-2 text-sm transition-colors duration-150 {activeTab === 'cutlayout' ? 'border-b-2 border-[var(--color-primary)] text-[var(--color-primary)] font-medium' : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'}" onclick={() => (activeTab = 'cutlayout')}>Cut Layout</button>
		{/if}
	</div>

	{#if activeTab === 'parts'}
		<div class="overflow-x-auto">
			<table class="w-full text-sm">
				<thead><tr class="border-b border-[var(--color-border)] text-left text-[var(--color-text-secondary)]">
					<th class="py-2 pr-4">Part</th><th class="py-2 pr-4">Qty</th><th class="py-2 pr-4">Dimensions</th><th class="py-2 pr-4">Type</th><th class="py-2 pr-4">Stock</th><th class="py-2">Notes</th>
				</tr></thead>
				<tbody>
					{#each result.parts as part}
						<tr class="border-b border-[var(--color-border)]">
							<td class="py-2 pr-4">{part.name}</td>
							<td class="py-2 pr-4">{part.quantity}</td>
							<td class="py-2 pr-4 font-mono text-xs">{formatDimensions(part, result.display_units)}</td>
							<td class="py-2 pr-4"><span class="px-2 py-0.5 rounded text-xs {part.board_type === 'solid' ? 'bg-emerald-900/20 text-emerald-400' : part.board_type === 'sheet' ? 'bg-amber-900/20 text-amber-400' : 'bg-purple-900/20 text-purple-400'}">{part.board_type}</span></td>
							<td class="py-2 pr-4">{part.stock}</td>
							<td class="py-2 text-[var(--color-text-secondary)] text-xs">{part.notes || '—'}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}

	{#if activeTab === 'shopping'}
		<div class="space-y-4">
			{#each (optimizeResult?.updated_shopping_list ?? result.shopping_list) as item}
				<div class="border border-[var(--color-border)] rounded-lg p-4">
					<div class="flex justify-between items-start mb-2">
						<div>
							<h4 class="font-medium text-[var(--color-text)]">
							{item.material}
							{#if item.url}
								<a href={item.url} target="_blank" rel="noopener noreferrer"
									class="ml-2 text-xs text-[var(--color-primary)] hover:text-[var(--color-primary-hover)] font-normal transition-colors duration-150">
									View on Woodworkers Source ↗
								</a>
							{/if}
						</h4>
							<p class="text-sm text-[var(--color-text-secondary)]">{item.description}</p>
						</div>
						<span class="text-sm font-mono bg-[var(--color-surface-hover)] px-2 py-1 rounded">{item.quantity} {item.unit}</span>
					</div>
					{#if item.cut_pieces.length > 0}
						<div class="mt-2">
							<p class="text-xs text-[var(--color-text-secondary)] uppercase tracking-wide mb-1">Cut pieces</p>
							<div class="flex flex-wrap gap-2">
								{#each item.cut_pieces as piece}
									<span class="text-xs font-mono bg-[var(--color-surface-hover)] border border-[var(--color-border)] px-2 py-1 rounded">{piece}</span>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}

	{#if activeTab === 'cost'}
		<div class="overflow-x-auto">
			<table class="w-full text-sm">
				<thead><tr class="border-b border-[var(--color-border)] text-left text-[var(--color-text-secondary)]">
					<th class="py-2 pr-4">Material</th><th class="py-2 pr-4">Qty</th><th class="py-2 pr-4">Unit Price</th><th class="py-2">Subtotal</th>
				</tr></thead>
				<tbody>
					{#each costItems as item}
						<tr class="border-b border-[var(--color-border)]">
							<td class="py-2 pr-4">
								{#if item.url}
									<a href={item.url} target="_blank" rel="noopener noreferrer"
										class="text-[var(--color-primary)] hover:text-[var(--color-primary-hover)] hover:underline transition-colors duration-150">
										{item.material} ↗
									</a>
								{:else}
									{item.material}
								{/if}
							</td><td class="py-2 pr-4">{item.quantity} {item.unit}</td><td class="py-2 pr-4">{formatPrice(item.unit_price)}</td><td class="py-2">{formatPrice(item.subtotal)}</td>
						</tr>
					{/each}
				</tbody>
				<tfoot><tr class="border-t-2 border-[var(--color-border-strong)] font-medium">
					<td colspan="3" class="py-2 text-right pr-4">Estimated Total:</td><td class="py-2">{formatPrice(costTotal())}</td>
				</tr></tfoot>
			</table>
		</div>
		{#if hasMissingPrices}
			<p class="mt-2 text-sm text-amber-400">Some prices are unavailable. Total is a partial estimate.</p>
		{/if}
	{/if}

	{#if activeTab === 'cutlayout' && optimizeResult && onReoptimize}
		<CutLayout result={optimizeResult} {onReoptimize} {optimizing} />
	{/if}

	<div class="flex gap-3 mt-6">
		{#if onSaveProject && isAuthenticated}
			<button
				onclick={onSaveProject}
				disabled={savingProject || projectSaved}
				class="bg-[var(--color-primary)] text-white px-4 py-2 rounded text-sm hover:bg-[var(--color-primary-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150">
				{#if projectSaved}
					Saved
				{:else if savingProject}
					Saving...
				{:else}
					Save Project
				{/if}
			</button>
		{/if}
		{#if onDownloadPdf}
			<button
				onclick={onDownloadPdf}
				disabled={downloadingPdf}
				class="bg-[var(--color-primary)] text-white px-4 py-2 rounded text-sm hover:bg-[var(--color-primary-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150">
				{#if downloadingPdf}
					Generating PDF...
				{:else if !isAuthenticated}
					Sign in to Download PDF
				{:else}
					Download PDF
				{/if}
			</button>
		{/if}
		<button onclick={exportCsv} class="bg-[var(--color-text)] text-white px-4 py-2 rounded text-sm hover:opacity-90 transition-colors duration-150">Export CSV</button>
		<button onclick={() => window.print()} class="bg-[var(--color-surface-hover)] text-[var(--color-text)] px-4 py-2 rounded text-sm hover:opacity-80 transition-colors duration-150">Print</button>
	</div>
</div>
