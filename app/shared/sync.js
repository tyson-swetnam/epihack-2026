// shared/sync.js
// Offline-first sync queue for AZ One Health Sentinel intake reports.
//
// Responsibilities
// ----------------
// 1. Persist reports captured while offline (or when the network drops mid-
//    submit) in IndexedDB, keyed by a UUID, with a vertical hint and a
//    monotonic timestamp.
// 2. Replay queued reports on demand: page load, `online` event, manual
//    "retry" button, or the service-worker's `sync` event handler (when
//    Background Sync is supported by the browser).
// 3. Notify subscribers whenever the queue length changes so UI badges
//    can update in real time.
//
// IndexedDB schema (v1)
// ---------------------
// Database: "az-onehealth-sentinel"
// Object store: "pending_reports" (keyPath: "id")
//   { id:           UUIDv4 string,
//     enqueued_at:  ISO-8601 string,
//     flow:         e.g. "tick_mailin" / "heat_chw_checkin",
//     vertical:     "vbd" | "heat",
//     mock_key:     optional mock-response selector,
//     api_base:     captured at enqueue time (so a later browser-session
//                   on a different network still targets the same host),
//     payload:      the Minimum-Dataset shaped JSON object,
//     retries:      integer, capped at MAX_RETRIES,
//     last_error:   string | null }
//   Index "by_enqueued_at" on "enqueued_at" for FIFO replay order.
//
// Browser-support fallbacks
// -------------------------
// * IndexedDB is supported by every browser we target. We do NOT keep a
//   localStorage shim — if IDB is unavailable the page surfaces the
//   intake error inline and falls back to the original online-only
//   behavior.
// * Background Sync (`ServiceWorkerRegistration.sync`) is Chromium-only
//   in 2026. On Safari/Firefox we rely on the `online` event plus a
//   manual retry button in the sync-status pill UI. See app/README.md
//   "Offline + sync-on-reconnect" for the user-visible difference.

const DB_NAME    = 'az-onehealth-sentinel';
const DB_VERSION = 1;
const STORE      = 'pending_reports';
const MAX_RETRIES = 5;
const SYNC_TAG    = 'az-sentinel-intake-replay';

// ---------------------------------------------------------------------------
// Tiny IndexedDB helper — promise wrapper around the bits we actually use.
// We deliberately avoid pulling in idb-keyval or similar to keep the no-build
// constraint clean.
// ---------------------------------------------------------------------------
function openDb() {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === 'undefined') {
      reject(new Error('IndexedDB unavailable in this environment'));
      return;
    }
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        const store = db.createObjectStore(STORE, { keyPath: 'id' });
        store.createIndex('by_enqueued_at', 'enqueued_at', { unique: false });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror   = () => reject(req.error);
  });
}

function tx(db, mode) {
  return db.transaction(STORE, mode).objectStore(STORE);
}

function awaitReq(r) {
  return new Promise((resolve, reject) => {
    r.onsuccess = () => resolve(r.result);
    r.onerror   = () => reject(r.error);
  });
}

// ---------------------------------------------------------------------------
// Subscribers
// ---------------------------------------------------------------------------
const listeners = new Set();

function notify(count) {
  listeners.forEach((cb) => {
    try { cb(count); } catch (e) { /* never let one bad subscriber kill the rest */ }
  });
}

/**
 * Subscribe to queue-length changes. The callback fires immediately with the
 * current count and again whenever it changes locally. (Cross-tab updates
 * arrive via the BroadcastChannel below.)
 *
 * @returns {() => void} unsubscribe
 */
export function subscribe(cb) {
  listeners.add(cb);
  // Fire once with the current length so the UI can paint without waiting
  // for the first mutation.
  pendingCount().then((n) => { try { cb(n); } catch (_) {} });
  return () => listeners.delete(cb);
}

// Cross-tab heads-up so that if the SW completes a sync the landing page's
// pill updates even when the form page is still open.
let bc = null;
try {
  if (typeof BroadcastChannel !== 'undefined') {
    bc = new BroadcastChannel('az-sentinel-sync');
    bc.onmessage = (ev) => {
      if (ev.data && ev.data.kind === 'queue-changed') {
        pendingCount().then(notify);
      }
    };
  }
} catch (_) { /* not fatal */ }

function broadcastChanged() {
  pendingCount().then((n) => {
    notify(n);
    if (bc) bc.postMessage({ kind: 'queue-changed', count: n });
  });
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------
function uuid() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
  // RFC4122-ish v4 fallback.
  const tpl = '10000000-1000-4000-8000-100000000000';
  return tpl.replace(/[018]/g, (c) =>
    (c ^ (crypto.getRandomValues(new Uint8Array(1))[0] & (15 >> (c / 4))))
      .toString(16)
  );
}

function resolveApiBase() {
  if (typeof document === 'undefined') return null;
  const attr = document.body && document.body.getAttribute('data-api-base');
  if (!attr || attr === 'mock') return null;
  return attr.replace(/\/+$/, '');
}

/**
 * Enqueue a report for later replay.
 *
 * @param {object} report
 * @param {string} report.flow
 * @param {string} [report.vertical]
 * @param {string} [report.mock_key]
 * @param {object} report.payload   Minimum-Dataset shaped JSON.
 * @returns {Promise<string>} the new report id.
 */
