'use client';

/**
 * /sign-in — sign-in / sign-up page.
 *
 * Provider order is fixed: Apple first, then Google, then Facebook
 * (App Store Guideline 4.8). Email + password and magic-link sit
 * underneath the social buttons. Anonymous report submission stays
 * fully usable without ever visiting this page — see plan/07.
 */
import { useState } from 'react';

import { AppTopBar } from '@/components/AppShell';
import {
  OAUTH_PROVIDERS,
  isAuthConfigured,
  signInWithMagicLink,
  signInWithPassword,
  signInWithProvider,
  signUpWithPassword,
} from '@/lib/supabase';

type Mode = 'signin' | 'signup' | 'magic';

export default function SignInPage() {
  const [mode, setMode] = useState<Mode>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const configured = isAuthConfigured();

  const handleOAuth = async (id: 'apple' | 'google' | 'facebook') => {
    setError(null);
    setBusy(true);
    try {
      await signInWithProvider(id);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setInfo(null);
    setBusy(true);
    try {
      if (mode === 'signin') {
        await signInWithPassword(email, password);
        setInfo("You're signed in.");
      } else if (mode === 'signup') {
        await signUpWithPassword(email, password);
        setInfo('Account created — check your email to confirm.');
      } else {
        await signInWithMagicLink(email);
        setInfo('Check your email for the sign-in link.');
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const fieldClass =
    'focus-ring w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-normal';

  return (
    <>
      <AppTopBar backHref="/" title="Sign in" />
      <section className="flex flex-col gap-4 px-4 pb-8 pt-5">
        <p className="text-sm leading-5 text-slate-600">
          Optional. You don&apos;t need an account to file a report — it just
          keeps your profile across devices and shows your report history.
        </p>

        {!configured && (
          <div
            className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800"
            role="status"
          >
            Auth isn&apos;t configured for this build. Set{' '}
            <code>NEXT_PUBLIC_SUPABASE_URL</code> and{' '}
            <code>NEXT_PUBLIC_SUPABASE_ANON_KEY</code>. Anonymous reporting still
            works.
          </div>
        )}

        <div className="flex flex-col gap-2">
          {OAUTH_PROVIDERS.map((p) => (
            <button
              key={p.id}
              type="button"
              className="app-button-secondary"
              onClick={() => handleOAuth(p.id)}
              disabled={!configured || busy}
            >
              {p.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3 text-xs text-slate-400">
          <span className="h-px flex-1 bg-slate-200" />
          or
          <span className="h-px flex-1 bg-slate-200" />
        </div>

        <form className="flex flex-col gap-3" onSubmit={handleSubmit}>
          <label className="flex flex-col gap-1 text-sm font-semibold text-ink">
            Email
            <input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={!configured || busy}
              className={fieldClass}
            />
          </label>
          {mode !== 'magic' && (
            <label className="flex flex-col gap-1 text-sm font-semibold text-ink">
              Password
              <input
                type="password"
                autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                required
                minLength={12}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={!configured || busy}
                className={fieldClass}
              />
            </label>
          )}

          <button
            type="submit"
            className="app-button"
            disabled={!configured || busy || !email || (mode !== 'magic' && password.length < 12)}
          >
            {mode === 'signin' && 'Sign in'}
            {mode === 'signup' && 'Create account'}
            {mode === 'magic' && 'Email me a sign-in link'}
          </button>
        </form>

        <div className="flex flex-col gap-1.5 text-center text-xs font-semibold text-public-teal">
          {mode !== 'signin' && (
            <button type="button" className="focus-ring" onClick={() => setMode('signin')}>
              Have an account? Sign in
            </button>
          )}
          {mode !== 'signup' && (
            <button type="button" className="focus-ring" onClick={() => setMode('signup')}>
              New here? Create an account
            </button>
          )}
          {mode !== 'magic' && (
            <button type="button" className="focus-ring" onClick={() => setMode('magic')}>
              Email me a magic link instead
            </button>
          )}
        </div>

        {info && (
          <p
            className="rounded-md border border-teal-200 bg-soft-mint px-3 py-2 text-sm text-public-teal"
            role="status"
          >
            {info}
          </p>
        )}
        {error && (
          <p
            className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700"
            role="alert"
          >
            {error}
          </p>
        )}
      </section>
    </>
  );
}
