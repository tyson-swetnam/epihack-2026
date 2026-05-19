// self-report.js
// Anonymous heat self-report flow. Mirrors the CHW check-in form but
// without the Identify step -- there is no proxy reporter, so we don't
// collect age/sex/unsheltered/pet up front. The success card offers a
// phone link to 211 Arizona instead of dispatching transport.

import { requestLocation, isPlausibleZip } from '../../shared/geo.js';
import { submitIntake, isMockMode }       from '../../shared/intake-client.js';
import { t, mountSwitcher, onLangChange } from '../../shared/i18n.js';
import {
  $, $$, escapeHtml,
  renderThermometer, renderCenterCard,
  rankCenters, triageLabel
} from '../heat-shared.js';

const STEPS = [
  { id: 'where',    name: 'Where'    },
  { id: 'symptoms', name: 'Symptoms' },
  { id: 'exposure', name: 'Exposure' },
  { id: 'consent',  name: 'Consent'  },
  { id: 'submit',   name: 'Submit'   }
];

const state = {
  step: 0,
  geo: null, zip: '', checkin_time: '',
  symptoms: [], core_temp_f: null,
  outdoor_hours: 3,
  ac_access:  true,
  last_water: 'under_1h',
  thermo_meds: false,
  consent: false
};

document.addEventListener('DOMContentLoaded', init);

