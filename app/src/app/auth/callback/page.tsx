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
import { Loader2 } from 'lucide-react';

import { AppTopBar } from '@/components/AppShell';
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
    <>
      <AppTopBar title="Finishing sign-in" />
      <section className="flex flex-col items-center gap-3 px-4 py-12 text-center">
        {!error ? (
          <>
            <Loader2 className="size-7 animate-spin text-public-teal" aria-hidden="true" />
            <p className="text-sm text-slate-600">One moment…</p>
          </>
        ) : (
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
