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
import Link from 'next/link';

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

  return (
    <article className="sign-in">
      <nav className="crumbs">
        <Link href="/">&laquo; Back</Link>
      </nav>
      <h2>Sign in</h2>
      <p className="muted small">
        Optional. You don&apos;t need an account to file a report. An account lets
        you keep your profile across devices and see your report history. See{' '}
        <a href="/epihack-2026/plan/07-auth.html">plan&nbsp;07</a> for the
        privacy details.
      </p>

      {!configured && (
        <div className="error-banner" role="status">
          Auth is not configured for this build. Set{' '}
          <code>NEXT_PUBLIC_SUPABASE_URL</code> and{' '}
          <code>NEXT_PUBLIC_SUPABASE_ANON_KEY</code> in <code>.env.local</code>{' '}
          to enable sign-in. Anonymous reporting still works on the home page.
        </div>
      )}

      <div className="oauth-buttons">
        {OAUTH_PROVIDERS.map((p) => (
          <button
            key={p.id}
            type="button"
            className={`btn oauth oauth-${p.id}`}
            onClick={() => handleOAuth(p.id)}
            disabled={!configured || busy}
          >
            {p.label}
          </button>
        ))}
      </div>

      <div className="divider"><span>or</span></div>

      <form className="email-form" onSubmit={handleSubmit}>
        <label className="field">
          Email
          <input
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={!configured || busy}
          />
        </label>
        {mode !== 'magic' && (
          <label className="field">
            Password
            <input
              type="password"
              autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
              required
              minLength={12}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={!configured || busy}
            />
          </label>
        )}

        <button
          type="submit"
          className="btn"
          disabled={!configured || busy || !email || (mode !== 'magic' && password.length < 12)}
        >
          {mode === 'signin' && 'Sign in'}
          {mode === 'signup' && 'Create account'}
          {mode === 'magic' && 'Email me a sign-in link'}
        </button>
      </form>

      <div className="mode-switch">
        {mode !== 'signin' && (
          <button type="button" className="link" onClick={() => setMode('signin')}>
            Have an account? Sign in
          </button>
        )}
        {mode !== 'signup' && (
          <button type="button" className="link" onClick={() => setMode('signup')}>
            New here? Create an account
          </button>
        )}
        {mode !== 'magic' && (
          <button type="button" className="link" onClick={() => setMode('magic')}>
            Email me a magic link instead
          </button>
        )}
      </div>

      {info && <p className="muted small" role="status">{info}</p>}
      {error && <p className="error-banner" role="alert">{error}</p>}
    </article>
  );
}
