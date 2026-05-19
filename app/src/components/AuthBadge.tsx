'use client';

/**
 * Small chip in the header: "Sign in" when signed-out (or auth
 * unconfigured), or the user's email + a sign-out button when
 * signed in.
 */
import Link from 'next/link';

import { signOut } from '@/lib/supabase';
import { useSession } from './AuthProvider';

export function AuthBadge() {
  const { user, loading, configured } = useSession();

  if (loading) return null;

  if (!configured || !user) {
    return (
      <Link href="/sign-in" className="auth-badge auth-badge-signin">
        Sign in
      </Link>
    );
  }

  const displayName =
    (user.user_metadata?.full_name as string | undefined) ?? user.email ?? 'Account';

  return (
    <span className="auth-badge auth-badge-signed-in">
      <Link href="/account" className="auth-name">
        {displayName}
      </Link>
      <button
        type="button"
        className="auth-signout"
        onClick={async () => {
          await signOut();
        }}
        aria-label="Sign out"
      >
        ⏻
      </button>
    </span>
  );
}
