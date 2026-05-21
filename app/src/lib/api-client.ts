/**
 * Typed HTTP client for the Intake API.
 *
 * Generation:
 *   npm run gen:api
 * regenerates ./api-types.ts from ../api/openapi.yaml via
 * openapi-typescript. Until that runs the type imports below
 * resolve to placeholder shapes (see api-types-fallback.ts) so
 * the project still type-checks on a fresh clone.
 *
 * Privacy boundary (plan/06-mobile-app.md):
 *   - The client never sends precise lat/lon at the API layer.
 *     Coarsening happens in `coarseSubmit` before the request.
 *   - The client never accepts EXIF data through the photo path
 *     without it having been through `stripExif()` first.
 *
 * Mock mode:
 *   NEXT_PUBLIC_API_BASE === 'mock' (the default for the GitHub
 *   Pages build) short-circuits every call to a bundled fixture
 *   under src/mocks/.
 */
import type { ReportPayload, ReportAck, ReportStatus, ProfilePatch, ContextEnvelope } from './api-shapes';

export type ReportType = 'human' | 'animal' | 'environmental';

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'mock';

// Which client this build is. The Capacitor mobile build sets
// NEXT_PUBLIC_CLIENT_CHANNEL=mobile so the API routes its writes to MongoDB;
// the web build leaves it 'web' (DuckLake). See plan/09-mobile-datastore.md.
const CLIENT_CHANNEL = process.env.NEXT_PUBLIC_CLIENT_CHANNEL ?? 'web';

function isMock(): boolean {
  return BASE === 'mock';
}

async function loadMock<T>(key: string): Promise<T> {
  // Mocks live next to the client as static JSON; bundlers inline them.
  const res = await fetch(`/epihack-2026/app/_next/static/mocks/${key}.json`, {
    cache: 'no-store',
  }).catch(() => null);
  if (res && res.ok) return (await res.json()) as T;
  // Dev fallback: import from src/mocks (works under `next dev`).
  const mod = await import(`@/mocks/${key}.json`);
  return mod.default as T;
}

/**
 * Submit a report. Throws on network failure or a non-2xx response — used
 * directly by the offline-queue flush. Most callers want `createReport`,
 * which adds offline queueing on top.
 *
 * The caller is responsible for:
 *   - stripping EXIF GPS from `photo` (see lib/exif-stripper.ts);
 *   - coarsening any precise lat/lon to ZIP / 1 km cell before
 *     building `payload.coarse_location`.
 */
export async function createReportRaw(
  payload: ReportPayload,
  photo?: Blob | null,
  opts: { signal?: AbortSignal } = {}
): Promise<ReportAck> {
  if (isMock()) {
    await sleep(1200); // simulate agent-chain latency for the spinner
    const ack = await loadMock<ReportAck>('reports.create');
    return {
      ...ack,
      observation_id: synthUuid(),
      claim_token: synthToken(),
    };
  }
  const form = new FormData();
  // Append as a plain string, NOT a Blob: a Blob becomes a multipart *file*
  // part (filename "blob"), which the API's `payload: str = Form(...)` rejects
  // with a 422. A string is a normal text field, which it parses as JSON.
  form.append('payload', JSON.stringify(payload));
  if (photo) form.append('photo', photo, 'report.jpg');
  const res = await fetch(`${BASE}/v1/reports`, {
    method: 'POST',
    headers: { 'X-Client-Channel': CLIENT_CHANNEL },
    body: form,
    signal: opts.signal,
  });
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return (await res.json()) as ReportAck;
}

/**
 * Submit a report, queueing it for later if the device is offline. A network
 * failure (no response — distinct from an HTTP error) parks the JSON payload
 * in the offline queue and returns a `queued` ack; the queue is replayed on
 * the next load / when the browser comes back online. HTTP errors (4xx/5xx)
 * still throw so the UI can surface a real validation problem.
 */
export async function createReport(
  payload: ReportPayload,
  photo?: Blob | null,
  opts: { signal?: AbortSignal } = {}
): Promise<ReportAck> {
  try {
    return await createReportRaw(payload, photo, opts);
  } catch (err) {
    if (err instanceof ApiError) throw err; // real server-side rejection
    // Network/offline error: queue the payload (photo is dropped on retry).
    const { enqueueReport } = await import('./offline-queue');
    const q = enqueueReport(payload);
    return {
      observation_id: q.id,
      claim_token: '',
      status_url: `/v1/reports/${q.id}`,
      queued: true,
    };
  }
}

export async function getReportStatus(
  observationId: string,
  claimToken: string
): Promise<ReportStatus> {
  if (isMock()) {
    await sleep(200);
    const status = await loadMock<ReportStatus>('reports.status');
    return { ...status, observation_id: observationId };
  }
  const res = await fetch(`${BASE}/v1/reports/${observationId}`, {
    headers: { Authorization: `Claim ${claimToken}` },
  });
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return (await res.json()) as ReportStatus;
}

export async function attachProfile(
  observationId: string,
  claimToken: string,
  profile: ProfilePatch
): Promise<ReportStatus> {
  if (isMock()) {
    await sleep(400);
    const status = await loadMock<ReportStatus>('reports.status');
    return { ...status, observation_id: observationId, profile_attached: true };
  }
  const res = await fetch(`${BASE}/v1/reports/${observationId}/profile`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Claim ${claimToken}`,
    },
    body: JSON.stringify(profile),
  });
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return (await res.json()) as ReportStatus;
}

export async function getContext(
  loc: { zip?: string; grid_id?: string }
): Promise<ContextEnvelope> {
  if (isMock()) {
    await sleep(200);
    return await loadMock<ContextEnvelope>('context.zip');
  }
  const qs = new URLSearchParams();
  if (loc.zip) qs.set('zip', loc.zip);
  if (loc.grid_id) qs.set('grid_id', loc.grid_id);
  const res = await fetch(`${BASE}/v1/context?${qs.toString()}`);
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return (await res.json()) as ContextEnvelope;
}

export class ApiError extends Error {
  constructor(public status: number, public body: string) {
    super(`API ${status}: ${body.slice(0, 200)}`);
  }
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function synthUuid(): string {
  const tpl = '10000000-1000-4000-8000-100000000000';
  return tpl.replace(/[018]/g, (c) =>
    (
      Number(c) ^
      (crypto.getRandomValues(new Uint8Array(1))[0]! & (15 >> (Number(c) / 4)))
    ).toString(16)
  );
}

function synthToken(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
}
