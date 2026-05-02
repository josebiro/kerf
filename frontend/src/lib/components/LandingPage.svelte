<script lang="ts">
	import { goto } from '$app/navigation';
</script>

<div class="min-h-screen bg-[var(--color-bg)]">
	<header class="bg-[var(--color-bg-deep)] border-b border-[var(--color-border-strong)] px-6 py-4">
		<div class="max-w-5xl mx-auto flex items-center justify-between">
			<span class="text-[var(--color-text)] font-semibold text-[15px] tracking-tight">kerf</span>
			<a href="/login" class="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition-colors duration-150">Sign In</a>
		</div>
	</header>

	<div class="max-w-5xl mx-auto px-6">
		<div class="py-24 text-center">
			<h1 class="text-4xl font-bold text-[var(--color-text)] tracking-tight mb-4">
				From CAD model to cut list in seconds
			</h1>
			<p class="text-lg text-[var(--color-text-secondary)] max-w-2xl mx-auto mb-8">
				Upload a 3MF file from Fusion 360, Onshape, or any CAD tool. Kerf analyzes your parts, optimizes cuts, and generates shopping lists with real lumber prices.
			</p>
			<div class="flex gap-3 justify-center">
				<button
					onclick={() => goto('/login?signup=true')}
					class="bg-[var(--color-primary)] text-white px-6 py-2.5 rounded-md text-sm font-semibold hover:bg-[var(--color-primary-hover)] transition-colors duration-150"
				>
					Get Started
				</button>
				<button
					onclick={() => goto('/login')}
					class="bg-[var(--color-surface)] text-[var(--color-text)] border border-[var(--color-border)] px-6 py-2.5 rounded-md text-sm font-medium hover:bg-[var(--color-surface-hover)] transition-colors duration-150"
				>
					Sign In
				</button>
			</div>
		</div>

		<div class="grid grid-cols-1 md:grid-cols-3 gap-6 pb-24">
			<div class="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-6">
				<div class="w-10 h-10 bg-[var(--color-bg-deep)] rounded-lg flex items-center justify-center mb-4">
					<span class="text-[var(--color-primary)] text-lg font-bold">$</span>
				</div>
				<h3 class="text-sm font-semibold text-[var(--color-text)] mb-2">Multi-Supplier Pricing</h3>
				<p class="text-sm text-[var(--color-text-secondary)]">Compare lumber prices across suppliers. Real prices from Woodworkers Source, Knotty Lumber, and Makerstock.</p>
			</div>
			<div class="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-6">
				<div class="w-10 h-10 bg-[var(--color-bg-deep)] rounded-lg flex items-center justify-center mb-4">
					<span class="text-[var(--color-primary)] text-lg font-bold">&#9638;</span>
				</div>
				<h3 class="text-sm font-semibold text-[var(--color-text)] mb-2">Cut Optimization</h3>
				<p class="text-sm text-[var(--color-text-secondary)]">Minimize waste with optimized cutting layouts for both sheet goods and solid lumber boards.</p>
			</div>
			<div class="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-6">
				<div class="w-10 h-10 bg-[var(--color-bg-deep)] rounded-lg flex items-center justify-center mb-4">
					<span class="text-[var(--color-primary)] text-lg font-bold">&#8595;</span>
				</div>
				<h3 class="text-sm font-semibold text-[var(--color-text)] mb-2">PDF Reports</h3>
				<p class="text-sm text-[var(--color-text-secondary)]">Download detailed cut list reports with 3D thumbnails, parts lists, shopping lists, and cost breakdowns.</p>
			</div>
		</div>
	</div>

	<footer class="border-t border-[var(--color-border-strong)] px-6 py-6">
		<div class="max-w-5xl mx-auto text-center text-xs text-[var(--color-text-dim)]">
			&copy; 2026 Kerf
		</div>
	</footer>
</div>
