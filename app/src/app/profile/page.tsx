/**
 * Optional post-submit profile interstitial.
 *
 * Every toggle defaults to OFF — a load-bearing rule from plan/06. The user
 * reaches this page after a successful submit; the claim_token stays in
 * localStorage so ProfileForm can PATCH /v1/reports/{id}/profile.
 */
import type { Metadata } from 'next';

import { AppTopBar } from '@/components/AppShell';
import { ProfileForm } from '@/components/ProfileForm';

export const metadata: Metadata = {
  title: 'Optional profile — AZ One Health Sentinel',
};

export default function ProfilePage() {
  return (
    <>
      <AppTopBar backHref="/" title="Optional profile" />
      <section className="flex flex-col gap-4 px-4 pb-8 pt-5">
        <h2 className="text-base font-extrabold text-ink">
          Make this easier next time?
        </h2>
        <p className="text-sm leading-5 text-slate-600">
          Everything below is optional and off by default. You can change or
          delete any of it later.
        </p>
        <ProfileForm />
      </section>
    </>
  );
}
