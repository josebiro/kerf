<script lang="ts">
	import { goto } from '$app/navigation';
	import { supabase } from '$lib/supabase';
	import { user } from '$lib/stores/auth';

	let open = $state(false);

	const initials = $derived(() => {
		const u = $user;
		if (!u?.email) return '?';
		return u.email.substring(0, 2).toUpperCase();
	});

	function handleClickOutside(event: MouseEvent) {
		const target = event.target as HTMLElement;
		if (!target.closest('.profile-menu')) {
			open = false;
		}
	}

	async function handleSignOut() {
		await supabase.auth.signOut();
		open = false;
		goto('/');
	}
</script>

<svelte:window onclick={handleClickOutside} />

<div class="profile-menu relative">
	<button
		onclick={() => (open = !open)}
		class="w-8 h-8 bg-[var(--color-primary)] rounded-full flex items-center justify-center cursor-pointer hover:bg-[var(--color-primary-hover)] transition-colors duration-150"
	>
		<span class="text-white text-xs font-semibold">{initials()}</span>
	</button>

	{#if open}
		<div class="absolute top-10 right-0 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg w-44 py-1 shadow-lg shadow-black/40 z-50">
			<button
				onclick={() => { open = false; goto('/preferences'); }}
				class="w-full text-left px-3 py-2 text-sm text-[var(--color-text)] hover:bg-[var(--color-surface-hover)] transition-colors duration-150"
			>
				Preferences
			</button>
			<div class="border-t border-[var(--color-border)] my-1"></div>
			<button
				onclick={handleSignOut}
				class="w-full text-left px-3 py-2 text-sm text-[var(--color-destructive)] hover:bg-[var(--color-surface-hover)] transition-colors duration-150"
			>
				Sign Out
			</button>
		</div>
	{/if}
</div>
