// app/sw.js
// Service worker for AZ One Health Sentinel. Scope = /app/.
//
// Caching strategies (three)
// --------------------------
// 1. App shell (HTML + CSS + JS shipped from /app/):
//    * Strategy: cache-first with a stale-while-revalidate background
//      refresh, so the form pages open instantly offline and the next
//      online navigation pulls fresh JS into the cache for the visit
//      after that.
//    * Pre-cached on `install` with the manifest below.
// 2. Mock-response fixtures, the i18n bundle, and canned cooling-center
//    data (mock-responses.json under /app/heat/, /app/, etc.):
//    * Strategy: stale-while-revalidate. The user gets the cached copy
//      instantly; in the background we refresh so the next page-load
//      can show updated fixtures without a hard reload.
// 3. Outbound POST /api/intake:
//    * If online: passthrough.
//    * If offline OR the fetch errors out: respond with a synthetic
//      202 Accepted + { "queued": true, "via": "sw" } and tell the
//      page (via postMessage) that it should enqueue via
//      app/shared/sync.js. The page is the source of truth for the
//      payload because the SW does not have access to the original
//      FormData by the time fetch() rejects.
//
// A separate "background sync" handler triggers the page to re-run
// replayAll() the next time the device gets connectivity, where the
// browser supports it (Chromium). Safari/Firefox fall back to the
// `online` event registered in app/shared/sync.js.
//
// IMPORTANT: scope is /app/ (NOT site-wide). The registration call in
// each form page passes { scope: '/app/' }, and this file is served
// from /app/sw.js so the browser allows that scope.

const VERSION = 'v1-2026-05-19';
const SHELL_CACHE   = `sentinel-shell-${VERSION}`;
const FIXTURE_CACHE = `sentinel-fixtures-${VERSION}`;
const SYNC_TAG      = 'az-sentinel-intake-replay';

// Files we want available offline on first install. Keep this list tight —
// listing everything would make the install transaction fragile.
const SHELL_URLS = [
  '/app/',
  '/app/index.html',
  '/app/manifest.webmanifest',

  '/app/shared/style.css',
  '/app/shared/geo.js',
  '/app/shared/i18n.js',
  '/app/shared/intake-client.js',
  '/app/shared/sync.js',
  '/app/shared/install-prompt.js',

  '/app/tick/index.html',
  '/app/tick/tick.js',
  '/app/tick/tick.css',

  '/app/heat/index.html',
  '/app/heat/heat.css',
  '/app/heat/heat-shared.js',
  '/app/heat/check-in/index.html',
  '/app/heat/check-in/check-in.js',
  '/app/heat/self-report/index.html',
  '/app/heat/self-report/self-report.js',
  '/app/heat/cool-off/index.html',
  '/app/heat/cool-off/cool-off.js',

  '/app/icons/icon-192.png',
  '/app/icons/icon-512.png',
  '/app/icons/icon.svg',
];

// Fixtures handled via SWR rather than precached. Listed here so they
// land in the fixture cache eagerly on first install too, but we don't
// fail install if any one of them 404s (dev environments may not have
// every file yet).
const FIXTURE_URLS = [
  '/app/mock-responses.json',
  '/app/heat/mock-responses.json',
];

// ---------------------------------------------------------------------------
// install: warm both caches.
// ---------------------------------------------------------------------------
self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const shell = await caches.open(SHELL_CACHE);
    // addAll() is atomic — if any URL fails the install aborts. We tolerate
    // a missing file by adding them one-by-one and ignoring failures, so a
    // partial dev tree doesn't brick the SW.
    await Promise.all(SHELL_URLS.map(async (u) => {
      try { await shell.add(new Request(u, { cache: 'reload' })); }
      catch (e) { console.warn('[sw] shell skip:', u, e && e.message); }
    }));
    const fix = await caches.open(FIXTURE_CACHE);
    await Promise.all(FIXTURE_URLS.map(async (u) => {
      try { await fix.add(new Request(u, { cache: 'reload' })); }
      catch (e) { /* fixtures are non-fatal */ }
    }));
    // Activate the new SW as soon as install finishes so users on a freshly
    // updated build don't get the old one.
    await self.skipWaiting();
  })());
});

