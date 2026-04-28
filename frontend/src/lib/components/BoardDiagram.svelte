<script lang="ts">
	import type { BoardLayout } from '$lib/types';

	interface Props {
		layout: BoardLayout;
	}

	let { layout }: Props = $props();

	const scale = 4;
	const svgWidth = layout.length * scale;
	const svgHeight = layout.width * scale;

	function partColor(isspare: boolean): string {
		return isspare ? '#92702a' : '#3d5a7c';
	}

	function partStroke(isspare: boolean): string {
		return isspare ? '#c4a34d' : '#6a8bad';
	}
</script>

<div class="mb-4">
	<div class="flex justify-between items-center mb-1">
		<span class="text-sm font-medium text-gray-700">{layout.material} — {layout.length}" × {layout.width}"</span>
		<span class="text-xs text-green-600 font-medium">Waste: {layout.waste_percent}%</span>
	</div>
	<svg
		viewBox="0 0 {svgWidth} {svgHeight}"
		class="w-full border border-gray-300 rounded bg-gray-100"
		style="max-height: 60px;"
	>
		<rect x="0" y="0" width={svgWidth} height={svgHeight} fill="#e5e7eb" />

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
				fill="white"
				font-size="8"
				font-weight="bold"
			>
				{p.part_name.length > 20 ? p.part_name.slice(0, 17) + '...' : p.part_name}
			</text>
		{/each}
	</svg>
</div>
