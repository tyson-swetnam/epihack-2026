// wearable-monitor.js
// Phase-4 continuous heat-stress monitor. One-button screen that
// streams heart rate (LOINC 8867-4) and skin temperature (LOINC
// 8328-7) from the user's paired wearable, recomputes a simplified
// heat-vulnerability score on every reading, and auto-files a Heat
// self-report via app/shared/intake-client.js if the score crosses
// the tc.go_to_cooling_center threshold.
//
// Threshold logic
// ---------------
// Mirrors plan/03-agentic-architecture.md, where 6-9 points maps to
// `tc.go_to_cooling_center`. We fire when the live composite score is
// >= 6 for at least 2 consecutive readings (debounced).

import { bootstrapOfflineUi } from '../../shared/sw-register.js';
import { submitIntake, isMockMode } from '../../shared/intake-client.js';
import { enqueueReport } from '../../shared/sync.js';
import {
  isWearableAvailable, requestPermission, subscribe, storeForSync
} from '../../shared/wearable.js';

bootstrapOfflineUi();

const COOLING_CENTER_THRESHOLD = 6;   // points; matches tc.go_to_cooling_center
const DEBOUNCE_READINGS         = 2;  // need N consecutive overs before firing

const state = {
  active:        false,
  unsubscribers: [],
  hr:            [],   // [{t, v}] sparkline buffers
  skin:          [],
  alerts:        [],
  fired:         false,
  overCount:     0,
  contributingLoincs: new Set()
};

const $ = (id) => document.getElementById(id);

document.addEventListener('DOMContentLoaded', init);

function init() {
  const av = isWearableAvailable();
  if (!av.web) {
    $('no-bridge').hidden = false;
    $('start-btn').disabled = true;
    $('start-btn').textContent = 'Wearable bridge unavailable';
    return;
  }
  $('start-btn').addEventListener('click', start);
  $('stop-btn').addEventListener('click', stop);
}

async function start() {
  if (state.active) return;
  $('start-btn').disabled = true;
  $('start-btn').textContent = 'Asking for permission...';

  const perm = await requestPermission(['8867-4', '8328-7']);
  if (perm.granted.length === 0) {
    $('start-btn').disabled = false;
    $('start-btn').textContent = 'Start monitoring';
    logAlert('Permission denied. Monitoring not started.');
    return;
  }
  state.contributingLoincs = new Set(perm.granted);
  state.active = true;
  $('start-btn').hidden = true;
  $('stop-btn').hidden  = false;

  if (perm.granted.includes('8867-4')) {
    const u = subscribe('8867-4', (r) => onReading('hr', r));
    state.unsubscribers.push(u);
  }
  if (perm.granted.includes('8328-7')) {
    const u = subscribe('8328-7', (r) => onReading('skin', r));
    state.unsubscribers.push(u);
  }
  logAlert(`Monitoring started: ${Array.from(state.contributingLoincs).join(', ')}.`);
}

function stop() {
  state.unsubscribers.forEach((fn) => { try { fn(); } catch (_) {} });
  state.unsubscribers = [];
  state.active = false;
  $('start-btn').hidden = false;
  $('stop-btn').hidden  = true;
  $('start-btn').disabled = false;
  $('start-btn').textContent = 'Start monitoring';
  logAlert('Monitoring stopped.');
}

function onReading(kind, r) {
  if (!r || typeof r.value !== 'number') return;
  const buf = state[kind];
  buf.push({ t: Date.parse(r.recorded_at) || Date.now(), v: r.value });
  // Keep the last 60 readings (~ 1 min at 1Hz or longer windows otherwise).
  while (buf.length > 60) buf.shift();

  if (kind === 'hr') {
    $('hr-val').textContent = Math.round(r.value);
    $('hr-ts').textContent  = formatTime(r.recorded_at);
    drawSparkline($('hr-chart'), state.hr, 40, 180);
  } else if (kind === 'skin') {
    $('temp-val').textContent = r.value.toFixed(1);
    $('temp-ts').textContent  = formatTime(r.recorded_at);
    drawSparkline($('temp-chart'), state.skin, 30, 40);
  }

  // Best-effort: stage every reading for sync so the on-device store
  // (which the wearable MCP serves) stays fresh even if we don't fire.
  storeForSync(r).catch(() => {});

  recomputeScore();
}

function recomputeScore() {
  const hr   = latest(state.hr);
  const skin = latest(state.skin);
  let score = 0;
  const components = [];

  if (hr != null && hr.v >= 130) {
    score += 3;
    components.push({ factor: 'tachycardia', label: `Heart rate ${Math.round(hr.v)} bpm`, points: 3 });
  } else if (hr != null && hr.v >= 110) {
    score += 2;
    components.push({ factor: 'elevated_hr', label: `Heart rate ${Math.round(hr.v)} bpm`, points: 2 });
  }
  if (skin != null && skin.v >= 38.5) {
    score += 3;
    components.push({ factor: 'skin_temp_high', label: `Skin temp ${skin.v.toFixed(1)} °C`, points: 3 });
  } else if (skin != null && skin.v >= 37.5) {
    score += 2;
    components.push({ factor: 'skin_temp_elevated', label: `Skin temp ${skin.v.toFixed(1)} °C`, points: 2 });
  }

  $('score-val').textContent = String(score);
  $('score-detail').textContent = components.length
    ? components.map((c) => c.label).join(' + ')
    : 'within resting range';

  if (score >= COOLING_CENTER_THRESHOLD) {
    state.overCount += 1;
  } else {
    state.overCount = 0;
  }

  if (!state.fired && state.overCount >= DEBOUNCE_READINGS) {
    state.fired = true;
    fileAutoReport(score, components);
  }
}

