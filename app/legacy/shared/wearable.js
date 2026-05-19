// shared/wearable.js
// Phase-4 wearable integration: client-side shim that talks to Apple
// HealthKit (via the WebKit message-handler bridge that an installed PWA
// gets on iOS) and Android Health Connect (via the Web Health Connect
// Origin Trial where available). Normalises everything to the
// `wearable_metric.*` shape defined in
//   schema/deep/application.sql  (wearable.heart_rate_bpm, ...)
//   schema/deep/followups.sql    (code.loinc.* nodes)
// so that downstream nodes carry a LOINC code alongside the value.
//
// Browser-bridge detection table
// ------------------------------
//   * Installed iOS PWA (Safari 17+) :  window.webkit.messageHandlers.health
//   * Android Chrome w/ Origin Trial :  navigator.health  OR  navigator.healthConnect
//   * Desktop / generic browsers     :  neither — every call resolves to a
//                                       graceful empty result + the
//                                       "web" bridge stays false. The
//                                       UI is expected to hide the
//                                       "Pair wearable" toggle in that case.
//
// Privacy stance
// --------------
// HealthKit / Health Connect are *strictly* user-consented, on-device
// data sources. This shim does the consent dance with the OS, but it
// does NOT exfiltrate raw readings; it only stages them into the
// existing IndexedDB sync queue (app/shared/sync.js), tagged with a
// `source: "wearable_auto"` property so the Intake Agent can apply
// `consent.wearable_only` suppression at the boundary.
//
// Metrics supported (LOINC):
//   8867-4  Heart rate                 (bpm)
//   8310-5  Body temperature           (degC)
//   8328-7  Skin temperature           (degC)   -- wearable-class
//   80404-7 R-R interval SDNN (HRV)    (ms)
//   41950-7 Number of steps in 24h     (steps)
//
// LOINC catalog gap notes
// -----------------------
// During this build we noted two cases where the followups.sql LOINC
// catalog did not provide a clean fit. Both are surfaced via the
// METRIC_CATALOG below with a comment + a fallback code:
//   * "Sweat rate" — schema/deep/application.sql carries a
//     wearable.sweat_rate_g_h node with loinc_code='pending'. We do
//     NOT list it in this shim's supported set; readers should not
//     ask for it until LOINC issues a canonical code.
//   * "Skin temperature" — followups.sql gives 8328-7 which is the
//     closest match (it is the modern "Skin temperature" LOINC),
//     superseding the 8310-5 + "skin-site qualifier needed" note in
//     application.sql. We use 8328-7 here.

import { enqueueReport } from './sync.js';

// ---------------------------------------------------------------------------
// Metric catalog
// ---------------------------------------------------------------------------
// Keyed by LOINC code (a stable, human-meaningful identifier we will pass
// to bridge calls and that downstream code can use directly).
export const METRIC_CATALOG = Object.freeze({
  '8867-4':  {
    loinc_code:  '8867-4',
    name:        'Heart rate',
    unit:        'bpm',
    kg_node_id:  'wearable.heart_rate_bpm',
    // Mapping to platform-native type names. The shim talks to
    // platform bridges using the platform's native string.
    healthkit:      'HKQuantityTypeIdentifierHeartRate',
    health_connect: 'HeartRate'
  },
  '8310-5':  {
    loinc_code:  '8310-5',
    name:        'Body temperature',
    unit:        'degC',
    kg_node_id:  null,             // not in application.sql; here for completeness
    healthkit:      'HKQuantityTypeIdentifierBodyTemperature',
    health_connect: 'BodyTemperature'
  },
  '8328-7':  {
    loinc_code:  '8328-7',
    name:        'Skin temperature',
    unit:        'degC',
    kg_node_id:  'wearable.skin_temp_c',
    healthkit:      'HKQuantityTypeIdentifierAppleSleepingWristTemperature',
    health_connect: 'SkinTemperature'
  },
  '80404-7': {
    loinc_code:  '80404-7',
    name:        'Heart rate variability (SDNN)',
    unit:        'ms',
    kg_node_id:  'wearable.hrv_ms',
    healthkit:      'HKQuantityTypeIdentifierHeartRateVariabilitySDNN',
    health_connect: 'HeartRateVariabilityRmssd'
  },
  '41950-7': {
    loinc_code:  '41950-7',
    name:        'Step count (24 h)',
    unit:        'steps',
    kg_node_id:  'wearable.steps_24h',
    healthkit:      'HKQuantityTypeIdentifierStepCount',
    health_connect: 'Steps'
  }
});

