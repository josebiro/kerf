<script lang="ts">
	import { uploadFile } from '$lib/api';
	import type { UploadResponse } from '$lib/types';

	interface Props {
		onUpload: (result: UploadResponse) => void;
	}

	let { onUpload }: Props = $props();
	let dragOver = $state(false);
	let uploading = $state(false);
	let error = $state('');

	function validateFile(file: File): string | null {
		if (!file.name.toLowerCase().endsWith('.3mf')) return 'Only .3mf files are accepted';
		if (file.size > 50 * 1024 * 1024) return 'File must be under 50MB';
		return null;
	}

	async function handleFile(file: File) {
		error = '';
		const validationError = validateFile(file);
		if (validationError) { error = validationError; return; }
		uploading = true;
		try {
			const result = await uploadFile(file);
			onUpload(result);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Upload failed';
		} finally {
			uploading = false;
		}
	}

	function handleDrop(event: DragEvent) {
		event.preventDefault();
		dragOver = false;
		const file = event.dataTransfer?.files[0];
		if (file) handleFile(file);
	}

	function handleDragOver(event: DragEvent) {
		event.preventDefault();
		dragOver = true;
	}

	function handleDragLeave() { dragOver = false; }

	function handleInputChange(event: Event) {
		const input = event.target as HTMLInputElement;
		const file = input.files?.[0];
		if (file) handleFile(file);
	}
</script>

<div
	class="border-2 border-dashed rounded-lg p-12 text-center transition-colors duration-150 cursor-pointer
		{dragOver ? 'border-[var(--color-primary)] bg-[var(--color-surface-hover)]' : 'border-[var(--color-border-strong)] hover:border-[var(--color-border-strong)]'}"
	role="button"
	tabindex="0"
	ondrop={handleDrop}
	ondragover={handleDragOver}
	ondragleave={handleDragLeave}
	onclick={() => document.getElementById('file-input')?.click()}
	onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') document.getElementById('file-input')?.click(); }}
>
	{#if uploading}
		<p class="text-[var(--color-text-secondary)]">Uploading...</p>
	{:else}
		<p class="text-lg text-[var(--color-text-secondary)] mb-2">Drop .3mf file here</p>
		<p class="text-sm text-[var(--color-text-secondary)] opacity-60">or click to browse</p>
	{/if}
	<input id="file-input" type="file" accept=".3mf" class="hidden" onchange={handleInputChange} />
</div>

{#if error}
	<p class="mt-4 text-[var(--color-destructive)] text-sm">{error}</p>
{/if}
