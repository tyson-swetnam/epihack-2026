'use client';

/**
 * /account — authenticated profile settings.
 *
 * Skeleton page; the full per-field consent UI lands in 07.2 once
 * `PATCH /v1/auth/me` is wired to a real implementation. For now we
 * surface the user identity, an account-deletion path, and a link
 * back to the per-report profile flow.
 */
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

import { useSession } from '@/components/AuthProvider';
import { signOut } from '@/lib/supabase';

export default function AccountPage() {
  const router = useRouter();
  const { user, loading, configured } = useSession();

  useEffect(() => {
    if (!loading && (!configured || !user)) {
      router.replace('/sign-in');
    }
  }, [loading, configured, user, router]);

  if (loading || !user) return <p className="muted small">Loading…</p>;

  return (
    <article className="account">
      <nav className="crumbs">
        <Link href="/">&laquo; Home</Link>
      </nav>

      <h2>Your account</h2>
      <dl className="account-dl">
        <dt>Email</dt>
        <dd>{user.email ?? '—'}</dd>
        <dt>Provider</dt>
        <dd>
          {(user.app_metadata?.provider as string | undefined) ?? 'email'}
        </dd>
        <dt>User ID</dt>
        <dd>
          <code>{user.id}</code>
        </dd>
      </dl>

      <h3>Reports</h3>
      <p className="muted small">
        Reports you&apos;ve <strong>attached</strong> to this account appear here.
        Anonymous reports do not. (Plan 07 case 3: a signed-in user can still
        file fully anonymous reports.)
      </p>
      <p>
        <Link href="/account/reports">See attached reports →</Link>
      </p>

      <h3>Privacy</h3>
      <p className="muted small">
        Persistent profile + per-field consent toggles (home ZIP,
        contact channels, photo-GPS opt-in, demographic fields) land
        in the next commit — they map 1-to-1 to the{' '}
        <a href="/epihack-2026/api/openapi.yaml">
          <code>AccountProfile</code>
        </a>{' '}
        shape in the OpenAPI spec.
      </p>

      <div className="actions">
        <button
          type="button"
          className="btn secondary"
          onClick={async () => {
            await signOut();
            router.replace('/');
          }}
        >
          Sign out
        </button>
        <Link className="btn ghost" href="/account/delete">
          Delete my account
        </Link>
      </div>
    </article>
  );
}
