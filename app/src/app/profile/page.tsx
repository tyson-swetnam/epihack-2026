/**
 * Optional post-submit profile interstitial.
 *
 * Every toggle here defaults to OFF — that's a load-bearing rule from
 * plan/06-mobile-app.md. The user reaches this page only after a
 * successful report submit; the claim_token stays in localStorage so
 * we can attach the profile via PATCH /v1/reports/{id}/profile.
 *
 * This commit ships the route + the toggle list; the wire-up to the
 * `attachProfile` API call lands in the next commit alongside the
 * "Heard you" reply-back flow.
 */
import type { Metadata } from 'next';
import Link from 'next/link';

import { ProfileForm } from '@/components/ProfileForm';

export const metadata: Metadata = {
  title: 'Optional profile — AZ One Health Sentinel',
};

export default function ProfilePage() {
  return (
    <article className="profile-page">
      <nav className="crumbs">
        <Link href="/">&laquo; Home</Link>
      </nav>
      <h2>Want to make this easier next time?</h2>
      <p>
        Everything below is optional and off by default. You can change or
        delete any of it later. The toggles map 1-to-1 to the{' '}
        <a href="/epihack-2026/api/openapi.yaml">
          <code>ProfilePatch</code>
        </a>{' '}
        shape in the OpenAPI spec.
      </p>
      <ProfileForm />
    </article>
  );
}
