'use client';

/**
 * AuthProvider — React context that exposes the current Supabase
 * session to the rest of the app. Mounts a single
 * `onAuthStateChange` listener; consumers read via `useSession()`.
 */
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import type { Session, User } from '@supabase/supabase-js';

import { getSupabase, isAuthConfigured } from '@/lib/supabase';

interface AuthState {
  /** The current session, or null when signed out / auth not configured. */
  session: Session | null;
  user: User | null;
  /** True until the first session read finishes. */
  loading: boolean;
  /** True when Supabase env is wired up; gates the sign-in UI. */
  configured: boolean;
}

const initial: AuthState = {
  session: null,
  user: null,
  loading: true,
  configured: false,
};

const AuthContext = createContext<AuthState>(initial);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(initial);

  useEffect(() => {
    if (!isAuthConfigured()) {
      setState({ ...initial, loading: false, configured: false });
      return;
    }
    const supabase = getSupabase();
    let cancelled = false;

    supabase.auth.getSession().then(({ data }) => {
      if (cancelled) return;
      setState({
        session: data.session,
        user: data.session?.user ?? null,
        loading: false,
        configured: true,
      });
    });

    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => {
      setState({
        session,
        user: session?.user ?? null,
        loading: false,
        configured: true,
      });
    });

    return () => {
      cancelled = true;
      sub.subscription.unsubscribe();
    };
  }, []);

  return <AuthContext.Provider value={state}>{children}</AuthContext.Provider>;
}

export function useSession(): AuthState {
  return useContext(AuthContext);
}
