// today/shared/feeds.js
// Tiny fetch wrappers used by the AZ One Health Today page. Each function
// returns a JSON object shaped exactly like the corresponding MCP tool
// (or a thin aggregation of two-three tools). In mock mode (the default)
// each function resolves the matching file under today/mock/. To wire to
// a real backend, set <body data-feeds-base="https://example.org"> and
// each function will hit `${base}/today/<key>` instead.
//
// All five feeds are independent so the panels render incrementally; a
// failure in one feed never blocks the others.

const MOCK_URLS = {
  heatrisk:        new URL('../mock/heatrisk.json',        import.meta.url).href,
  wnv:             new URL('../mock/wnv-positivity.json',  import.meta.url).href,
  wildlife:        new URL('../mock/wildlife-signals.json',import.meta.url).href,
  cooling_centers: new URL('../mock/cooling-centers.json', import.meta.url).href,
  rollup:          new URL('../mock/statewide-rollup.json',import.meta.url).href,
};

const REAL_PATHS = {
  heatrisk:        '/today/heatrisk',
  wnv:             '/today/wnv-positivity',
  wildlife:        '/today/wildlife-signals',
  cooling_centers: '/today/cooling-centers',
  rollup:          '/today/statewide-rollup',
};

function resolveBase() {
  const attr = document.body && document.body.getAttribute('data-feeds-base');
  if (!attr || attr === 'mock') return null;
  return attr.replace(/\/+$/, '');
}

export function isMockMode() {
  return resolveBase() === null;
}

async function loadFeed(key, { signal } = {}) {
  const base = resolveBase();
  const url  = base ? `${base}${REAL_PATHS[key]}` : MOCK_URLS[key];
  if (!url) throw new Error(`unknown feed: ${key}`);
  const res = await fetch(url, { cache: 'no-store', signal });
  if (!res.ok) throw new Error(`${key}: ${res.status} ${res.statusText}`);
  return await res.json();
}

export const fetchHeatRisk        = (opts) => loadFeed('heatrisk', opts);
export const fetchWnvPositivity   = (opts) => loadFeed('wnv', opts);
export const fetchWildlifeSignals = (opts) => loadFeed('wildlife', opts);
export const fetchCoolingCenters  = (opts) => loadFeed('cooling_centers', opts);
export const fetchStatewideRollup = (opts) => loadFeed('rollup', opts);

/**
 * Best-effort number formatter that respects locale (so Spanish renders
 * "1.234" instead of "1,234"). Falls back to plain toString in old browsers.
 */
export function fmtNumber(n, lang = 'en') {
  try { return new Intl.NumberFormat(lang === 'es' ? 'es-MX' : 'en-US').format(n); }
  catch (_) { return String(n); }
}

/**
 * Human "as-of" timestamp. Inputs in ISO; output respects the page lang.
 */
export function fmtAsOf(iso, lang = 'en') {
  try {
    const d = new Date(iso);
    const opts = { year: 'numeric', month: 'short', day: 'numeric',
                   hour: 'numeric', minute: '2-digit', timeZoneName: 'short' };
    return new Intl.DateTimeFormat(lang === 'es' ? 'es-MX' : 'en-US', opts).format(d);
  } catch (_) {
    return iso;
  }
}
