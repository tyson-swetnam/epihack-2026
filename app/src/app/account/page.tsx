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

import { AppTopBar } from '@/components/AppShell';
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

  if (loading || !user) {
    return (
      <>
        <AppTopBar backHref="/" title="Your account" />
        <p className="px-4 pt-6 text-sm text-slate-500">Loading…</p>
      </>
    );
  }

  return (
    <>
      <AppTopBar backHref="/" title="Your account" />
      <section className="flex flex-col gap-4 px-4 pb-8 pt-5">
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 rounded-md bg-soft-mint p-3 text-sm">
          <dt className="font-semibold text-ink">Email</dt>
          <dd className="text-slate-600">{user.email ?? '—'}</dd>
          <dt className="font-semibold text-ink">Provider</dt>
          <dd className="text-slate-600">
            {(user.app_metadata?.provider as string | undefined) ?? 'email'}
          </dd>
          <dt className="font-semibold text-ink">User ID</dt>
          <dd className="break-all text-slate-600">
            <code className="text-xs">{user.id}</code>
          </dd>
        </dl>

        <div>
          <h3 className="text-sm font-extrabold text-ink">Reports</h3>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            Reports you&apos;ve <strong>attached</strong> to this account appear
            here. Anonymous reports do not — a signed-in user can still file
            fully anonymous reports.
          </p>
          <Link
            href="/account/reports"
            className="focus-ring mt-2 inline-block text-xs font-semibold text-public-teal"
          >
            See attached reports →
          </Link>
        </div>

        <div className="mt-2 flex gap-2">
          <button
            type="button"
            className="app-button-secondary"
            onClick={async () => {
              await signOut();
              router.replace('/');
            }}
          >
            Sign out
          </button>
          <Link className="app-button-secondary" href="/account/delete">
            Delete account
          </Link>
        </div>
      </section>
    </>
  );
}
