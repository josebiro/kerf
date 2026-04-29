<script lang="ts">
	import type { OptimizeResponse, BufferConfig, BoardSizeConfig, SheetSizeConfig } from '$lib/types';
	import SheetDiagram from './SheetDiagram.svelte';
	import BoardDiagram from './BoardDiagram.svelte';

	interface Props {
		result: OptimizeResponse;
		onReoptimize: (config: BufferConfig, sizes: Record<string, BoardSizeConfig>, sheetSize: SheetSizeConfig) => void;
		optimizing: boolean;
	}

	let { result, onReoptimize, optimizing }: Props = $props();

	const SHEET_SIZE_OPTIONS: SheetSizeConfig[] = [
		{ width: 48, length: 96, label: "4' × 8' (full)" },
		{ width: 48, length: 48, label: "4' × 4' (half)" },
		{ width: 24, length: 96, label: "2' × 8' (half)" },
		{ width: 24, length: 48, label: "2' × 4' (quarter)" },
	];

	// Initialize from saved config in result
	let sheetMode = $state<'percentage' | 'extra_parts'>(
		(result.buffer_config?.sheet_mode as 'percentage' | 'extra_parts') || 'percentage'
	);
	let sheetValue = $state(result.buffer_config?.sheet_value ?? 15);
	let lumberMode = $state<'percentage' | 'extra_parts'>(
		(result.buffer_config?.lumber_mode as 'percentage' | 'extra_parts') || 'extra_parts'
	);
	let lumberValue = $state(result.buffer_config?.lumber_value ?? 1);

	// Find matching sheet size index from saved config
	function findSheetSizeIndex(): number {
		if (!result.sheet_size) return 0;
		const idx = SHEET_SIZE_OPTIONS.findIndex(
			o => o.width === result.sheet_size.width && o.length === result.sheet_size.length
		);
		return idx >= 0 ? idx : 0;
	}
	let selectedSheetSize = $state(findSheetSizeIndex());

	// Initialize board sizes from saved config, falling back to result boards
	let boardSizes = $state<Record<string, { width: number; length: number }>>({});

	$effect(() => {
		const sizes: Record<string, { width: number; length: number }> = {};
		// Start from saved board_sizes config if available
		if (result.board_sizes) {
			for (const [thickness, size] of Object.entries(result.board_sizes)) {
				sizes[thickness] = { width: size.width, length: size.length };
			}
		}
		// Fill in any missing thicknesses from the actual board layouts
		for (const board of result.boards) {
			if (board.thickness && !sizes[board.thickness]) {
				sizes[board.thickness] = { width: board.width, length: board.length };
			}
		}
		boardSizes = sizes;
	});

	function handleReoptimize() {
		const config: BufferConfig = {
			sheet_mode: sheetMode,
			sheet_value: sheetValue,
			lumber_mode: lumberMode,
			lumber_value: lumberValue,
		};
		const sizes: Record<string, BoardSizeConfig> = {};
		for (const [thickness, size] of Object.entries(boardSizes)) {
			sizes[thickness] = { width: size.width, length: size.length };
		}
		onReoptimize(config, sizes, SHEET_SIZE_OPTIONS[selectedSheetSize]);
	}
</script>

