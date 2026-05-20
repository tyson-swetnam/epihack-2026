/**
 * Offline retry queue for report submissions (plan/09 Phase D).
 *
 * When a submit fails because the device is offline, the payload is parked in
 * localStorage and replayed on the next app load and whenever the browser
 * fires `online`. Keyed by a client-generated id (the server assigns the real
 * observation_id + claim_token once the report actually lands).
 *
 * Note: a queued retry re-sends the JSON payload only — an attached photo is
 * not persisted across an offline gap (Blobs don't belong in localStorage).
 */
import type { ReportPayload } from './api-shapes';

const KEY = 'onehealth:reportQueue';

export interface QueuedReport {
  id: string;
  payload: ReportPayload;
  ts: number;
}

function read(): QueuedReport[] {
  if (typeof window === 'undefined') return [];
  try {
    return JSON.parse(window.localStorage.getItem(KEY) || '[]') as QueuedReport[];
  } catch {
    return [];
  }
}

function write(items: QueuedReport[]): void {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(KEY, JSON.stringify(items));
}

export function enqueueReport(payload: ReportPayload): QueuedReport {
  const id =
    typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `q-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const item: QueuedReport = { id, payload, ts: Date.now() };
  write([...read(), item]);
  return item;
}

export function queuedCount(): number {
  return read().length;
}

/**
 * Replay every queued report through `send`. Items that still fail are kept
 * for the next attempt. Returns the number successfully sent.
 */
export async function flushQueue(
  send: (payload: ReportPayload) => Promise<unknown>
): Promise<number> {
  const items = read();
  if (items.length === 0) return 0;
  const remaining: QueuedReport[] = [];
  let sent = 0;
  for (const item of items) {
    try {
      await send(item.payload);
      sent += 1;
    } catch {
      remaining.push(item); // still offline / failing — keep for next time
    }
  }
  write(remaining);
  return sent;
}
