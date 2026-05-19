/**
 * Supabase client + session helpers (plan/07-auth.md).
 *
 * The client is lazily constructed so a missing env var doesn't crash
 * unrelated parts of the app — `isAuthConfigured()` returns false and
 * the sign-in UI shows a "configure me" notice instead.
 */
import { createClient, type SupabaseClient } from '@supabase/supabase-js';

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL ?? '';
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? '';

let _client: SupabaseClient | null = null;

export function isAuthConfigured(): boolean {
  return Boolean(SUPABASE_URL && SUPABASE_ANON_KEY);
}

export function getSupabase(): SupabaseClient {
  if (!isAuthConfigured()) {
    throw new Error(
      'Supabase auth is not configured. Set NEXT_PUBLIC_SUPABASE_URL ' +
        'and NEXT_PUBLIC_SUPABASE_ANON_KEY in .env.local.'
    );
  }
  if (_client) return _client;
  _client = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    auth: {
      // Persist the session across reloads, but in the browser memory +
      // a per-origin storage scope (Supabase's default). The cookie is
      // managed by @supabase/ssr in server contexts; static export
      // doesn't have those, so we stay client-only.
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true, // pick up the OAuth callback fragment
    },
  });
  return _client;
}

/**
 * Best-effort access-token getter for outbound API calls. Returns
 * null when there's no session — callers should fall through to the
 * anonymous flow.
 */
export async function getAccessToken(): Promise<string | null> {
  if (!isAuthConfigured()) return null;
  const { data } = await getSupabase().auth.getSession();
  return data.session?.access_token ?? null;
}

/**
 * Provider-button labels, in App-Store-required order: Apple first
 * (Guideline 4.8), then Google, then Facebook.
 */
export const OAUTH_PROVIDERS: { id: 'apple' | 'google' | 'facebook'; label: string }[] = [
  { id: 'apple', label: 'Continue with Apple' },
  { id: 'google', label: 'Continue with Google' },
  { id: 'facebook', label: 'Continue with Facebook' },
];

export async function signInWithProvider(
  provider: 'apple' | 'google' | 'facebook'
): Promise<void> {
  const { error } = await getSupabase().auth.signInWithOAuth({
    provider,
    options: {
      redirectTo:
        typeof window !== 'undefined'
          ? `${window.location.origin}/epihack-2026/app/auth/callback/`
          : undefined,
    },
  });
  if (error) throw error;
}

export async function signInWithMagicLink(email: string): Promise<void> {
  const { error } = await getSupabase().auth.signInWithOtp({
    email,
    options: {
      emailRedirectTo:
        typeof window !== 'undefined'
          ? `${window.location.origin}/epihack-2026/app/auth/callback/`
          : undefined,
    },
  });
  if (error) throw error;
}

export async function signInWithPassword(
  email: string,
  password: string
): Promise<void> {
  const { error } = await getSupabase().auth.signInWithPassword({ email, password });
  if (error) throw error;
}

export async function signUpWithPassword(
  email: string,
  password: string
): Promise<void> {
  const { error } = await getSupabase().auth.signUp({
    email,
    password,
    options: {
      emailRedirectTo:
        typeof window !== 'undefined'
          ? `${window.location.origin}/epihack-2026/app/auth/callback/`
          : undefined,
    },
  });
  if (error) throw error;
}

export async function signOut(): Promise<void> {
  if (!isAuthConfigured()) return;
  await getSupabase().auth.signOut();
}
