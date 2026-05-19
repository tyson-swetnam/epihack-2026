// shared/sw-register.js
// Register the AZ One Health Sentinel service worker and mount the
// sync-status pill UI on any page that imports this module.
//
// Why one shared helper?
// ----------------------
// Every form page (tick, heat check-in, heat self-report) needs the
// exact same wiring: register /app/sw.js with scope /app/, listen for
// `sentinel:synced` to flash a toast, subscribe to the IDB queue for
// the pending-count badge, and run replayAll() on `online`.
// Centralising it here keeps the per-page bootstrapping to a single
// import.

import { subscribe, replayAll, pendingCount } from './sync.js';

const STYLE_ID = 'sentinel-sync-pill-style';

const PILL_CSS = `
  .sentinel-sync-pill {
    display: inline-flex;
    align-items: center;
    gap: .3rem;
    margin-left: .5rem;
    padding: 2px 9px;
    border-radius: 999px;
    font-size: .72rem;
    font-weight: 600;
    background: rgba(255,255,255,.18);
    color: #fff;
    border: 1px solid rgba(255,255,255,.3);
    vertical-align: middle;
    line-height: 1.5;
    user-select: none;
  }
  .sentinel-sync-pill[data-state="synced"]  { background: rgba(76,175,80,.85); border-color: rgba(255,255,255,.35); }
  .sentinel-sync-pill[data-state="pending"] { background: rgba(255,179,0,.92); color: #1a1a1a; border-color: rgba(0,0,0,.1); cursor: pointer; }
  .sentinel-sync-pill[data-state="syncing"] { background: rgba(31,143,191,.95); }
  .sentinel-sync-pill[data-state="offline"] { background: rgba(192,57,43,.92); }
  .sentinel-sync-pill .dot {
    width: 8px; height: 8px; border-radius: 50%; background: currentColor; opacity: .85;
  }
  .sentinel-sync-pill[data-state="syncing"] .dot { animation: sentinel-pulse .9s ease-in-out infinite; }
  @keyframes sentinel-pulse { 0%,100% { opacity: .3; } 50% { opacity: 1; } }
  @media (prefers-reduced-motion: reduce) {
    .sentinel-sync-pill[data-state="syncing"] .dot { animation: none; }
  }

  .sentinel-sync-toast {
    position: fixed;
    left: 50%;
    bottom: calc(env(safe-area-inset-bottom, 0px) + 5.5rem);
    transform: translateX(-50%);
    background: #1a1a1a;
    color: #fff;
    padding: .55rem 1rem;
    border-radius: 999px;
    font-size: .85rem;
    box-shadow: 0 6px 18px rgba(0,0,0,.25);
    z-index: 9999;
    opacity: 0;
    pointer-events: none;
    transition: opacity .25s ease;
  }
  .sentinel-sync-toast.show { opacity: 1; }
  @media (prefers-reduced-motion: reduce) {
    .sentinel-sync-toast { transition: none; }
  }
`;

function injectStyle() {
  if (document.getElementById(STYLE_ID)) return;
  const s = document.createElement('style');
  s.id = STYLE_ID;
  s.textContent = PILL_CSS;
  document.head.appendChild(s);
}

/**
 * Register the service worker. Safe to call multiple times.
 * Returns the registration (or null in browsers that don't support SW).
 */
export async function registerServiceWorker() {
  if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) {
    return null;
  }
  try {
    const reg = await navigator.serviceWorker.register('/app/sw.js', { scope: '/app/' });
    // Wire SW->page replay trigger.
    navigator.serviceWorker.addEventListener('message', (ev) => {
      const d = ev.data || {};
      if (d.kind === 'replay-now') {
        replayAll().catch(() => {});
      }
    });
    return reg;
  } catch (err) {
    // Most often: opened via file:// or a path that puts sw.js out of scope.
    console.warn('[sw] registration failed:', err && err.message);
    return null;
  }
}

/**
 * Mount the sync-status pill into the given parent (default: the
 * page's first <header> h1). Returns a teardown function.
 */
export function mountSyncPill(parent) {
  injectStyle();
  const host = parent || document.querySelector('header h1') || document.body;
  if (!host) return () => {};

  // If the host is a <header> rather than the title element, prefer to
  // sit next to the h1 inside it.
  const inlineTarget = host.tagName === 'H1' ? host : host.querySelector('h1') || host;

  let pill = inlineTarget.querySelector(':scope > .sentinel-sync-pill');
  if (!pill) {
    pill = document.createElement('span');
    pill.className = 'sentinel-sync-pill';
    pill.setAttribute('role', 'status');
    pill.setAttribute('aria-live', 'polite');
    pill.innerHTML = '<span class="dot" aria-hidden="true"></span><span class="label">…</span>';
    inlineTarget.appendChild(pill);
  }
  const label = pill.querySelector('.label');

  // Click to manually trigger replay (essential on iOS where there's no
  // Background Sync API).
  pill.addEventListener('click', async () => {
    if (pill.dataset.state === 'pending') {
      pill.dataset.state = 'syncing';
      label.textContent = 'syncing…';
      await replayAll().catch(() => {});
    }
  });

  function paint(count) {
    if (typeof navigator !== 'undefined' && navigator.onLine === false) {
      pill.dataset.state = 'offline';
      label.textContent = count > 0 ? `offline · ${count} pending` : 'offline';
      pill.title = 'No network. Pending reports will sync automatically on reconnect.';
      return;
    }
    if (count > 0) {
      pill.dataset.state = 'pending';
      label.textContent = `${count} pending`;
      pill.title = 'Tap to retry the queued reports now.';
    } else {
      pill.dataset.state = 'synced';
      label.textContent = 'synced';
      pill.title = 'All reports uploaded.';
    }
  }

  const unsub = subscribe(paint);
  // Repaint on network changes too.
  const onlineHandler  = () => pendingCount().then(paint);
  const offlineHandler = () => pendingCount().then(paint);
  window.addEventListener('online',  onlineHandler);
  window.addEventListener('offline', offlineHandler);

  // Toast on each successful sync.
  let toast;
  const syncedHandler = (ev) => {
    if (!toast) {
      toast = document.createElement('div');
      toast.className = 'sentinel-sync-toast';
      toast.setAttribute('role', 'status');
      toast.setAttribute('aria-live', 'polite');
      document.body.appendChild(toast);
    }
    const flow = (ev && ev.detail && ev.detail.flow) || 'report';
    toast.textContent = `✓ ${flow.replace(/_/g, ' ')} synced`;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2400);
  };
  window.addEventListener('sentinel:synced', syncedHandler);

  return () => {
    unsub();
    window.removeEventListener('online',  onlineHandler);
    window.removeEventListener('offline', offlineHandler);
    window.removeEventListener('sentinel:synced', syncedHandler);
  };
}

/**
 * Convenience: do both at once on DOMContentLoaded.
 */
export function bootstrapOfflineUi(opts = {}) {
  const init = () => {
    registerServiceWorker();
    mountSyncPill(opts.pillParent);
  };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
}