function init() {
  $('progress').hidden  = false;
  $('sticky-bar').hidden = false;

  mountSwitcher(document.querySelector('.heat-header'));
  onLangChange(() => {
    renderStep();
    if (state.step === STEPS.length - 1 && !$('submit-pre').hidden) renderSubmitSummary();
  });

  wireWhere();
  wireSymptoms();
  wireExposure();
  wireConsent();
  wireNavigation();

  const now = new Date();
  $('time-of-checkin').value =
    `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;
  state.checkin_time = $('time-of-checkin').value;

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
    nextBtn.classList.remove('heat');
    nextBtn.classList.add('success');
    renderSubmitSummary();
  } else {
    nextBtn.textContent =
      state.step === STEPS.length - 2 ? t('nav.review') : t('nav.next');
    nextBtn.classList.remove('success');
    nextBtn.classList.add('heat');
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
  state.step += 1; renderStep();
}

function validateStep(id) {
  switch (id) {
    case 'where':
      if (!state.geo && !isPlausibleZip(state.zip)) {
        return 'Tap "Use my location" or enter a 5-digit ZIP.';
      }
      if (!state.checkin_time) return 'Pick a time.';
      return null;
    case 'consent':
      if (!state.consent) return 'Consent acceptance is required.';
      return null;
    default:
      return null;
  }
}

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

  $('zip').addEventListener('input', (e) => { state.zip = e.target.value.trim(); });
  $('time-of-checkin').addEventListener('change', (e) => { state.checkin_time = e.target.value; });
}

function wireSymptoms() {
  $('symptoms-grid').addEventListener('change', (e) => {
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

function wireExposure() {
  const slider = $('outdoor-hours');
  const value  = $('outdoor-hours-value');
  const renderSlider = () => {
    state.outdoor_hours = parseInt(slider.value, 10);
    value.textContent = t('heat.exposure.outdoor.value', { n: state.outdoor_hours });
  };
  slider.addEventListener('input', renderSlider);
  renderSlider();
  $('ac-access').addEventListener('change',   (e) => { state.ac_access   = e.target.checked; });
  $('thermo-meds').addEventListener('change', (e) => { state.thermo_meds = e.target.checked; });
  document.querySelectorAll('input[name="last-water"]').forEach((el) => {
    el.addEventListener('change', (e) => { state.last_water = e.target.value; });
  });
}

function wireConsent() {
  $('consent-ok').addEventListener('change', (e) => { state.consent = e.target.checked; });
}

function renderSubmitSummary() {
  const lines = [];
  if (state.geo) lines.push(`Location: GPS ${state.geo.lat.toFixed(3)}, ${state.geo.lon.toFixed(3)}`);
  else if (state.zip) lines.push(`Location: ZIP ${state.zip}`);
  lines.push(`Time: ${state.checkin_time}`);
  lines.push(`Symptoms: ${state.symptoms.length ? state.symptoms.join(', ') : 'none reported'}`);
  if (state.core_temp_f != null) lines.push(`Core temp: ${state.core_temp_f} °F`);
  lines.push(`Outdoor: ${state.outdoor_hours} h · AC: ${state.ac_access ? 'yes' : 'no'} · ` +
             `water: ${state.last_water} · meds: ${state.thermo_meds ? 'yes' : 'no'}`);
  $('summary-body').innerHTML = lines.map((l) =>
    `<div>${escapeHtml(l)}</div>`).join('');
}

function buildPayload() {
  return {
    flow: 'heat_self_report',
    vertical: 'heat',
    channel: 'mobile',
    consent_profile: 'consent.anonymous_heat',
    general: {
      reported_at: new Date().toISOString(),
      lat: state.geo ? state.geo.lat : null,
      lon: state.geo ? state.geo.lon : null,
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
      outdoor_time_24h_hours: state.outdoor_hours,
      ac_access:              state.ac_access ? 'yes' : 'no',
      last_water_bucket:      state.last_water,
      thermo_meds:            state.thermo_meds
    },
    environmental: {}
  };
}

function pickMockKey() {
  if (state.symptoms.includes('hot_dry_skin') ||
      state.symptoms.includes('confusion') ||
      (state.core_temp_f != null && state.core_temp_f >= 104)) {
    return 'heat_chw_checkin_911';
  }
  // Default self-report = drink-water advisory.
  return 'heat_self_report';
}

async function doSubmit() {
  const pre    = $('submit-pre');
  const pend   = $('submit-pending');
  const result = $('submit-result');
  const error  = $('submit-error');
  const stick  = $('sticky-bar');

  pre.hidden = true; pend.hidden = false;
  result.hidden = true; error.hidden = true; stick.hidden = true;

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
    const res = await submitIntake('heat_self_report', payload, {
      vertical: 'heat',
      mockKey:  pickMockKey()
    });
    pend.hidden = true;
    renderResult(res);
  } catch (e) {
    pend.hidden = true;
    pre.hidden  = false;
    stick.hidden = false;
    error.hidden = false;
    error.textContent = `Submit failed: ${e.message}.`;
  }
}

function renderResult(res) {
  const el = $('submit-result');
  el.hidden = false;

  const tc = res.triage_class || 'tc.check_in_only';
  const tcSlug = tc.replace(/^tc\./, '');
  const centers = rankCenters((res.cooling_centers && res.cooling_centers.centers) || []);
  const nearest = centers[0];
  const phone = (res.transport_offer && res.transport_offer.phone) || '+1-877-211-8661';

  el.innerHTML = `
    <div class="result-card tc-${tcSlug}" role="status" aria-live="polite">
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

    <div class="section-block">
      <h3>211 Arizona</h3>
      <p>Heat-relief, hydration drop-off, and transport are all on the
         same statewide line. Tap to call &mdash; self-report does
         <em>not</em> auto-dispatch a vehicle.</p>
      <a class="btn heat block" href="tel:${escapeHtml(phone.replace(/[^+0-9]/g,''))}"
         aria-label="${escapeHtml(t('heat.submit.call_211'))}">
        ${escapeHtml(t('heat.submit.call_211'))}
      </a>
    </div>

    ${tc === 'tc.call_911' ? `
    <div class="section-block" style="border-color:var(--c-red)">
      <h3 style="color:#7a1a12">911</h3>
      <a class="btn danger block" href="tel:911">${escapeHtml(t('tc.call_911'))}</a>
    </div>` : ''}

    <div class="section-block">
      <h3>kg writeback</h3>
      <p class="muted small">
        ${(res.milestones || []).map((m) =>
          `<span class="badge heat">${escapeHtml(m.milestone)}</span>`).join(' ')}
      </p>
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

  renderThermometer(el.querySelector('#thermo-host'),
    res.heat_vulnerability || { total: 0, max_possible: 15, components: [] });
}

if (isMockMode()) {
  console.info('[heat-selfreport] running in mock mode — see app/heat/mock-responses.json');
}
