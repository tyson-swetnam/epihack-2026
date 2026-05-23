'use client';

/**
 * Personal dashboard (stub).
 *
 * Every user — anonymous or signed-in — gets this view. It pulls the same
 * public-health context the report flow surfaces (`GET /v1/context`) and
 * frames it as a personal "what's happening near me" page:
 *
 *   - Local weather strip (derived from the heat signal; mock until a
 *     dedicated weather feed is wired)
 *   - Active health alerts in your area (live ContextSignal list)
 *   - A link into the live interactive map + county resources
 *   - Community leaderboard + rewards (engagement stubs, mock data)
 *   - Weekly-email opt-in
 *
 * Mock-mode (the GitHub Pages build) renders bundled fixtures, so this page
 * works with no backend.
 */
import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Bell,
  CloudSun,
  Gift,
  Map as MapIcon,
  Mail,
  Trophy,
} from 'lucide-react';

import { getContext } from '@/lib/api-client';
import type { ContextEnvelope, ContextSignal } from '@/lib/api-shapes';

const TIER_STYLE: Record<string, string> = {
  info: 'border-slate-200 bg-slate-50 text-slate-700',
  advisory: 'border-amber-200 bg-amber-50 text-amber-800',
  watch: 'border-orange-200 bg-orange-50 text-orange-800',
  warning: 'border-rose-200 bg-rose-50 text-rose-800',
};

const CLASS_LABEL: Record<ContextSignal['class'], string> = {
  vbd: 'Mosquito / tick',
  heat: 'Heat',
  wildlife: 'Wildlife',
  environment: 'Environment',
};

// Engagement stubs — mock data only. Wire to a real endpoint later.
const LEADERBOARD = [
  { zone: 'Your neighborhood (85001)', reports: 18, you: true },
  { zone: 'Central Phoenix', reports: 31 },
  { zone: 'Tempe', reports: 27 },
  { zone: 'Mesa', reports: 12 },
];
const REWARDS = [
  { partner: 'Local pharmacy', perk: '$5 off sunscreen & repellent', code: 'SHADE5' },
  { partner: 'County cooling center', perk: 'Free reusable water bottle', code: 'HYDRATE' },
];

