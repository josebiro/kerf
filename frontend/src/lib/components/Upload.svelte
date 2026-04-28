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
	class="border-2 border-dashed rounded-lg p-12 text-center transition-colors cursor-pointer
		{dragOver ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}"
	role="button"
	tabindex="0"
	ondrop={handleDrop}
	ondragover={handleDragOver}
	ondragleave={handleDragLeave}
	onclick={() => document.getElementById('file-input')?.click()}
	onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') document.getElementById('file-input')?.click(); }}
>
	{#if uploading}
		<p class="text-gray-500">Uploading...</p>
	{:else}
		<p class="text-lg text-gray-600 mb-2">Drop .3mf file here</p>
		<p class="text-sm text-gray-400">or click to browse</p>
	{/if}
	<input id="file-input" type="file" accept=".3mf" class="hidden" onchange={handleInputChange} />
</div>

{#if error}
	<p class="mt-4 text-red-600 text-sm">{error}</p>
{/if}
