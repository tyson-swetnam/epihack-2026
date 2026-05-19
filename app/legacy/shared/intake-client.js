// shared/intake-client.js
// Thin fetch wrapper that posts a Minimum-Dataset payload to the
// IntakeAgent endpoint (/api/intake by default).
//
// In production (real deployment) the page should be served with a
// data-api-base attribute on <body> pointing at the real backend:
//
//   <body data-api-base="https://sentinel.example.org">
//
// In the hackathon prototype, GitHub Pages has no backend, so we
// short-circuit to the canned response in mock-responses.json when:
//   * data-api-base is absent or
//   * data-api-base="mock"
//
// Swapping in a real backend later is changing one HTML attribute.

// Each vertical has its own mock-responses.json next to its top-level
// folder, so the tick flow can ship without bundling heat fixtures and
// vice versa. Default vertical is "vbd" (the existing tick mail-in).
const MOCK_URLS = {
  vbd:  new URL('../mock-responses.json',          import.meta.url).href,
  heat: new URL('../heat/mock-responses.json',     import.meta.url).href,
};

function resolveBase() {
  const attr = document.body && document.body.getAttribute('data-api-base');
  if (!attr || attr === 'mock') return null;
  return attr.replace(/\/+$/, '');
}

async function loadMockResponse(flow, vertical) {
  const url = MOCK_URLS[vertical] || MOCK_URLS.vbd;
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) throw new Error(`mock-responses.json missing for ${vertical}`);
  const all = await res.json();
  const r = all[flow];
  if (!r) throw new Error(`mock response for flow=${flow} not found in ${vertical}`);
  return r;
}

// Simulated latency so the spinner is actually visible during the demo.
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * Post an intake payload.
 *
 * @param {string} flow      e.g. 'tick_mailin', 'heat_chw_checkin'
 * @param {object} payload   Minimum-Dataset shaped object
 * @param {object} opts      { signal?: AbortSignal, photoBlob?: Blob|File,
 *                             vertical?: 'vbd' | 'heat',
 *                             mockKey?: string }
 *
 *   - vertical selects which mock-responses.json gets loaded in mock mode.
 *     Defaults to 'vbd' for backward compatibility with the tick flow.
 *   - mockKey lets a flow request a *specific* canned response (e.g. the
 *     heat flow has one canned response per tc.* triage class so the
 *     demo can show each branch). Falls back to `flow` if absent.
 *
 * @returns {Promise<object>} the IntakeAgent → … → NotificationAgent result
 */
export async function submitIntake(flow, payload, opts = {}) {
  const base = resolveBase();
  const vertical = opts.vertical || 'vbd';

  if (base === null) {
    // Mock mode: simulate 1.4 s of agent chain latency so the spinner
    // is visible, then merge the canned response with a synthesized id.
    await sleep(1400);
    const canned = await loadMockResponse(opts.mockKey || flow, vertical);
    return {
      ...canned,
      observation_id: synthId(),
      received_at: new Date().toISOString(),
      mock: true
    };
  }

  // Real mode: multipart so the photo can travel with the JSON.
  const form = new FormData();
  form.append('flow', flow);
  form.append('vertical', vertical);
  form.append('payload', new Blob([JSON.stringify(payload)],
                                  { type: 'application/json' }));
  if (opts.photoBlob) form.append('photo', opts.photoBlob, 'tick.jpg');

  const res = await fetch(`${base}/api/intake`, {
    method: 'POST',
    body: form,
    signal: opts.signal
  });
  // The service worker (app/sw.js) hands back a 202 + { queued: true } when
  // it has caught an offline submission. Surface that to callers verbatim
  // so they can route through the IDB sync queue without retrying.
  if (res.status === 202) {
    const body = await res.json().catch(() => ({}));
    if (body && body.queued) return { ...body, http_status: 202 };
  }
  if (!res.ok) {
    throw new Error(`intake failed: ${res.status} ${res.statusText}`);
  }
  return await res.json();
}

/**
 * Fetch a vertical's mock fixtures directly (used by the cool-off flow,
 * which is a lookup not an intake).
 */
export async function loadMockFixture(key, vertical = 'heat') {
  return await loadMockResponse(key, vertical);
}

function synthId() {
  // Cheap RFC4122-ish v4 (good enough for a prototype demo id).
  const tpl = '10000000-1000-4000-8000-100000000000';
  return tpl.replace(/[018]/g, (c) =>
    (c ^ (crypto.getRandomValues(new Uint8Array(1))[0] & (15 >> (c / 4))))
      .toString(16)
  );
}

export function isMockMode() {
  return resolveBase() === null;
}
