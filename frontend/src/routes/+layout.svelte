<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { supabase } from '$lib/supabase';
	import { user, session, authLoading, isAuthenticated } from '$lib/stores/auth';
	import ProfileMenu from '$lib/components/ProfileMenu.svelte';

	let { children } = $props();

	const publicRoutes = ['/login', '/auth/callback'];
	const isPublicRoute = $derived(publicRoutes.some(r => page.url.pathname.startsWith(r)));

	onMount(() => {
		supabase.auth.getSession().then(({ data }) => {
			session.set(data.session);
			user.set(data.session?.user ?? null);
			authLoading.set(false);
		});

		const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, newSession) => {
			session.set(newSession);
			user.set(newSession?.user ?? null);
		});

		return () => subscription.unsubscribe();
	});

	$effect(() => {
		if (!$authLoading && !$isAuthenticated && !isPublicRoute && page.url.pathname !== '/') {
			goto(`/login?redirect=${encodeURIComponent(page.url.pathname)}`);
		}
	});
</script>

{#if $authLoading}
	<div class="min-h-screen bg-[var(--color-bg)] flex items-center justify-center">
		<div class="text-[var(--color-text-muted)]">Loading...</div>
	</div>
{:else if $isAuthenticated}
	<div class="min-h-screen bg-[var(--color-bg)]">
		<header class="bg-[var(--color-bg-deep)] border-b border-[var(--color-border-strong)] px-6 py-2.5">
			<div class="max-w-6xl mx-auto flex items-center justify-between">
				<div class="flex items-center gap-5">
					<a href="/projects" class="flex items-center gap-2">
						<span class="text-[var(--color-text)] font-semibold text-[15px] tracking-tight">kerf</span>
					</a>
					<nav class="flex gap-0.5">
						<a
							href="/projects"
							class="px-3 py-1.5 text-xs rounded transition-colors duration-150
								{page.url.pathname === '/projects'
									? 'bg-[var(--color-border-strong)] text-[var(--color-text)]'
									: 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'}"
						>Projects</a>
						<a
							href="/"
							class="px-3 py-1.5 text-xs rounded transition-colors duration-150
								{page.url.pathname === '/'
									? 'bg-[var(--color-border-strong)] text-[var(--color-text)]'
									: 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'}"
						>New Project</a>
					</nav>
				</div>
				<ProfileMenu />
			</div>
		</header>

		<main class="max-w-6xl mx-auto px-6 py-8">
			{@render children()}
		</main>
	</div>
{:else}
	{@render children()}
{/if}