export const SUPPORTED_LOINC = Object.freeze(Object.keys(METRIC_CATALOG));

// ---------------------------------------------------------------------------
// Bridge detection
// ---------------------------------------------------------------------------
// Returns one of:
//   { healthkit: true,  health_connect: false, web: true }   -- iOS installed PWA
//   { healthkit: false, health_connect: true,  web: true }   -- Android OT
//   { healthkit: false, health_connect: false, web: false }  -- desktop / no bridge
//
// We intentionally do NOT throw when bridges are missing. The desktop
// path has to render every page in this app, so callers can keep using
// the same functions; they just get empty arrays / `granted: []`.
export function isWearableAvailable() {
  let healthkit = false;
  let health_connect = false;
  try {
    healthkit = !!(typeof window !== 'undefined' &&
                   window.webkit &&
                   window.webkit.messageHandlers &&
                   window.webkit.messageHandlers.health);
  } catch (_) { /* ignore */ }
  try {
    health_connect = !!(typeof navigator !== 'undefined' &&
                        (navigator.health || navigator.healthConnect));
  } catch (_) { /* ignore */ }
  return {
    healthkit,
    health_connect,
    web: healthkit || health_connect
  };
}

// ---------------------------------------------------------------------------
// Bridge messaging
// ---------------------------------------------------------------------------
// WebKit's messageHandlers.postMessage() is fire-and-forget. The native
// side replies by calling a JS function we register on window, keyed by
// a request id. We model that as a Promise that resolves when the
// reply comes back, with a 5 s timeout in case the user dismisses the
// system permission sheet.
const WK_TIMEOUT_MS = 5000;
let _wkSeq = 0;
const _wkPending = new Map();

if (typeof window !== 'undefined') {
  // The native side will call window.__wearableBridgeReply(id, payload).
  window.__wearableBridgeReply = (id, payload) => {
    const entry = _wkPending.get(id);
    if (!entry) return;
    _wkPending.delete(id);
    clearTimeout(entry.t);
    entry.resolve(payload);
  };
}

function _wkCall(method, args) {
  return new Promise((resolve, reject) => {
    const av = isWearableAvailable();
    if (!av.healthkit) {
      reject(new Error('HealthKit bridge unavailable'));
      return;
    }
    const id = ++_wkSeq;
    const t = setTimeout(() => {
      _wkPending.delete(id);
      reject(new Error(`HealthKit bridge timeout for ${method}`));
    }, WK_TIMEOUT_MS);
    _wkPending.set(id, { resolve, t });
    try {
      window.webkit.messageHandlers.health.postMessage({
        id, method, args: args || {}
      });
    } catch (e) {
      _wkPending.delete(id);
      clearTimeout(t);
      reject(e);
    }
  });
}

