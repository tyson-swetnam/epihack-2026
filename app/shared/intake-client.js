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

const MOCK_URL = new URL('../mock-responses.json', import.meta.url).href;

function resolveBase() {
  const attr = document.body && document.body.getAttribute('data-api-base');
  if (!attr || attr === 'mock') return null;
  return attr.replace(/\/+$/, '');
}

async function loadMockResponse(flow) {
  const res = await fetch(MOCK_URL, { cache: 'no-store' });
  if (!res.ok) throw new Error('mock-responses.json missing');
  const all = await res.json();
  const r = all[flow];
  if (!r) throw new Error(`mock response for flow=${flow} not found`);
  return r;
}

// Simulated latency so the spinner is actually visible during the demo.
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * Post an intake payload.
 *
 * @param {string} flow   e.g. 'tick_mailin'
 * @param {object} payload Minimum-Dataset shaped object
 * @param {object} opts   { signal?: AbortSignal, photoBlob?: Blob|File }
 * @returns {Promise<object>} the IntakeAgent → … → NotificationAgent result
 */
export async function submitIntake(flow, payload, opts = {}) {
  const base = resolveBase();

  if (base === null) {
    // Mock mode: simulate 1.4 s of agent chain latency so the spinner
    // is visible, then merge the canned response with a synthesized id.
    await sleep(1400);
    const canned = await loadMockResponse(flow);
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
  form.append('payload', new Blob([JSON.stringify(payload)],
                                  { type: 'application/json' }));
  if (opts.photoBlob) form.append('photo', opts.photoBlob, 'tick.jpg');

  const res = await fetch(`${base}/api/intake`, {
    method: 'POST',
    body: form,
    signal: opts.signal
  });
  if (!res.ok) {
    throw new Error(`intake failed: ${res.status} ${res.statusText}`);
  }
  return await res.json();
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
