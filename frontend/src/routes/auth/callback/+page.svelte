<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { supabase } from '$lib/supabase';
	import { safeRedirect } from '$lib/safeRedirect';
	let error = $state('');

	onMount(async () => {
		const { error: authError } = await supabase.auth.getSession();
		if (authError) {
			error = authError.message;
			return;
		}

		goto(safeRedirect(page.url.searchParams.get('redirect')));
	});
</script>

<div class="min-h-screen bg-gray-50 flex items-center justify-center">
	{#if error}
		<div class="text-center">
			<p class="text-red-600 mb-4">{error}</p>
			<a href="/login" class="text-blue-600 hover:underline text-sm">Try again</a>
		</div>
	{:else}
		<p class="text-gray-500">Completing sign in...</p>
	{/if}
</div>