export async function enqueueReport(report) {
  if (!report || !report.flow || !report.payload) {
    throw new Error('enqueueReport: flow and payload are required');
  }
  const rec = {
    id:          uuid(),
    enqueued_at: new Date().toISOString(),
    flow:        report.flow,
    vertical:    report.vertical || 'vbd',
    mock_key:    report.mock_key || null,
    api_base:    resolveApiBase(),         // null => mock-mode page
    payload:     report.payload,
    retries:     0,
    last_error:  null
  };
  const db = await openDb();
  try {
    await awaitReq(tx(db, 'readwrite').add(rec));
  } finally {
    db.close();
  }
  // Best-effort: ask the SW to fire a Background Sync the next time the
  // device is online. (Caller can also call replayAll() directly.)
  await requestBackgroundSync();
  broadcastChanged();
  return rec.id;
}

/**
 * List every pending report, oldest first.
 * @returns {Promise<object[]>}
 */
export async function pendingReports() {
  const db = await openDb();
  try {
    const store = tx(db, 'readonly');
    const idx   = store.index('by_enqueued_at');
    return await awaitReq(idx.getAll());
  } finally {
    db.close();
  }
}

/**
 * Pending-count, cheaper than pendingReports() when you only need the badge.
 * @returns {Promise<number>}
 */
export async function pendingCount() {
  try {
    const db = await openDb();
    try {
      return await awaitReq(tx(db, 'readonly').count());
    } finally {
      db.close();
    }
  } catch (_) {
    return 0;
  }
}

async function deleteReport(id) {
  const db = await openDb();
  try {
    await awaitReq(tx(db, 'readwrite').delete(id));
  } finally {
    db.close();
  }
}

async function bumpRetry(rec, errMsg) {
  rec.retries    = (rec.retries || 0) + 1;
  rec.last_error = String(errMsg || '').slice(0, 500);
  const db = await openDb();
  try {
    await awaitReq(tx(db, 'readwrite').put(rec));
  } finally {
    db.close();
  }
}

/**
 * POST a single queued report. Returns the parsed JSON response on success.
 * Caller is responsible for catching and handling failure.
 */
async function postOne(rec) {
  if (!rec.api_base) {
    // Captured in mock mode — there is no real endpoint. We treat this as
    // an immediate "success" so the queue drains in demo environments
    // (the success card was already shown to the user at enqueue time).
    return { mock: true, observation_id: rec.id, replayed: true };
  }
  const form = new FormData();
  form.append('flow',     rec.flow);
  form.append('vertical', rec.vertical);
  form.append('payload',  new Blob([JSON.stringify(rec.payload)],
                                   { type: 'application/json' }));
  const res = await fetch(`${rec.api_base}/api/intake`, {
    method: 'POST',
    body:   form,
    // Critical: do not send credentials by default for offline replays;
    // the page's own intake-client.js never does either.
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} ${res.statusText}`);
  }
  return await res.json();
}

/**
 * Replay every pending report. Each success deletes the row; each failure
 * bumps retries (capped at MAX_RETRIES, after which the row is left alone
 * until a manual retry).
 *
 * @returns {Promise<{ sent: number, failed: number, skipped: number }>}
 */
export async function replayAll() {
  const out = { sent: 0, failed: 0, skipped: 0 };
  if (typeof navigator !== 'undefined' && navigator.onLine === false) {
    out.skipped = (await pendingReports()).length;
    return out;
  }
  const items = await pendingReports();
  for (const rec of items) {
    if ((rec.retries || 0) >= MAX_RETRIES) {
      out.skipped += 1;
      continue;
    }
    try {
      await postOne(rec);
      await deleteReport(rec.id);
      out.sent += 1;
      // One success notification per row so the UI can show a toast
      // ("Report synced") in foreground tabs.
      try {
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new CustomEvent('sentinel:synced', {
            detail: { id: rec.id, flow: rec.flow }
          }));
        }
      } catch (_) {}
    } catch (e) {
      await bumpRetry(rec, e && e.message);
      out.failed += 1;
    }
  }
  broadcastChanged();
  return out;
}

// ---------------------------------------------------------------------------
// Background-sync registration (Chromium-only as of 2026; harmless on Safari)
// ---------------------------------------------------------------------------
async function requestBackgroundSync() {
  try {
    if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) return;
    const reg = await navigator.serviceWorker.ready;
    if (reg && 'sync' in reg) {
      await reg.sync.register(SYNC_TAG);
    }
  } catch (_) {
    // Background Sync not supported (Safari/Firefox). The `online` event
    // listener below + the manual retry button cover the fallback path.
  }
}

// On every page that imports this module: when the device comes back
// online, kick off a replay. This is the fallback for browsers without
// Background Sync.
if (typeof window !== 'undefined') {
  window.addEventListener('online', () => {
    replayAll().catch(() => { /* surfaced via subscribers */ });
  });
  // Also try once on load, in case we were offline at enqueue time but
  // are back online by the time the page reopens.
  window.addEventListener('load', () => {
    if (navigator.onLine !== false) {
      replayAll().catch(() => {});
    } else {
      // Still call subscribers so the badge paints accurately.
      broadcastChanged();
    }
  });
}

// Re-export some constants for tests + the UI badge.
export const SYNC_CONSTANTS = Object.freeze({
  DB_NAME, DB_VERSION, STORE, MAX_RETRIES, SYNC_TAG
});
