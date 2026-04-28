<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { supabase } from '$lib/supabase';
	import { user, session, authLoading } from '$lib/stores/auth';

	let { children } = $props();

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
</script>

{@render children()}
