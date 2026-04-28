import { writable, derived } from 'svelte/store';
import type { User, Session } from '@supabase/supabase-js';

export const user = writable<User | null>(null);
export const session = writable<Session | null>(null);
export const authLoading = writable(true);
export const isAuthenticated = derived(user, ($user) => $user !== null);
