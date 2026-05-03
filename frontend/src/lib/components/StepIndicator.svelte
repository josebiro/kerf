<script lang="ts">
	interface Props {
		currentStep: 1 | 2 | 3;
	}

	let { currentStep }: Props = $props();

	const steps = [
		{ number: 1, label: 'Upload' },
		{ number: 2, label: 'Configure' },
		{ number: 3, label: 'Results' },
	];
</script>

<div class="flex items-center gap-0 py-3 mb-4">
	{#each steps as step, i}
		{#if i > 0}
			<div class="w-8 h-px {currentStep > step.number - 1 ? 'bg-[var(--color-primary)]' : 'bg-[var(--color-border)]'} mx-2"></div>
		{/if}
		<div class="flex items-center gap-1.5">
			<div class="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-semibold
				{currentStep >= step.number
					? 'bg-[var(--color-primary)] text-white'
					: 'bg-[var(--color-border-strong)] text-[var(--color-text-muted)]'}"
			>
				{step.number}
			</div>
			<span class="text-xs {currentStep >= step.number ? 'text-[var(--color-text)] font-medium' : 'text-[var(--color-text-muted)]'}">{step.label}</span>
		</div>
	{/each}
</div>