// ---------------------------------------------------------------------------
// activate: prune old versions.
// ---------------------------------------------------------------------------
self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keep = new Set([SHELL_CACHE, FIXTURE_CACHE]);
    const names = await caches.keys();
    await Promise.all(names.map((n) => keep.has(n) ? null : caches.delete(n)));
    await self.clients.claim();
  })());
});

// ---------------------------------------------------------------------------
// fetch router
// ---------------------------------------------------------------------------
self.addEventListener('fetch', (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Only handle same-origin requests. Cross-origin (tel:, mailto:, third
  // parties) passes through untouched.
  if (url.origin !== self.location.origin) return;

  // Scope guard: only intercept /app/ paths. The rest of the static site
  // (map/, graph/, plan/, root index.html) must NOT be aggressively
  // cached by us — that's the static-site CDN's job.
  if (!url.pathname.startsWith('/app/')) return;

  // POST /api/intake — the offline-replay hotspot.
  if (req.method === 'POST' &&
      url.pathname.startsWith('/api/intake')) {
    event.respondWith(handleIntakePost(event));
    return;
  }

  // Only GETs are cacheable below.
  if (req.method !== 'GET') return;

  // Fixtures: stale-while-revalidate.
  if (isFixture(url)) {
    event.respondWith(staleWhileRevalidate(req, FIXTURE_CACHE));
    return;
  }

  // App shell (HTML / CSS / JS / icons): cache-first + SWR refresh.
  event.respondWith(cacheFirstSWR(req, SHELL_CACHE));
});

function isFixture(url) {
  return url.pathname.endsWith('mock-responses.json');
}

// ---------------------------------------------------------------------------
// Strategy implementations
// ---------------------------------------------------------------------------
async function cacheFirstSWR(req, cacheName) {
  const cache = await caches.open(cacheName);
  const hit   = await cache.match(req, { ignoreSearch: false });
  // Kick off a background refresh either way (when online).
  const refresh = fetch(req).then((res) => {
    if (res && res.ok && (res.type === 'basic' || res.type === 'default')) {
      cache.put(req, res.clone()).catch(() => {});
    }
    return res;
  }).catch(() => null);
  if (hit) return hit;
  const fresh = await refresh;
  if (fresh) return fresh;
  // Final fallback: offline + uncached. For HTML navigations, hand back
  // the app shell so the page at least renders a shell skeleton.
  if (req.mode === 'navigate') {
    const shellHit = await cache.match('/app/index.html');
    if (shellHit) return shellHit;
  }
  return new Response('Offline and resource not in cache', {
    status: 503, statusText: 'Service Unavailable'
  });
}

async function staleWhileRevalidate(req, cacheName) {
  const cache = await caches.open(cacheName);
  const hit   = await cache.match(req);
  const fetchPromise = fetch(req).then((res) => {
    if (res && res.ok) cache.put(req, res.clone()).catch(() => {});
    return res;
  }).catch(() => null);
  return hit || (await fetchPromise) ||
         new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
}

// ---------------------------------------------------------------------------
// /api/intake handling
// ---------------------------------------------------------------------------
async function handleIntakePost(event) {
  // Try the network first. If that fails (offline) OR returns non-2xx,
  // respond with a synthetic 202 and signal the page to enqueue.
  try {
    const res = await fetch(event.request.clone());
    if (res && res.ok) return res;
    // Server errors are also a candidate for offline-queueing, but only
    // when the user is actually offline — a real 5xx from a reachable
    // server should surface to the page so the user sees the failure.
    if (!self.navigator.onLine) {
      return queuedResponse('server-unreachable');
    }
    return res;
  } catch (err) {
    // Network failure (DNS, CORS, offline). Tell the page to enqueue.
    return queuedResponse(err && err.message);
  }
}

function queuedResponse(reason) {
  // 202 Accepted is the right semantic: we've taken responsibility for
  // the report, the work is pending. The page reads `queued: true` and
  // routes through sync.js instead of treating this as a success.
  return new Response(JSON.stringify({
    queued: true,
    via:    'service-worker',
    reason: reason || 'offline'
  }), {
    status:  202,
    statusText: 'Accepted (queued for sync)',
    headers: { 'Content-Type': 'application/json' }
  });
}

// ---------------------------------------------------------------------------
// Background Sync — Chromium-only.
// ---------------------------------------------------------------------------
self.addEventListener('sync', (event) => {
  if (event.tag !== SYNC_TAG) return;
  event.waitUntil(replayViaClients());
});

// We don't have the original payloads here directly — they live in IndexedDB
// owned by the page's `app/shared/sync.js`. We notify every active client to
// run `replayAll()`. If there are NO clients (true background sync after the
// tab was closed) we fall back to a minimal in-SW replay by reading the
// same IndexedDB store directly.
async function replayViaClients() {
  const clientsList = await self.clients.matchAll({
    type: 'window', includeUncontrolled: true
  });
  if (clientsList.length > 0) {
    for (const c of clientsList) {
      c.postMessage({ kind: 'replay-now' });
    }
    return;
  }
  // No window clients open — replay directly from the SW.
  await swDirectReplay();
}

// Minimal duplicate of the page-side replayAll() so background-sync works
// even with no tab open. Kept intentionally small (no retry bookkeeping
// beyond a single attempt; the page will reconcile on next open).
async function swDirectReplay() {
  try {
    const db = await new Promise((resolve, reject) => {
      const r = indexedDB.open('az-onehealth-sentinel', 1);
      r.onsuccess = () => resolve(r.result);
      r.onerror   = () => reject(r.error);
    });
    const items = await new Promise((resolve, reject) => {
      const tx = db.transaction('pending_reports', 'readonly');
      const all = tx.objectStore('pending_reports').getAll();
      all.onsuccess = () => resolve(all.result);
      all.onerror   = () => reject(all.error);
    });
    for (const rec of items || []) {
      if (!rec.api_base) {
        // Mock-mode rec — drop it; the demo's already shown success UI.
        await deleteRec(db, rec.id);
        continue;
      }
      try {
        const form = new FormData();
        form.append('flow',     rec.flow);
        form.append('vertical', rec.vertical || 'vbd');
        form.append('payload',  new Blob([JSON.stringify(rec.payload)],
                                         { type: 'application/json' }));
        const res = await fetch(`${rec.api_base}/api/intake`, {
          method: 'POST', body: form
        });
        if (res && res.ok) {
          await deleteRec(db, rec.id);
          // No active tab to receive a "sentinel:synced" event — surface
          // via a Notification instead, where the user granted permission.
          await maybeNotifySynced(rec);
        }
      } catch (_) { /* keep for next sync */ }
    }
    db.close();
  } catch (_) { /* nothing to replay */ }
}

function deleteRec(db, id) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction('pending_reports', 'readwrite');
    const del = tx.objectStore('pending_reports').delete(id);
    del.onsuccess = () => resolve();
    del.onerror   = () => reject(del.error);
  });
}

async function maybeNotifySynced(rec) {
  try {
    if (!self.registration || !self.registration.showNotification) return;
    if (Notification && Notification.permission !== 'granted') return;
    await self.registration.showNotification('Sentinel report synced', {
      body: `Your ${rec.flow.replace(/_/g, ' ')} report just uploaded.`,
      icon: '/app/icons/icon-192.png',
      tag:  'sentinel-sync',
      renotify: false
    });
  } catch (_) { /* notifications are best-effort */ }
}

// ---------------------------------------------------------------------------
// Page-initiated messaging
// ---------------------------------------------------------------------------
self.addEventListener('message', (event) => {
  const d = event.data || {};
  if (d.kind === 'skip-waiting') self.skipWaiting();
  if (d.kind === 'ping') event.source && event.source.postMessage({ kind: 'pong' });
});
