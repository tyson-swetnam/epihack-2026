// check-in.js
// CHW-mediated unsheltered heat check-in. Mirrors Scenario C in
// plan/04-data-flows.md. Six steps; submits a Minimum-Dataset shaped
// payload through app/shared/intake-client.js (mock or real).

import { requestLocation, isPlausibleZip } from '../../shared/geo.js';
import { submitIntake, isMockMode }       from '../../shared/intake-client.js';
import { t, mountSwitcher, onLangChange } from '../../shared/i18n.js';
import { enqueueReport }                  from '../../shared/sync.js';
import { bootstrapOfflineUi }             from '../../shared/sw-register.js';
import {
  $, $$, escapeHtml,
  attachConfirm, renderThermometer, renderCenterCard,
  rankCenters, triageLabel
} from '../heat-shared.js';

// Register the service worker + mount the sync-status pill in the header.
bootstrapOfflineUi();

// ---------------------------------------------------------------------------
// Step orchestration
// ---------------------------------------------------------------------------
const STEPS = [
  { id: 'subject',  name: 'Identify'  },
  { id: 'where',    name: 'Where'     },
  { id: 'symptoms', name: 'Symptoms'  },
  { id: 'exposure', name: 'Exposure'  },
  { id: 'consent',  name: 'Consent'   },
  { id: 'submit',   name: 'Submit'    }
];

const state = {
  step: 0,
  // Identify
  age_range:     '40_64',
  sex:           'M',
  unsheltered:   true,
  with_pet:      false,
  // Where + when
  geo:           null,
  zip:           '',
  checkin_time:  '',
  // Symptoms
  symptoms:      [],
  core_temp_f:   null,
  // Exposure
  outdoor_hours: 6,
  ac_access:     false,
  last_water:    '1_3h',
  thermo_meds:   false,
  transport:     false,
  // Consent
  consent:       false
};

document.addEventListener('DOMContentLoaded', init);

function init() {
  $('progress').hidden  = false;
  $('sticky-bar').hidden = false;

  // Drop a language switcher into the header so CHWs working with
  // Spanish-speaking subjects can flip without remembering a URL.
  mountSwitcher(document.querySelector('.heat-header'));
  // When the language flips mid-flow, re-render the live bits.
  onLangChange(() => {
    renderStep();
    if (state.step === STEPS.length - 1 && !$('submit-pre').hidden) {
      renderSubmitSummary();
    }
  });

  wireSubject();
  wireWhere();
  wireSymptoms();
  wireExposure();
  wireConsent();
  wireNavigation();

  // Default time-of-checkin = now.
  const now = new Date();
  const hh = String(now.getHours()).padStart(2, '0');
  const mm = String(now.getMinutes()).padStart(2, '0');
  $('time-of-checkin').value = `${hh}:${mm}`;
  state.checkin_time = `${hh}:${mm}`;

  renderStep();
}

