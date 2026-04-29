<script lang="ts">
	import type { SheetLayout } from '$lib/types';

	interface Props {
		layout: SheetLayout;
	}

	let { layout }: Props = $props();

	const scale = 4; // pixels per inch
	const svgWidth = $derived(layout.width * scale);
	const svgHeight = $derived(layout.length * scale);

	function partColor(isspare: boolean): string {
		return isspare ? '#92702a' : '#3d7a4a';
	}

	function partStroke(isspare: boolean): string {
		return isspare ? '#c4a34d' : '#5aad6b';
	}
</script>

<div class="mb-4">
	<div class="flex justify-between items-center mb-1">
		<span class="text-sm font-medium text-[var(--color-foreground)]">{layout.material} — {layout.width}" × {layout.length}"</span>
		<span class="text-xs text-[var(--color-accent)] font-medium">Waste: {layout.waste_percent}%</span>
	</div>
	<svg
		viewBox="0 0 {svgWidth} {svgHeight}"
		class="w-full border border-[var(--color-border)] rounded bg-[var(--color-surface-muted)]"
		style="max-height: 200px;"
	>
		<!-- Sheet background -->
		<rect x="0" y="0" width={svgWidth} height={svgHeight} fill="#e5e7eb" />

		<!-- Parts -->
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
				y={(p.y + p.height / 2) * scale - 4}
				text-anchor="middle"
				fill="white"
				font-size="9"
				font-weight="bold"
			>
				{p.part_name.length > 15 ? p.part_name.slice(0, 12) + '...' : p.part_name}
			</text>
			<text
				x={(p.x + p.width / 2) * scale}
				y={(p.y + p.height / 2) * scale + 8}
				text-anchor="middle"
				fill="rgba(255,255,255,0.7)"
				font-size="7"
			>
				{p.width.toFixed(1)}" × {p.height.toFixed(1)}"
			</text>
		{/each}
	</svg>
</div>