async function fileAutoReport(score, components) {
  $('threshold-host').innerHTML = `
    <div class="threshold-banner" role="alert">
      Vulnerability score ${score}/15 — auto-filing a Heat self-report.
      Cooling-center routing should appear shortly.
    </div>`;
  logAlert(`Threshold crossed (score=${score}). Auto-report dispatched.`);

  const payload = {
    flow:            'heat_self_report',
    vertical:        'heat',
    channel:         'wearable',
    consent_profile: 'consent.wearable_only',
    source:          'wearable_auto',
    wearable: {
      loinc_codes:    Array.from(state.contributingLoincs),
      heart_rate_bpm: latest(state.hr)?.v ?? null,
      skin_temp_c:    latest(state.skin)?.v ?? null,
      auto_score:     score,
      components
    },
    general: {
      reported_at:     new Date().toISOString(),
      time_of_checkin: nowHHMM()
    },
    human:    {},
    exposure: {},
    environmental: {}
  };

  try {
    if (typeof navigator !== 'undefined' && navigator.onLine === false) {
      await enqueueReport({
        flow: 'heat_self_report', vertical: 'heat',
        mock_key: 'heat_self_report', payload
      });
      logAlert('Offline — queued for sync.');
      return;
    }
    const res = await submitIntake('heat_self_report', payload, {
      vertical: 'heat',
      mockKey:  'heat_chw_checkin'   // demo: show the full cooling-center card
    });
    const tc = res && res.triage_class || 'tc.go_to_cooling_center';
    const centers = (res && res.cooling_centers && res.cooling_centers.centers) || [];
    const phone   = (res && res.transport_offer && res.transport_offer.phone) || '+1-877-211-8661';
    $('threshold-host').innerHTML += `
      <div class="monitor-card">
        <h3>${escapeHtml(tc)}</h3>
        ${centers[0] ? `<div>${escapeHtml(centers[0].name)} &middot; ${centers[0].distance_km} km</div>` : ''}
        <a class="btn heat" style="display:inline-block;margin-top:.5rem" href="tel:${escapeHtml(phone.replace(/[^+0-9]/g,''))}">Call 211</a>
        <a class="btn danger" style="display:inline-block;margin-top:.5rem" href="tel:911">Call 911</a>
      </div>`;
  } catch (e) {
    logAlert(`Auto-report failed: ${e.message}. Queued instead.`);
    try {
      await enqueueReport({
        flow: 'heat_self_report', vertical: 'heat',
        mock_key: 'heat_self_report', payload
      });
    } catch (_) {}
  }
}

// ---------------------------------------------------------------------------
// Tiny sparkline (no charting library, no build step).
// ---------------------------------------------------------------------------
function drawSparkline(host, points, lo, hi) {
  if (!host) return;
  const w = host.clientWidth || 320;
  const h = host.clientHeight || 120;
  if (points.length < 2) {
    host.innerHTML = '';
    return;
  }
  const ts0 = points[0].t;
  const tsN = points[points.length - 1].t;
  const tspan = Math.max(1, tsN - ts0);
  const yMin = Math.min(lo, Math.min(...points.map((p) => p.v)) - 1);
  const yMax = Math.max(hi, Math.max(...points.map((p) => p.v)) + 1);
  const yspan = Math.max(1, yMax - yMin);
  const d = points.map((p, i) => {
    const x = ((p.t - ts0) / tspan) * (w - 4) + 2;
    const y = h - ((p.v - yMin) / yspan) * (h - 6) - 3;
    return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(' ');
  host.innerHTML =
    `<svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">` +
      `<path d="${d}" stroke="#E84A2B" stroke-width="2" fill="none" stroke-linejoin="round" stroke-linecap="round" />` +
    `</svg>`;
}

function latest(buf) { return buf.length ? buf[buf.length - 1] : null; }
function nowHHMM() {
  const n = new Date();
  return `${String(n.getHours()).padStart(2,'0')}:${String(n.getMinutes()).padStart(2,'0')}`;
}
function formatTime(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString();
  } catch (_) { return ''; }
}
function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}
function logAlert(text) {
  state.alerts.push({ at: new Date().toISOString(), text });
  const log = $('alert-log');
  if (!log) return;
  const li = document.createElement('li');
  li.textContent = `${new Date().toLocaleTimeString()} — ${text}`;
  log.appendChild(li);
}

if (isMockMode()) {
  console.info('[wearable-monitor] running in mock mode — see app/heat/mock-responses.json');
}
