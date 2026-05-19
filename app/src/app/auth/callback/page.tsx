'use client';

/**
 * /auth/callback — OAuth-provider redirect target.
 *
 * The Supabase JS SDK parses the URL hash automatically (we set
 * `detectSessionInUrl: true` in lib/supabase.ts), so this page just
 * waits for `onAuthStateChange` to fire and then bounces home.
 */
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

import { getSupabase, isAuthConfigured } from '@/lib/supabase';

export default function AuthCallbackPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthConfigured()) {
      setError('Auth is not configured for this build.');
      return;
    }
    const supabase = getSupabase();
    let cancelled = false;

    supabase.auth.getSession().then(({ data, error }) => {
      if (cancelled) return;
      if (error) {
        setError(error.message);
        return;
      }
      if (data.session) router.replace('/');
    });

    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session) router.replace('/');
    });

    return () => {
      cancelled = true;
      sub.subscription.unsubscribe();
    };
  }, [router]);

  return (
    <article>
      <h2>Finishing sign-in…</h2>
      {error && <p className="error-banner" role="alert">{error}</p>}
      {!error && <p className="muted small">One moment.</p>}
    </article>
  );
}
