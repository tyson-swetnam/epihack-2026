/**
 * Personal dashboard route.
 *
 * Available to every user — anonymous or signed-in. Surfaces local weather,
 * active health alerts, a link into the live map + county resources, and the
 * engagement stubs (leaderboard, rewards, weekly-email opt-in). See
 * components/DashboardView.tsx for the data wiring.
 */
import type { Metadata } from 'next';

import { AppTopBar } from '@/components/AppShell';
import { DashboardView } from '@/components/DashboardView';

export const metadata: Metadata = {
  title: 'My dashboard — AZ One Health Sentinel',
};

export default function DashboardPage() {
  return (
    <>
      <AppTopBar backHref="/" title="My dashboard" />
      <DashboardView />
    </>
  );
}
