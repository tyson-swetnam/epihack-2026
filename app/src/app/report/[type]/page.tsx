/**
 * Per-type report flow. The route segment [type] is one of
 * 'human' | 'animal' | 'environmental' — anything else 404s.
 *
 * generateStaticParams is required because next.config.mjs sets
 * output: 'export'; static export needs an exhaustive list of the
 * route parameters to pre-render.
 *
 * This file is intentionally a thin shell. The multi-step form, the
 * photo capture, the EXIF strip, the location coarsening, and the
 * submit-and-spinner flow all live in the <ReportFlow /> client
 * component (next commit). Keeping the route as a server component
 * means the heavy JS only loads when the user picks a type.
 */
import { notFound } from 'next/navigation';
import type { Metadata } from 'next';

import { ReportFlow } from '@/components/ReportFlow';
import type { ReportType } from '@/lib/api-client';

const TYPES: ReportType[] = ['human', 'animal', 'environmental'];

export const dynamicParams = false; // 404 unknown [type] values

export function generateStaticParams() {
  return TYPES.map((type) => ({ type }));
}

export function generateMetadata({
  params,
}: {
  params: { type: string };
}): Metadata {
  if (!isReportType(params.type)) return {};
  const title = {
    human: 'Report a person',
    animal: 'Report an animal event',
    environmental: 'Report an environmental hazard',
  }[params.type];
  return { title: `${title} — AZ One Health Sentinel` };
}

export default function ReportTypePage({
  params,
}: {
  params: { type: string };
}) {
  if (!isReportType(params.type)) notFound();
  return <ReportFlow reportType={params.type} />;
}

function isReportType(s: string): s is ReportType {
  return (TYPES as string[]).includes(s);
}
