<script lang="ts">
	import { supabase } from '$lib/supabase';
	import { isAuthenticated } from '$lib/stores/auth';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';

	let email = $state('');
	let password = $state('');
	let error = $state('');
	let loading = $state(false);
	let isSignUp = $state(false);
	let checkEmail = $state(false);

	const redirectTo = $derived(page.url.searchParams.get('redirect') || '/');

	$effect(() => {
		if ($isAuthenticated) {
			goto(redirectTo);
		}
	});

	async function handleEmailAuth() {
		error = '';
		loading = true;
		try {
			if (isSignUp) {
				const { error: signUpError } = await supabase.auth.signUp({
					email,
					password,
					options: {
						emailRedirectTo: `${window.location.origin}/auth/callback?redirect=${encodeURIComponent(redirectTo)}`,
					},
				});
				if (signUpError) throw signUpError;
				checkEmail = true;
			} else {
				const { error: signInError } = await supabase.auth.signInWithPassword({
					email,
					password,
				});
				if (signInError) throw signInError;
				goto(redirectTo);
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Authentication failed';
		} finally {
			loading = false;
		}
	}

	async function handleGoogleAuth() {
		error = '';
		const { error: oauthError } = await supabase.auth.signInWithOAuth({
			provider: 'google',
			options: {
				redirectTo: `${window.location.origin}/auth/callback?redirect=${encodeURIComponent(redirectTo)}`,
			},
		});
		if (oauthError) {
			error = oauthError.message;
		}
	}
</script>

<div class="min-h-screen bg-gray-50 flex items-center justify-center px-4">
	<div class="max-w-sm w-full">
		<div class="text-center mb-8">
			<h1 class="text-2xl font-semibold text-gray-800">Kerf</h1>
			<p class="text-sm text-gray-500 mt-1">Sign in to download PDF reports and save projects</p>
		</div>

		{#if checkEmail}
			<div class="bg-white rounded-lg border border-gray-200 p-6 text-center">
				<h2 class="text-lg font-medium text-gray-800 mb-2">Check your email</h2>
				<p class="text-sm text-gray-500">We sent a verification link to <strong>{email}</strong>. Click the link to finish signing up.</p>
			</div>
		{:else}
			<div class="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
				<button
					onclick={handleGoogleAuth}
					class="w-full flex items-center justify-center gap-2 border border-gray-300 rounded-md px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
				>
					<svg class="w-4 h-4" viewBox="0 0 24 24">
						<path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
						<path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
						<path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
						<path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
					</svg>
					Continue with Google
				</button>

				<div class="relative">
					<div class="absolute inset-0 flex items-center"><div class="w-full border-t border-gray-200"></div></div>
					<div class="relative flex justify-center text-xs"><span class="bg-white px-2 text-gray-400">or</span></div>
				</div>

				<form onsubmit={(e) => { e.preventDefault(); handleEmailAuth(); }} class="space-y-3">
					<div>
						<input
							type="email"
							bind:value={email}
							placeholder="Email"
							required
							class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
						/>
					</div>
					<div>
						<input
							type="password"
							bind:value={password}
							placeholder="Password"
							required
							minlength="6"
							class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
						/>
					</div>
					<button
						type="submit"
						disabled={loading}
						class="w-full bg-blue-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
					>
						{loading ? 'Please wait...' : isSignUp ? 'Sign Up' : 'Sign In'}
					</button>
				</form>

				{#if error}
					<p class="text-sm text-red-600">{error}</p>
				{/if}

				<p class="text-center text-xs text-gray-500">
					{#if isSignUp}
						Already have an account? <button class="text-blue-600 hover:underline" onclick={() => (isSignUp = false)}>Sign In</button>
					{:else}
						Don't have an account? <button class="text-blue-600 hover:underline" onclick={() => (isSignUp = true)}>Sign Up</button>
					{/if}
				</p>
			</div>
		{/if}

		<p class="text-center mt-4">
			<a href="/" class="text-sm text-gray-400 hover:text-gray-600">Back to app</a>
		</p>
	</div>
</div>