<div class="space-y-6">
	<!-- Buffer Controls -->
	<div class="bg-[var(--color-surface-muted)] border border-[var(--color-border)] rounded-lg p-4">
		<h4 class="text-sm font-medium text-[var(--color-foreground)] mb-3">Mistake Buffer</h4>
		<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
			<div>
				<label class="text-xs text-[var(--color-foreground-muted)] block mb-1">Sheet goods</label>
				<div class="flex gap-2 items-center">
					<select bind:value={sheetMode} class="text-sm border border-[var(--color-border)] rounded px-2 py-1">
						<option value="percentage">Waste %</option>
						<option value="extra_parts">Extra parts</option>
					</select>
					<input type="number" bind:value={sheetValue} min="0" max="100" step="1"
						class="w-16 text-sm border border-[var(--color-border)] rounded px-2 py-1" />
					<span class="text-xs text-[var(--color-foreground-muted)] opacity-60">{sheetMode === 'percentage' ? '%' : 'per part'}</span>
				</div>
			</div>
			<div>
				<label class="text-xs text-[var(--color-foreground-muted)] block mb-1">Solid lumber</label>
				<div class="flex gap-2 items-center">
					<select bind:value={lumberMode} class="text-sm border border-[var(--color-border)] rounded px-2 py-1">
						<option value="extra_parts">Extra parts</option>
						<option value="percentage">Waste %</option>
					</select>
					<input type="number" bind:value={lumberValue} min="0" max="100" step="1"
						class="w-16 text-sm border border-[var(--color-border)] rounded px-2 py-1" />
					<span class="text-xs text-[var(--color-foreground-muted)] opacity-60">{lumberMode === 'percentage' ? '%' : 'per part'}</span>
				</div>
			</div>
		</div>

		<!-- Sheet Size Selector -->
		{#if result.sheets.length > 0}
			<div class="mt-3 pt-3 border-t border-[var(--color-border)]">
				<label class="text-xs text-[var(--color-foreground-muted)] block mb-1">Sheet size</label>
				<select bind:value={selectedSheetSize} class="text-sm border border-[var(--color-border)] rounded px-2 py-1">
					{#each SHEET_SIZE_OPTIONS as option, i}
						<option value={i}>{option.label} ({option.width}" × {option.length}")</option>
					{/each}
				</select>
			</div>
		{/if}

		<!-- Board Size Editors -->
		{#if Object.keys(boardSizes).length > 0}
			<div class="mt-3 pt-3 border-t border-[var(--color-border)]">
				<label class="text-xs text-[var(--color-foreground-muted)] block mb-1">Board dimensions (editable)</label>
				<div class="flex flex-wrap gap-3">
					{#each Object.entries(boardSizes) as [thickness, size]}
						<div class="flex items-center gap-1 text-xs">
							<span class="font-medium text-[var(--color-foreground-muted)]">{thickness}:</span>
							<input type="number" bind:value={size.width} min="1" max="24" step="0.5"
								class="w-12 border border-[var(--color-border)] rounded px-1 py-0.5 text-xs" />"W ×
							<input type="number" bind:value={size.length} min="12" max="192" step="6"
								class="w-14 border border-[var(--color-border)] rounded px-1 py-0.5 text-xs" />"L
						</div>
					{/each}
				</div>
			</div>
		{/if}

		<button
			onclick={handleReoptimize}
			disabled={optimizing}
			class="mt-3 bg-[var(--color-accent)] text-white px-3 py-1.5 rounded text-sm hover:bg-[var(--color-accent-hover)] disabled:opacity-50 transition-colors duration-150"
		>
			{optimizing ? 'Optimizing...' : 'Re-optimize'}
		</button>
	</div>

	<!-- Sheet Diagrams -->
	{#if result.sheets.length > 0}
		<div>
			<h4 class="text-sm font-medium text-[var(--color-foreground)] mb-2">Sheet Goods Layout</h4>
			{#each result.sheets as sheet, i}
				<SheetDiagram layout={sheet} />
			{/each}
		</div>
	{/if}

	<!-- Board Diagrams -->
	{#if result.boards.length > 0}
		<div>
			<h4 class="text-sm font-medium text-[var(--color-foreground)] mb-2">Lumber Board Layout</h4>
			{#each result.boards as board, i}
				<BoardDiagram layout={board} />
			{/each}
		</div>
	{/if}

	<!-- Summary -->
	<div class="bg-[var(--color-surface-muted)] border border-[var(--color-border)] rounded-lg p-4">
		<h4 class="text-sm font-medium text-[var(--color-foreground)] mb-2">Optimization Summary</h4>
		<div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
			<div>
				<div class="text-lg font-bold text-[var(--color-foreground)]">{result.summary.total_sheets}</div>
				<div class="text-xs text-[var(--color-foreground-muted)]">Sheets</div>
			</div>
			<div>
				<div class="text-lg font-bold text-[var(--color-foreground)]">{result.summary.total_boards}</div>
				<div class="text-xs text-[var(--color-foreground-muted)]">Boards</div>
			</div>
			<div>
				<div class="text-lg font-bold text-[var(--color-accent)]">{result.summary.avg_waste_percent}%</div>
				<div class="text-xs text-[var(--color-foreground-muted)]">Avg Waste</div>
			</div>
			<div>
				<div class="text-lg font-bold text-[#A16207]">{result.summary.total_spare_parts}</div>
				<div class="text-xs text-[var(--color-foreground-muted)]">Spare Parts</div>
			</div>
		</div>
	</div>
</div>
