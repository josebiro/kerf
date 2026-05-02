<script lang="ts">
	import type { BoardLayout } from '$lib/types';

	interface Props {
		layout: BoardLayout;
	}

	let { layout }: Props = $props();

	const scale = 4;
	const svgWidth = $derived(layout.length * scale);
	const svgHeight = $derived(layout.width * scale);

	function partColor(isspare: boolean): string {
		return isspare ? 'rgba(129, 140, 248, 0.2)' : 'rgba(99, 102, 241, 0.3)';
	}

	function partStroke(isspare: boolean): string {
		return isspare ? '#818cf8' : '#6366f1';
	}
</script>

<div class="mb-4">
	<div class="flex justify-between items-center mb-1">
		<span class="text-sm font-medium text-[var(--color-text)]">{layout.material} — {layout.length}" × {layout.width}"</span>
		<span class="text-xs text-[var(--color-primary)] font-medium">Waste: {layout.waste_percent}%</span>
	</div>
	<svg
		viewBox="0 0 {svgWidth} {svgHeight}"
		class="w-full border border-[var(--color-border)] rounded"
		style="max-height: 60px; background: #0f1219;"
	>
		<rect x="0" y="0" width={svgWidth} height={svgHeight} fill="#1e293b" stroke="#2a3040" stroke-width="1" />

		{#each layout.placements as p}
			<rect
				x={p.x * scale}
				y={p.y * scale}
				width={p.width * scale}
				height={p.height * scale}
				fill={partColor(p.is_spare)}
				stroke={partStroke(p.is_spare)}
				stroke-width="1"
				stroke-dasharray={p.is_spare ? '4,2' : 'none'}
				rx="2"
			/>
			<text
				x={(p.x + p.width / 2) * scale}
				y={(p.y + p.height / 2) * scale + 3}
				text-anchor="middle"
				fill="#e2e8f0"
				font-size="8"
				font-weight="bold"
			>
				{p.part_name.length > 20 ? p.part_name.slice(0, 17) + '...' : p.part_name}
			</text>
		{/each}
	</svg>
</div>