function renderStep() {
  const stepDef = STEPS[state.step];
  $$('.step').forEach((el) => {
    const isActive = el.dataset.step === stepDef.id;
    el.classList.toggle('active', isActive);
    el.hidden = !isActive;
  });

  $('step-name').textContent  = stepDef.name;
  $('step-count').textContent = `Step ${state.step + 1} of ${STEPS.length}`;
  $('progress-fill').style.width =
    `${((state.step + 1) / STEPS.length) * 100}%`;

  const backBtn = $('back-btn');
  const nextBtn = $('next-btn');
  backBtn.disabled = state.step === 0;
  backBtn.style.visibility = state.step === 0 ? 'hidden' : 'visible';

  if (stepDef.id === 'submit') {
    nextBtn.textContent = t('nav.submit');
    nextBtn.classList.remove('magenta');
    nextBtn.classList.add('success');
    renderSubmitSummary();
  } else {
    nextBtn.textContent =
      state.step === STEPS.length - 2 ? t('nav.review') : t('nav.next');
    nextBtn.classList.remove('success');
    nextBtn.classList.add('magenta');
  }

  if (state.step !== 0) {
    const h = document.querySelector('.step.active h2');
    if (h) { h.setAttribute('tabindex', '-1'); h.focus({ preventScroll: false }); }
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function wireNavigation() {
  $('next-btn').addEventListener('click', onNext);
  $('back-btn').addEventListener('click', () => {
    if (state.step > 0) { state.step -= 1; renderStep(); }
  });
}

function onNext() {
  const err = validateStep(STEPS[state.step].id);
  if (err) { alert(err); return; }
  if (STEPS[state.step].id === 'submit') { doSubmit(); return; }
  state.step += 1;
  renderStep();
}

function validateStep(id) {
  switch (id) {
    case 'where':
      if (!state.geo && !isPlausibleZip(state.zip)) {
        return 'Tap "Use my location" or enter a 5-digit ZIP.';
      }
      if (!state.checkin_time) return 'Pick a time of check-in.';
      return null;
    case 'consent':
      if (!state.consent) return 'Consent acceptance is required for this flow.';
      return null;
    default:
      return null;
  }
}

// ---------------------------------------------------------------------------
// Step 1 — Identify
// ---------------------------------------------------------------------------
function wireSubject() {
  document.querySelectorAll('input[name="age_range"]').forEach((el) => {
    el.addEventListener('change', (e) => { state.age_range = e.target.value; });
  });
  document.querySelectorAll('input[name="sex"]').forEach((el) => {
    el.addEventListener('change', (e) => { state.sex = e.target.value; });
  });
  $('unsheltered').addEventListener('change', (e) => { state.unsheltered = e.target.checked; });
  $('with-pet').addEventListener('change',    (e) => { state.with_pet    = e.target.checked; });
}

// ---------------------------------------------------------------------------
// Step 2 — Where + when (GPS via shared/geo.js, ZIP fallback)
// ---------------------------------------------------------------------------
function wireWhere() {
  const btn    = $('geo-btn');
  const status = $('geo-status');
  const text   = $('geo-status-text');

  btn.addEventListener('click', async () => {
    btn.disabled = true;
    status.classList.remove('ok', 'warn');
    text.textContent = t('geo.asking');

    const loc = await requestLocation();
    btn.disabled = false;

    if (loc.source === 'gps') {
      state.geo = loc;
      status.classList.add('ok');
      text.textContent =
        `${t('geo.got')}: ${loc.lat.toFixed(4)}, ${loc.lon.toFixed(4)} ` +
        `(±${Math.round(loc.accuracy)} m)`;
    } else if (loc.source === 'unsupported') {
      state.geo = null;
      status.classList.add('warn');
      text.textContent = t('geo.unsupported');
    } else {
      state.geo = null;
      status.classList.add('warn');
      text.textContent = t('geo.denied');
    }
  });

  $('zip').addEventListener('input',  (e) => { state.zip = e.target.value.trim(); });
  $('time-of-checkin').addEventListener('change', (e) => {
    state.checkin_time = e.target.value;
  });
}

// ---------------------------------------------------------------------------
// Step 3 — Symptoms
// ---------------------------------------------------------------------------
function wireSymptoms() {
  $('symptoms-grid').addEventListener('change', (e) => {
    // "none of the above" is exclusive with any other symptom.
    const target = e.target;
    if (target.value === 'none' && target.checked) {
      $$('#symptoms-grid input').forEach((el) => {
        if (el.value !== 'none') el.checked = false;
      });
    } else if (target.value !== 'none' && target.checked) {
      const none = document.querySelector('#symptoms-grid input[value="none"]');
      if (none) none.checked = false;
    }
    state.symptoms = $$('#symptoms-grid input:checked')
      .map((el) => el.value)
      .filter((v) => v !== 'none');
  });

  $('core-temp').addEventListener('input', (e) => {
    const v = parseFloat(e.target.value);
    state.core_temp_f = Number.isFinite(v) ? v : null;
  });
}

// ---------------------------------------------------------------------------
// Step 4 — Exposure
// ---------------------------------------------------------------------------
function wireExposure() {
  const slider = $('outdoor-hours');
  const value  = $('outdoor-hours-value');
  const renderSlider = () => {
    state.outdoor_hours = parseInt(slider.value, 10);
    value.textContent = t('heat.exposure.outdoor.value', { n: state.outdoor_hours });
  };
  slider.addEventListener('input', renderSlider);
  renderSlider();

  $('ac-access').addEventListener('change',       (e) => { state.ac_access      = e.target.checked; });
  $('thermo-meds').addEventListener('change',     (e) => { state.thermo_meds    = e.target.checked; });
  $('transport-access').addEventListener('change',(e) => { state.transport      = e.target.checked; });
  document.querySelectorAll('input[name="last-water"]').forEach((el) => {
    el.addEventListener('change', (e) => { state.last_water = e.target.value; });
  });
}

// ---------------------------------------------------------------------------
// Step 5 — Consent
// ---------------------------------------------------------------------------
function wireConsent() {
  $('consent-ok').addEventListener('change', (e) => { state.consent = e.target.checked; });
}

// ---------------------------------------------------------------------------
// Step 6 — Submit
// ---------------------------------------------------------------------------
function renderSubmitSummary() {
  const lines = [];
  lines.push(`Subject: age ${labelAge(state.age_range)}, sex ${state.sex}, ` +
             `${state.unsheltered ? 'unsheltered' : 'sheltered'}` +
             (state.with_pet ? ', with pet' : ''));
  if (state.geo) lines.push(`Location: GPS ${state.geo.lat.toFixed(3)}, ${state.geo.lon.toFixed(3)}`);
  else if (state.zip) lines.push(`Location: ZIP ${state.zip}`);
  lines.push(`Time: ${state.checkin_time}`);
  lines.push(`Symptoms: ${state.symptoms.length ? state.symptoms.join(', ') : 'none'}`);
  if (state.core_temp_f != null) lines.push(`Core temp: ${state.core_temp_f} °F`);
  lines.push(`Outdoor: ${state.outdoor_hours} h · AC: ${state.ac_access ? 'yes' : 'no'} · ` +
             `water: ${state.last_water} · meds: ${state.thermo_meds ? 'yes' : 'no'} · ` +
             `transport: ${state.transport ? 'yes' : 'no'}`);
  $('summary-body').innerHTML = lines.map((l) =>
    `<div>${escapeHtml(l)}</div>`).join('');
}

const AGE_LABELS = {
  under_18: 'under 18', '18_39': '18-39', '40_64': '40-64', '65_plus': '65+'
};
const labelAge = (a) => AGE_LABELS[a] || a;

// Map the in-state form -> Minimum Dataset shape, then submit.
function buildPayload() {
  // Translate the form to the agents contracts shape (see
  // agents/src/onehealth_agents/contracts.py).
  return {
    flow: 'heat_chw_checkin',
    vertical: 'heat',
    channel: 'chw_tablet',
    consent_profile: 'consent.anonymous_heat',
    general: {
      reported_at: new Date().toISOString(),
      age_range:   state.age_range,
      sex:         state.sex,
      lat:         state.geo ? state.geo.lat : null,
      lon:         state.geo ? state.geo.lon : null,
      gps_accuracy_m: state.geo ? state.geo.accuracy : null,
      postal_code: state.zip || null,
      time_of_checkin: state.checkin_time
    },
    human: {
      confusion:      state.symptoms.includes('confusion'),
      hot_dry_skin:   state.symptoms.includes('hot_dry_skin'),
      heavy_sweating: state.symptoms.includes('heavy_sweating'),
      headache:       state.symptoms.includes('headache'),
      dizziness:      state.symptoms.includes('dizziness'),
      muscle_cramps:  state.symptoms.includes('muscle_cramps'),
      core_temp_f:    state.core_temp_f
    },
    exposure: {
      sheltered_status:        state.unsheltered ? 'unsheltered' : 'sheltered',
      with_pet:                state.with_pet,
      outdoor_time_24h_hours:  state.outdoor_hours,
      ac_access:               state.ac_access ? 'yes' : 'no',
      last_water_bucket:       state.last_water,
      thermo_meds:             state.thermo_meds,
      transport_access:        state.transport ? 'self' : 'none'
    },
    environmental: { /* filled by EnrichmentAgent via nws-heatrisk-mcp */ }
  };
}

// Pick which canned response to use in mock mode. The real backend ignores
// this hint; in mock mode it lets the same form exercise every triage class.
function pickMockKey() {
  if (state.symptoms.includes('hot_dry_skin') ||
      state.symptoms.includes('confusion') ||
      (state.core_temp_f != null && state.core_temp_f >= 104)) {
    return 'heat_chw_checkin_911';
  }
  // Default = the Scenario C "go-to-cooling-center" canned response.
  if (state.unsheltered && state.symptoms.length > 0) return 'heat_chw_checkin';
  // Minimal symptoms + sheltered + AC = check-in-only.
  if (!state.unsheltered && state.ac_access && state.symptoms.length === 0) {
    return 'heat_check_in_only';
  }
  return 'heat_chw_checkin';
}

async function doSubmit() {
  const pre    = $('submit-pre');
  const pend   = $('submit-pending');
  const result = $('submit-result');
  const error  = $('submit-error');
  const stick  = $('sticky-bar');

  pre.hidden    = true;
  pend.hidden   = false;
  result.hidden = true;
  error.hidden  = true;
  stick.hidden  = true;

  const agentLines = document.querySelectorAll('#agent-log .line');
  const totalDelay = 1400;
  agentLines.forEach((el, i) => {
    setTimeout(() => {
      el.classList.remove('pending');
      el.classList.add('done');
    }, (totalDelay / agentLines.length) * (i + 1));
  });

  try {
    const payload = buildPayload();
    const mockKey = pickMockKey();

    if (typeof navigator !== 'undefined' && navigator.onLine === false) {
      await enqueueReport({
        flow: 'heat_chw_checkin', vertical: 'heat', mock_key: mockKey, payload
      });
      pend.hidden = true;
      renderQueuedResult();
      return;
    }

    const res = await submitIntake('heat_chw_checkin', payload, {
      vertical: 'heat',
      mockKey
    });
    if (res && res.queued) {
      await enqueueReport({
        flow: 'heat_chw_checkin', vertical: 'heat', mock_key: mockKey, payload
      });
      pend.hidden = true;
      renderQueuedResult();
      return;
    }
    pend.hidden = true;
    renderResult(res);
  } catch (e) {
    try {
      await enqueueReport({
        flow: 'heat_chw_checkin', vertical: 'heat',
        mock_key: pickMockKey(), payload: buildPayload()
      });
      pend.hidden = true;
      renderQueuedResult();
      return;
    } catch (_) { /* fall through */ }
    pend.hidden = true;
    pre.hidden  = false;
    stick.hidden = false;
    error.hidden = false;
    error.textContent =
      `Submit failed: ${e.message}. Try again, or come back later.`;
  }
}

function renderQueuedResult() {
  const el = $('submit-result');
  el.hidden = false;
  el.innerHTML = `
    <div class="result-card" role="status" aria-live="polite"
         style="border-left:6px solid #FFB300;background:#fff8e6">
      <h3>Saved offline.</h3>
      <p>You're offline (or the server isn't reachable). This check-in is
         safely stored on this device and will upload automatically when
         a network is available. Cooling-center routing and 211 dispatch
         resume once the report reaches the Triage Agent.</p>
      <p class="muted small">
        If this is a <strong>911</strong> case, do not wait for sync &mdash;
        call now. Offline mode does not interfere with the phone's
        emergency dialer.
      </p>
    </div>
    <div class="cta-grid">
      <a class="btn danger block" href="tel:911"
         aria-label="Call 911 now">Call 911</a>
      <a class="btn ghost" href="../../index.html">${escapeHtml(t('nav.home'))}</a>
    </div>
  `;
}

function renderResult(res) {
  const el = $('submit-result');
  el.hidden = false;

  const tc = res.triage_class || 'tc.check_in_only';
  const tcSlug = tc.replace(/^tc\./, '');
  const centers = rankCenters((res.cooling_centers && res.cooling_centers.centers) || []);
  const nearest = centers[0];

  const cardClass = `result-card tc-${tcSlug}`;

  el.innerHTML = `
    <div class="${cardClass}" role="status" aria-live="polite">
      <h3>${escapeHtml(triageLabel(tc))}</h3>
      <p class="muted small" style="margin:.25rem 0 0">
        ${escapeHtml(res.rationale || '')}
      </p>
      <div id="thermo-host"></div>
    </div>

    ${nearest ? `
    <div class="section-block">
      <h3>${escapeHtml(t('heat.submit.nearest'))}</h3>
      <ul class="center-list">${renderCenterCard(nearest)}</ul>
    </div>` : ''}

    ${res.transport_offer && res.transport_offer.available && tc !== 'tc.call_911' ? `
    <div class="section-block">
      <h3>211 Arizona</h3>
      <p class="muted small">
        Provider: <strong>${escapeHtml(res.transport_offer.provider || '—')}</strong>
        ${res.transport_offer.eta_minutes != null
          ? ` &middot; ETA ~${res.transport_offer.eta_minutes} min` : ''}
      </p>
      <button type="button" class="btn heat block confirm-btn" id="dispatch-btn">
        ${escapeHtml(t('heat.submit.request_transport'))}
      </button>
      <p class="muted small" style="margin-top:.4rem">
        ${escapeHtml(res.transport_offer.note || '')}
      </p>
    </div>` : ''}

    ${tc === 'tc.call_911' ? `
    <div class="section-block" style="border-color:var(--c-red)">
      <h3 style="color:#7a1a12">911</h3>
      <a class="btn danger block" href="tel:911" aria-label="Call 911 now">
        ${escapeHtml(t('tc.call_911'))}
      </a>
    </div>` : ''}

    <div class="section-block">
      <h3>kg writeback</h3>
      <p class="muted small">
        ${(res.milestones || []).map((m) =>
          `<span class="badge heat">${escapeHtml(m.milestone)}</span>`).join(' ')}
      </p>
      <ul class="muted small">
        ${(res.edges_written || []).map((e) =>
          `<li><code>${escapeHtml(e)}</code></li>`).join('') || '<li>(none)</li>'}
      </ul>
      <p class="muted small">${escapeHtml(t('heat.submit.cluster_note'))}</p>
    </div>

    <div class="section-block">
      <h3>See how this fits</h3>
      <div class="cta-grid">
        <a class="btn secondary" href="../../../map/index.html">Arizona map</a>
        <a class="btn secondary" href="../../../graph/index.html">Pathogen graph</a>
        <a class="btn secondary" href="../../../heat/index.html">Heat focus-group docs</a>
        <a class="btn ghost"     href="../../index.html">${escapeHtml(t('nav.home'))}</a>
      </div>
      <p class="receipt" style="margin-top:.6rem">
        Observation: <code>${escapeHtml(res.observation_id || '—')}</code>
        ${res.mock ? '&middot; <span class="muted">(mock response)</span>' : ''}
      </p>
    </div>
  `;

  // Render the thermometer into its placeholder slot.
  renderThermometer(el.querySelector('#thermo-host'),
    res.heat_vulnerability || { total: 0, max_possible: 15, components: [] });

  // Attach the two-tap confirm guard to the dispatch button if present.
  const dispatchBtn = el.querySelector('#dispatch-btn');
  if (dispatchBtn) {
    attachConfirm(dispatchBtn, {
      armedLabel:      t('heat.submit.confirm'),
      dispatchedLabel: t('heat.submit.dispatched'),
      onConfirm: () => {
        // In real mode, fire-and-forget a POST to /api/transport.
        // In mock mode, just log.
        if (isMockMode()) {
          console.info('[heat-checkin] mock: 211 transport dispatched');
        }
      }
    });
  }
}

if (isMockMode()) {
  console.info('[heat-checkin] running in mock mode — see app/heat/mock-responses.json');
}