export function DashboardView() {
  const [zip, setZip] = useState('85001');
  const [ctx, setCtx] = useState<ContextEnvelope | null>(null);
  const [loading, setLoading] = useState(true);
  const [weeklyEmail, setWeeklyEmail] = useState(false);

  useEffect(() => {
    const saved = window.localStorage.getItem('homeZip');
    const z = saved && /^\d{5}$/.test(saved) ? saved : '85001';
    setZip(z);
    setWeeklyEmail(window.localStorage.getItem('weeklyEmailOptIn') === '1');
    getContext({ zip: z })
      .then(setCtx)
      .catch(() => setCtx(null))
      .finally(() => setLoading(false));
  }, []);

  const heat = ctx?.signals.find((s) => s.class === 'heat');

  return (
    <section className="flex flex-col gap-4 px-4 pb-10 pt-4">
      {/* Weather strip */}
      <div className="flex items-center gap-3 rounded-lg border border-teal-900/10 bg-gradient-to-br from-teal-50 to-cyan-50 px-4 py-3">
        <CloudSun className="size-8 shrink-0 text-public-teal" aria-hidden="true" />
        <div className="flex-1">
          <p className="text-xs font-bold uppercase tracking-wide text-public-teal">
            Local weather · {zip}
          </p>
          <p className="text-sm font-semibold text-ink">
            {heat?.severity_tier === 'warning'
              ? 'Extreme heat — limit midday exposure'
              : 'Hot & dry · stay hydrated'}
          </p>
          <p className="text-[11px] text-slate-500">
            Demo weather strip · live NWS feed pending
          </p>
        </div>
      </div>

      {/* Active health alerts */}
      <div className="flex flex-col gap-2">
        <h2 className="flex items-center gap-2 text-sm font-extrabold text-ink">
          <Bell className="size-4 text-public-teal" aria-hidden="true" />
          Active alerts near you
        </h2>
        {loading && <p className="text-sm text-slate-500">Loading…</p>}
        {!loading && (!ctx || ctx.signals.length === 0) && (
          <p className="text-sm text-slate-500">No active alerts in your area.</p>
        )}
        {ctx?.signals.map((s, i) => (
          <article
            key={i}
            className={`rounded-md border px-3 py-2 text-sm ${
              TIER_STYLE[s.severity_tier ?? 'info']
            }`}
          >
            <p className="text-[10px] font-bold uppercase tracking-wide opacity-70">
              {CLASS_LABEL[s.class]}
              {s.severity_tier ? ` · ${s.severity_tier}` : ''}
            </p>
            <p className="font-medium leading-5">{s.headline}</p>
            <a
              href={s.source.url}
              target="_blank"
              rel="noreferrer"
              className="text-[11px] underline opacity-80"
            >
              {s.source.name}
            </a>
          </article>
        ))}
      </div>

      {/* Map + resources links */}
      <div className="grid grid-cols-2 gap-3">
        <Link
          href="/epihack-2026/map/"
          className="focus-ring flex flex-col gap-1 rounded-lg border border-slate-200 bg-white px-3 py-3"
        >
          <MapIcon className="size-5 text-public-blue" aria-hidden="true" />
          <span className="text-sm font-semibold text-ink">Live map</span>
          <span className="text-[11px] text-slate-500">
            Cases & cooling centers near you
          </span>
        </Link>
        <Link
          href="/epihack-2026/heat/resources.html"
          className="focus-ring flex flex-col gap-1 rounded-lg border border-slate-200 bg-white px-3 py-3"
        >
          <Gift className="size-5 text-warm-gold" aria-hidden="true" />
          <span className="text-sm font-semibold text-ink">County resources</span>
          <span className="text-[11px] text-slate-500">
            Help lines & relief for your area
          </span>
        </Link>
      </div>

      {/* Leaderboard */}
      <div className="flex flex-col gap-2">
        <h2 className="flex items-center gap-2 text-sm font-extrabold text-ink">
          <Trophy className="size-4 text-warm-gold" aria-hidden="true" />
          Community leaderboard
        </h2>
        <ul className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          {LEADERBOARD.sort((a, b) => b.reports - a.reports).map((row) => (
            <li
              key={row.zone}
              className={`flex items-center justify-between px-3 py-2 text-sm ${
                row.you ? 'bg-soft-mint font-semibold text-public-teal' : 'text-ink'
              }`}
            >
              <span>{row.zone}</span>
              <span className="tabular-nums">{row.reports} reports</span>
            </li>
          ))}
        </ul>
        <p className="text-[11px] text-slate-500">
          Demo leaderboard · aggregated by ZIP, never per-person.
        </p>
      </div>

      {/* Rewards */}
      <div className="flex flex-col gap-2">
        <h2 className="flex items-center gap-2 text-sm font-extrabold text-ink">
          <Gift className="size-4 text-warm-gold" aria-hidden="true" />
          Rewards for staying engaged
        </h2>
        {REWARDS.map((r) => (
          <div
            key={r.code}
            className="flex items-center justify-between rounded-md border border-amber-200 bg-amber-50 px-3 py-2"
          >
            <div>
              <p className="text-sm font-semibold text-ink">{r.perk}</p>
              <p className="text-[11px] text-slate-500">{r.partner}</p>
            </div>
            <code className="rounded bg-white px-2 py-1 text-xs font-bold text-amber-800">
              {r.code}
            </code>
          </div>
        ))}
      </div>

      {/* Weekly email opt-in */}
      <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-slate-200 bg-white px-3 py-3">
        <input
          type="checkbox"
          checked={weeklyEmail}
          onChange={(e) => {
            setWeeklyEmail(e.target.checked);
            window.localStorage.setItem(
              'weeklyEmailOptIn',
              e.target.checked ? '1' : '0'
            );
          }}
          className="mt-0.5 size-4 shrink-0 accent-public-teal"
        />
        <span className="flex-1">
          <span className="flex items-center gap-1 text-sm font-semibold text-ink">
            <Mail className="size-4 text-public-teal" aria-hidden="true" />
            Email me a weekly local summary
          </span>
          <span className="text-[11px] text-slate-500">
            For people who don&apos;t open the app often. Off by default; opt out
            anytime.
          </span>
        </span>
      </label>
    </section>
  );
}