async function _hcCall(method, args) {
  const nav = (typeof navigator !== 'undefined') ? navigator : null;
  const ns = nav && (nav.health || nav.healthConnect);
  if (!ns) throw new Error('Health Connect bridge unavailable');
  if (typeof ns[method] !== 'function') {
    throw new Error(`Health Connect: method ${method} not implemented in this OT build`);
  }
  return await ns[method](args || {});
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Request read permission for the given LOINC-coded metrics.
 *
 * @param {string[]} metrics  LOINC codes from SUPPORTED_LOINC
 * @returns {Promise<{ granted: string[], denied: string[] }>}
 */
export async function requestPermission(metrics) {
  const av = isWearableAvailable();
  const requested = (metrics || []).filter((m) => METRIC_CATALOG[m]);
  if (!av.web) {
    // No bridge at all: every request is denied. Callers should
    // already have hidden the toggle, but be safe.
    return { granted: [], denied: requested };
  }

  // HealthKit path
  if (av.healthkit) {
    try {
      const reply = await _wkCall('requestAuthorization', {
        read: requested.map((code) => METRIC_CATALOG[code].healthkit)
      });
      // The native side echoes back the LOINC codes it ended up granting.
      // If it instead echoes platform type names, translate them back.
      const granted = new Set();
      const replyGranted = (reply && reply.granted) || [];
      for (const item of replyGranted) {
        if (METRIC_CATALOG[item]) {
          granted.add(item);
          continue;
        }
        for (const code of requested) {
          if (METRIC_CATALOG[code].healthkit === item) granted.add(code);
        }
      }
      return {
        granted: Array.from(granted),
        denied:  requested.filter((c) => !granted.has(c))
      };
    } catch (e) {
      console.warn('[wearable] HealthKit permission failed:', e.message);
      return { granted: [], denied: requested };
    }
  }

  // Health Connect path
  if (av.health_connect) {
    try {
      const reply = await _hcCall('requestPermissions', {
        read: requested.map((code) => METRIC_CATALOG[code].health_connect)
      });
      const grantedNames = (reply && reply.granted) || [];
      const granted = new Set();
      for (const item of grantedNames) {
        if (METRIC_CATALOG[item]) { granted.add(item); continue; }
        for (const code of requested) {
          if (METRIC_CATALOG[code].health_connect === item) granted.add(code);
        }
      }
      return {
        granted: Array.from(granted),
        denied:  requested.filter((c) => !granted.has(c))
      };
    } catch (e) {
      console.warn('[wearable] Health Connect permission failed:', e.message);
      return { granted: [], denied: requested };
    }
  }
  return { granted: [], denied: requested };
}

/**
 * Pull the most recent readings for one metric since a given ISO ts.
 * Always returns an array of normalised reading objects:
 *   { value, unit, recorded_at, source, loinc_code }
 *
 * On platforms without a wearable bridge this returns an empty array.
 *
 * @param {string} metric    LOINC code
 * @param {string} sinceIso  ISO-8601 timestamp lower bound (inclusive)
 * @returns {Promise<object[]>}
 */
export async function readRecent(metric, sinceIso) {
  const cat = METRIC_CATALOG[metric];
  if (!cat) throw new Error(`Unknown metric: ${metric}`);
  const av = isWearableAvailable();
  if (!av.web) return [];
  const since = sinceIso || new Date(Date.now() - 6 * 3600 * 1000).toISOString();

  let raw = [];
  try {
    if (av.healthkit) {
      const reply = await _wkCall('readQuantitySamples', {
        type: cat.healthkit, since, limit: 200
      });
      raw = (reply && reply.samples) || [];
    } else if (av.health_connect) {
      const reply = await _hcCall('readRecords', {
        type: cat.health_connect, timeRangeFilter: { startTime: since }
      });
      raw = (reply && (reply.records || reply)) || [];
    }
  } catch (e) {
    console.warn(`[wearable] readRecent(${metric}) failed:`, e.message);
    return [];
  }
  return raw.map((s) => _normalise(s, cat));
}

/**
 * Best-effort live subscription. If the platform supports server-sent
 * style push (HealthKit observer query, Health Connect change tokens),
 * use it. Otherwise poll every 60 s.
 *
 * @param {string} metric LOINC code
 * @param {(r:object)=>void} cb  Called once per delivered reading.
 * @returns {() => void} unsubscribe
 */
export function subscribe(metric, cb) {
  const cat = METRIC_CATALOG[metric];
  if (!cat) throw new Error(`Unknown metric: ${metric}`);
  if (typeof cb !== 'function') throw new Error('subscribe: cb required');
  const av = isWearableAvailable();
  if (!av.web) {
    // Nothing to subscribe to. Return a no-op unsubscribe so the
    // caller's lifecycle code keeps working on desktop.
    return () => {};
  }

  let active = true;
  let lastSeen = new Date().toISOString();

  // Try a native observer first. If the bridge advertises it, the
  // native side will push every new reading via __wearableBridgeReply.
  const observerId = ++_wkSeq;
  let observerActive = false;
  if (av.healthkit) {
    try {
      window.webkit.messageHandlers.health.postMessage({
        id: observerId, method: 'startObserverQuery',
        args: { type: cat.healthkit }
      });
      // We can't really know if the bridge will reply; assume yes but
      // keep polling as a backstop on a longer interval.
      observerActive = true;
      const handler = (ev) => {
        if (!active) return;
        if (ev && ev.detail && ev.detail.observerId === observerId) {
          for (const s of (ev.detail.samples || [])) {
            cb(_normalise(s, cat));
          }
        }
      };
      window.addEventListener('wearable:reading', handler);
      // Stash for cleanup
      _wkPending.set(`obs:${observerId}`, { resolve: () => {
        window.removeEventListener('wearable:reading', handler);
      }, t: 0 });
    } catch (_) { observerActive = false; }
  }

  const pollMs = observerActive ? 120000 : 60000;
  const tick = async () => {
    if (!active) return;
    try {
      const items = await readRecent(metric, lastSeen);
      if (items.length) {
        lastSeen = items[items.length - 1].recorded_at;
        for (const r of items) cb(r);
      }
    } catch (_) { /* swallow; UI keeps running */ }
  };
  const iv = setInterval(tick, pollMs);
  // Kick once on subscribe so the chart has data immediately.
  tick();

  return () => {
    active = false;
    clearInterval(iv);
    if (observerActive) {
      try {
        window.webkit.messageHandlers.health.postMessage({
          id: observerId, method: 'stopObserverQuery',
          args: { type: cat.healthkit }
        });
      } catch (_) {}
      const cleanup = _wkPending.get(`obs:${observerId}`);
      if (cleanup) { cleanup.resolve(); _wkPending.delete(`obs:${observerId}`); }
    }
  };
}

/**
 * Push a normalised reading into the IndexedDB sync queue so it replays
 * on reconnect alongside the regular intake flow. The reading is
 * wrapped as a `wearable_reading` flow payload — the server can route
 * these into the Intake Agent with `source: "wearable_auto"`.
 *
 * @param {object} reading  { value, unit, recorded_at, source, loinc_code }
 * @returns {Promise<string>} the enqueued report id
 */
export async function storeForSync(reading) {
  if (!reading || typeof reading.value !== 'number' || !reading.loinc_code) {
    throw new Error('storeForSync: reading must have value + loinc_code');
  }
  const cat = METRIC_CATALOG[reading.loinc_code];
  return await enqueueReport({
    flow:     'wearable_reading',
    vertical: 'heat',
    payload: {
      flow:            'wearable_reading',
      vertical:        'heat',
      consent_profile: 'consent.wearable_only',
      source:          'wearable_auto',
      wearable: {
        loinc_code:  reading.loinc_code,
        kg_node_id:  cat ? cat.kg_node_id : null,
        value:       reading.value,
        unit:        reading.unit || (cat && cat.unit) || null,
        recorded_at: reading.recorded_at || new Date().toISOString(),
        source:      reading.source || 'wearable'
      }
    }
  });
}

// ---------------------------------------------------------------------------
// Internals
// ---------------------------------------------------------------------------
function _normalise(sample, cat) {
  // Accept both HealthKit-style (HKQuantitySample-ish JSON) and
  // Health-Connect-style records, plus a generic { value, unit, time }
  // shape that mock harnesses may emit.
  let value = null;
  let unit  = cat.unit;
  let when  = null;
  let src   = cat.healthkit ? 'healthkit' : 'health_connect';

  if (sample == null) return null;

  if (typeof sample.value === 'number') {
    value = sample.value;
  } else if (sample.quantity && typeof sample.quantity.doubleValue === 'number') {
    value = sample.quantity.doubleValue;
    unit  = sample.quantity.unit || unit;
  } else if (typeof sample.beatsPerMinute === 'number') {
    value = sample.beatsPerMinute;
  } else if (typeof sample.count === 'number') {
    value = sample.count;
  } else if (sample.temperature && typeof sample.temperature.inCelsius === 'number') {
    value = sample.temperature.inCelsius;
    unit  = 'degC';
  }

  when = sample.recorded_at
      || sample.endDate
      || sample.endTime
      || sample.time
      || new Date().toISOString();

  if (sample.source) src = String(sample.source);

  // Common unit normalisation: HealthKit returns "count/min" for HR,
  // "degC" or "degF" for temperature. Convert F to C so downstream
  // schema (degC) is consistent.
  if (cat.loinc_code === '8867-4') unit = 'bpm';
  if ((cat.loinc_code === '8328-7' || cat.loinc_code === '8310-5') && unit === 'degF') {
    value = ((+value) - 32) * 5 / 9;
    unit  = 'degC';
  }

  return {
    value:       Number(value),
    unit,
    recorded_at: when,
    source:      src,
    loinc_code:  cat.loinc_code
  };
}

// Re-export for tests + UI badges.
export const WEARABLE_CONSTANTS = Object.freeze({
  SUPPORTED_LOINC,
  WK_TIMEOUT_MS
});
