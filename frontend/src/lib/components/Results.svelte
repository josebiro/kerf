<script lang="ts">
	import type { AnalyzeResponse, Part, DisplayUnits } from '$lib/types';

	interface Props {
		result: AnalyzeResponse;
		onDownloadPdf?: () => void;
		downloadingPdf?: boolean;
	}
	let { result, onDownloadPdf, downloadingPdf = false }: Props = $props();
	let activeTab = $state<'parts' | 'shopping' | 'cost'>('parts');

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
	<div class="flex gap-2 mb-4">
		<button class="px-4 py-2 text-sm rounded-t {activeTab === 'parts' ? 'bg-white border border-b-0 border-gray-300 font-medium' : 'bg-gray-100 text-gray-500'}" onclick={() => (activeTab = 'parts')}>Parts List</button>
		<button class="px-4 py-2 text-sm rounded-t {activeTab === 'shopping' ? 'bg-white border border-b-0 border-gray-300 font-medium' : 'bg-gray-100 text-gray-500'}" onclick={() => (activeTab = 'shopping')}>Shopping List</button>
		<button class="px-4 py-2 text-sm rounded-t {activeTab === 'cost' ? 'bg-white border border-b-0 border-gray-300 font-medium' : 'bg-gray-100 text-gray-500'}" onclick={() => (activeTab = 'cost')}>Cost Estimate</button>
	</div>

	{#if activeTab === 'parts'}
		<div class="overflow-x-auto">
			<table class="w-full text-sm">
				<thead><tr class="border-b border-gray-300 text-left text-gray-600">
					<th class="py-2 pr-4">Part</th><th class="py-2 pr-4">Qty</th><th class="py-2 pr-4">Dimensions</th><th class="py-2 pr-4">Type</th><th class="py-2 pr-4">Stock</th><th class="py-2">Notes</th>
				</tr></thead>
				<tbody>
					{#each result.parts as part}
						<tr class="border-b border-gray-100">
							<td class="py-2 pr-4">{part.name}</td>
							<td class="py-2 pr-4">{part.quantity}</td>
							<td class="py-2 pr-4 font-mono text-xs">{formatDimensions(part, result.display_units)}</td>
							<td class="py-2 pr-4"><span class="px-2 py-0.5 rounded text-xs {part.board_type === 'solid' ? 'bg-green-100 text-green-700' : part.board_type === 'sheet' ? 'bg-yellow-100 text-yellow-700' : 'bg-purple-100 text-purple-700'}">{part.board_type}</span></td>
							<td class="py-2 pr-4">{part.stock}</td>
							<td class="py-2 text-gray-500 text-xs">{part.notes || '—'}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}

	{#if activeTab === 'shopping'}
		<div class="space-y-4">
			{#each result.shopping_list as item}
				<div class="border border-gray-200 rounded-lg p-4">
					<div class="flex justify-between items-start mb-2">
						<div>
							<h4 class="font-medium text-gray-800">
							{item.material}
							{#if item.url}
								<a href={item.url} target="_blank" rel="noopener noreferrer"
									class="ml-2 text-xs text-blue-600 hover:text-blue-800 font-normal">
									View on Woodworkers Source ↗
								</a>
							{/if}
						</h4>
							<p class="text-sm text-gray-500">{item.description}</p>
						</div>
						<span class="text-sm font-mono bg-gray-100 px-2 py-1 rounded">{item.quantity} {item.unit}</span>
					</div>
					{#if item.cut_pieces.length > 0}
						<div class="mt-2">
							<p class="text-xs text-gray-500 uppercase tracking-wide mb-1">Cut pieces</p>
							<div class="flex flex-wrap gap-2">
								{#each item.cut_pieces as piece}
									<span class="text-xs font-mono bg-gray-50 border border-gray-200 px-2 py-1 rounded">{piece}</span>
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
				<thead><tr class="border-b border-gray-300 text-left text-gray-600">
					<th class="py-2 pr-4">Material</th><th class="py-2 pr-4">Qty</th><th class="py-2 pr-4">Unit Price</th><th class="py-2">Subtotal</th>
				</tr></thead>
				<tbody>
					{#each result.cost_estimate.items as item}
						<tr class="border-b border-gray-100">
							<td class="py-2 pr-4">
								{#if item.url}
									<a href={item.url} target="_blank" rel="noopener noreferrer"
										class="text-blue-600 hover:text-blue-800 hover:underline">
										{item.material} ↗
									</a>
								{:else}
									{item.material}
								{/if}
							</td><td class="py-2 pr-4">{item.quantity} {item.unit}</td><td class="py-2 pr-4">{formatPrice(item.unit_price)}</td><td class="py-2">{formatPrice(item.subtotal)}</td>
						</tr>
					{/each}
				</tbody>
				<tfoot><tr class="border-t-2 border-gray-300 font-medium">
					<td colspan="3" class="py-2 text-right pr-4">Estimated Total:</td><td class="py-2">{formatPrice(result.cost_estimate.total)}</td>
				</tr></tfoot>
			</table>
		</div>
		{#if result.cost_estimate.has_missing_prices}
			<p class="mt-2 text-sm text-amber-600">Some prices are unavailable. Total is a partial estimate.</p>
		{/if}
	{/if}

	<div class="flex gap-3 mt-6">
		{#if onDownloadPdf}
			<button
				onclick={onDownloadPdf}
				disabled={downloadingPdf}
				class="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed">
				{downloadingPdf ? 'Generating PDF...' : 'Download PDF'}
			</button>
		{/if}
		<button onclick={exportCsv} class="bg-gray-800 text-white px-4 py-2 rounded text-sm hover:bg-gray-900">Export CSV</button>
		<button onclick={() => window.print()} class="bg-gray-200 text-gray-700 px-4 py-2 rounded text-sm hover:bg-gray-300">Print</button>
	</div>
</div>
