// tick/tick.js
// Vanilla ES-module that drives the multi-step tick mail-in flow.
// No framework, no bundler. Imports two shared helpers.

import { requestLocation, isPlausibleZip } from '../shared/geo.js';
import { submitIntake, isMockMode } from '../shared/intake-client.js';
import { enqueueReport } from '../shared/sync.js';
import { bootstrapOfflineUi } from '../shared/sw-register.js';

// Register the service worker + mount the sync-status pill in the header.
bootstrapOfflineUi();

// ---------------------------------------------------------------------------
// Step orchestration
// ---------------------------------------------------------------------------

const STEPS = [
  { id: 'welcome',  name: 'Welcome'      },
  { id: 'where',    name: 'Where & when' },
  { id: 'photo',    name: 'Photo'        },
  { id: 'symptoms', name: 'Symptoms'     },
  { id: 'consent',  name: 'Consent'      },
  { id: 'submit',   name: 'Submit'       }
];

// Application state — everything the user enters lives here so a single
// payload can be assembled at submit time.
const state = {
  step: 0,
  geo: null,           // { source, lat, lon } or null
  zip: '',
  date_attached: '',
  hours_attached: '',
  body_location: '',
  photo: null,         // File
  symptoms: [],        // ['fever', ...]
  consent: false
};

// DOM handles, captured after DOMContentLoaded.
const $ = (id) => document.getElementById(id);

document.addEventListener('DOMContentLoaded', init);

function init() {
  // Reveal the progress bar and sticky bar now that JS is alive.
  $('progress').hidden = false;
  $('sticky-bar').hidden = false;

  wireGeoStep();
  wireWhereInputs();
  wirePhotoStep();
  wireSymptomsStep();
  wireConsentStep();
  wireNavigation();

  renderStep();

  // Pre-fill today's date so the field isn't blank for the common case
  // "I just pulled it off."
  const today = new Date().toISOString().slice(0, 10);
  $('date-attached').value = today;
  state.date_attached = today;
}

function renderStep() {
  const stepDef = STEPS[state.step];

  // Show/hide sections.
  document.querySelectorAll('.step').forEach((el) => {
    const isActive = el.dataset.step === stepDef.id;
    el.classList.toggle('active', isActive);
    el.hidden = !isActive;
  });

  // Update progress bar.
  $('step-name').textContent  = stepDef.name;
  $('step-count').textContent = `Step ${state.step + 1} of ${STEPS.length}`;
  $('progress-fill').style.width =
    `${((state.step + 1) / STEPS.length) * 100}%`;

  // Update nav buttons.
  const backBtn = $('back-btn');
  const nextBtn = $('next-btn');
  backBtn.disabled = state.step === 0;
  backBtn.style.visibility = state.step === 0 ? 'hidden' : 'visible';

  if (stepDef.id === 'submit') {
    nextBtn.textContent = 'Submit';
    nextBtn.classList.add('success');
    renderSubmitSummary();
  } else {
    nextBtn.textContent = state.step === STEPS.length - 2 ? 'Review' : 'Next';
    nextBtn.classList.remove('success');
  }

  // Focus management: move keyboard focus to the new step's heading
  // for screen-reader users (but avoid stealing it on the very first load).
  if (state.step !== 0) {
    const h = document.querySelector('.step.active h2');
    if (h) {
      h.setAttribute('tabindex', '-1');
      h.focus({ preventScroll: false });
    }
  }

  // Always scroll to top of the new step.
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function wireNavigation() {
  $('next-btn').addEventListener('click', onNext);
  $('back-btn').addEventListener('click', () => {
    if (state.step > 0) {
      state.step -= 1;
      renderStep();
    }
  });
}

function onNext() {
  const stepDef = STEPS[state.step];
  const err = validateStep(stepDef.id);
  if (err) {
    alert(err); // mobile-friendly, no extra dom needed
    return;
  }

  if (stepDef.id === 'submit') {
    doSubmit();
    return;
  }

  state.step += 1;
  renderStep();
}

function validateStep(id) {
  switch (id) {
    case 'where':
      if (!state.geo && !isPlausibleZip(state.zip)) {
        return 'Tap "Use my location" or enter a valid 5-digit ZIP.';
      }
      if (!state.date_attached) return 'Pick the date you noticed the tick.';
      if (!state.hours_attached) return 'Pick how long the tick was attached.';
      if (!state.body_location) return 'Pick where on your body the tick was.';
      return null;
    case 'consent':
      if (!state.consent) return 'You need to accept the consent profile to continue.';
      return null;
    default:
      return null;
  }
}

// ---------------------------------------------------------------------------
// Step 2: Where & when
// ---------------------------------------------------------------------------

function wireGeoStep() {
  const btn    = $('geo-btn');
  const status = $('geo-status');
  const text   = $('geo-status-text');

  btn.addEventListener('click', async () => {
    btn.disabled = true;
    status.classList.remove('ok', 'warn');
    text.textContent = 'Asking for location permission…';

    const loc = await requestLocation();
    btn.disabled = false;

    if (loc.source === 'gps') {
      state.geo = loc;
      status.classList.add('ok');
      text.textContent =
        `Got it: ${loc.lat.toFixed(4)}, ${loc.lon.toFixed(4)} ` +
        `(±${Math.round(loc.accuracy)} m)`;
    } else if (loc.source === 'unsupported') {
      state.geo = null;
      status.classList.add('warn');
      text.textContent = 'This device can\'t share location. Enter your ZIP instead.';
    } else {
      state.geo = null;
      status.classList.add('warn');
      text.textContent = 'Location not shared. Enter your ZIP below instead.';
    }
  });
}

function wireWhereInputs() {
  $('zip').addEventListener('input', (e) => {
    state.zip = e.target.value.trim();
  });
  $('date-attached').addEventListener('change', (e) => {
    state.date_attached = e.target.value;
  });
  $('hours-attached').addEventListener('change', (e) => {
    state.hours_attached = e.target.value;
  });
  $('body-location').addEventListener('change', (e) => {
    state.body_location = e.target.value;
  });
}

// ---------------------------------------------------------------------------
// Step 3: Photo
// ---------------------------------------------------------------------------

function wirePhotoStep() {
  const input   = $('photo');
  const label   = $('photo-label');
  const prompt  = $('photo-prompt');
  const preview = $('photo-preview');
  const clear   = $('photo-clear');

  input.addEventListener('change', () => {
    const file = input.files && input.files[0];
    if (!file) return;
    state.photo = file;
    label.classList.add('has-file');
    prompt.textContent = `Selected: ${file.name} — tap to replace`;
    preview.src = URL.createObjectURL(file);
    preview.hidden = false;
    preview.alt = 'Preview of the tick photo you selected';
    clear.hidden = false;
  });

  clear.addEventListener('click', () => {
    state.photo = null;
    input.value = '';
    label.classList.remove('has-file');
    prompt.textContent = 'Tap to take a photo or upload from your gallery';
    if (preview.src) URL.revokeObjectURL(preview.src);
    preview.removeAttribute('src');
    preview.hidden = true;
    clear.hidden = true;
  });
}

// ---------------------------------------------------------------------------
// Step 4: Symptoms
// ---------------------------------------------------------------------------

function wireSymptomsStep() {
  $('symptoms-grid').addEventListener('change', () => {
    state.symptoms = Array.from(
      document.querySelectorAll('#symptoms-grid input:checked')
    ).map((el) => el.value);
  });
}

// ---------------------------------------------------------------------------
// Step 5: Consent
// ---------------------------------------------------------------------------

function wireConsentStep() {
  $('consent-ok').addEventListener('change', (e) => {
    state.consent = e.target.checked;
  });
}

// ---------------------------------------------------------------------------
// Step 6: Submit
// ---------------------------------------------------------------------------

function renderSubmitSummary() {
  const lines = [];
  if (state.geo) {
    lines.push(`Location: GPS ${state.geo.lat.toFixed(3)}, ${state.geo.lon.toFixed(3)}`);
  } else if (state.zip) {
    lines.push(`Location: ZIP ${state.zip}`);
  }
  lines.push(`Date attached: ${state.date_attached || '—'}`);
  lines.push(`Hours attached: ${labelForHours(state.hours_attached)}`);
  lines.push(`Body location: ${labelForBody(state.body_location)}`);
  lines.push(`Photo: ${state.photo ? state.photo.name : 'none'}`);
  lines.push(`Symptoms: ${state.symptoms.length
    ? state.symptoms.join(', ') : 'none reported'}`);
  $('summary-body').innerHTML = lines.map((l) =>
    `<div>${escapeHtml(l)}</div>`).join('');
}

const HOURS_LABELS = {
  '0-2':   'Less than 2 hours',
  '2-6':   '2 to 6 hours',
  '6-24':  '6 to 24 hours',
  '24-48': '1 to 2 days',
  '48+':   'More than 2 days',
  unknown: 'Unknown'
};
const BODY_LABELS = {
  head_neck: 'Head or neck',
  torso: 'Torso',
  arm: 'Arm',
  hand: 'Hand',
  groin: 'Groin / waistline',
  leg: 'Leg',
  foot: 'Foot',
  other: 'Other / multiple'
};
const labelForHours = (h) => HOURS_LABELS[h] || '—';
const labelForBody  = (b) => BODY_LABELS[b]  || '—';

function buildPayload() {
  return {
    flow: 'tick_mailin',
    consent_profile: 'consent.tick_mailin',
    general: {
      reported_at: new Date().toISOString(),
      lat: state.geo ? state.geo.lat : null,
      lon: state.geo ? state.geo.lon : null,
      gps_accuracy_m: state.geo ? state.geo.accuracy : null,
      postal_code: state.zip || null
    },
    exposure: {
      tick_bite: true,
      attached_hours_bucket: state.hours_attached,
      bite_location_body: state.body_location,
      date_attached: state.date_attached
    },
    human: {
      symptoms: state.symptoms
    },
    auxiliary: {
      photo: state.photo
        ? { filename: state.photo.name,
            mime: state.photo.type,
            size_bytes: state.photo.size }
        : null
    }
  };
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

  // Walk the agent-log lines from pending -> done so the user sees progress.
  const agentLines = document.querySelectorAll('#agent-log .line');
  const totalDelay = 1400; // matches the mock latency in intake-client.js
  agentLines.forEach((el, i) => {
    setTimeout(() => {
      el.classList.remove('pending');
      el.classList.add('done');
    }, (totalDelay / agentLines.length) * (i + 1));
  });

  try {
    const payload = buildPayload();

    // Offline short-circuit: if the browser already knows it's offline,
    // skip the fetch attempt and queue immediately. This also covers the
    // mock-mode case where the SW won't see a real network request.
    if (typeof navigator !== 'undefined' && navigator.onLine === false) {
      await enqueueReport({
        flow: 'tick_mailin',
        vertical: 'vbd',
        payload,
        // Carry the actual photo File into the IDB queue so it
        // re-attaches on the multipart replay -- before this fix
        // offline tick submissions shipped without the picture.
        blob: state.photo || null,
        blob_field: state.photo ? 'auxiliary.photo' : null,
        blob_filename: state.photo ? state.photo.name : null,
      });
      pend.hidden = true;
      renderQueuedResult();
      return;
    }

    const res = await submitIntake('tick_mailin', payload,
                                   { photoBlob: state.photo });
    // The service worker may catch an offline submit and respond with a
    // 202 { queued: true } — in that case we still need to put it in the
    // IDB queue ourselves (the SW does not have the original payload).
    if (res && res.queued) {
      await enqueueReport({
        flow: 'tick_mailin',
        vertical: 'vbd',
        payload,
        // Carry the actual photo File into the IDB queue so it
        // re-attaches on the multipart replay -- before this fix
        // offline tick submissions shipped without the picture.
        blob: state.photo || null,
        blob_field: state.photo ? 'auxiliary.photo' : null,
        blob_filename: state.photo ? state.photo.name : null,
      });
      pend.hidden = true;
      renderQueuedResult();
      return;
    }
    pend.hidden = true;
    renderResult(res);
  } catch (e) {
    // Network rejection (DNS, CORS, offline w/o SW). Treat as offline-queue.
    try {
      await enqueueReport({
        flow: 'tick_mailin',
        vertical: 'vbd',
        payload: buildPayload()
      });
      pend.hidden = true;
      renderQueuedResult();
      return;
    } catch (_) { /* fall through to error UI */ }
    pend.hidden = true;
    pre.hidden  = false;
    stick.hidden = false;
    error.hidden = false;
    error.textContent = `Submit failed: ${e.message}. Try again, or come back later.`;
  }
}

function renderQueuedResult() {
  const el = $('submit-result');
  el.hidden = false;
  el.innerHTML = `
    <div class="result-card" role="status" aria-live="polite"
         style="border-left:6px solid #FFB300;background:#fff8e6">
      <h3>Saved offline.</h3>
      <p>You're offline (or the server isn't reachable). Your tick report
         is safely stored on this device and will upload automatically
         the next time you have a network connection.</p>
      <p class="muted small">
        Watch the <strong>pending</strong> badge in the header — it will
        switch to <strong>synced</strong> once the report reaches the
        Intake Agent.
      </p>
    </div>
    <div class="cta-grid">
      <a class="btn ghost" href="../index.html">Back to app home</a>
    </div>
  `;
}

function renderResult(res) {
  const el = $('submit-result');
  el.hidden = false;

  const sp = res.species_estimate || {};
  const wl = res.symptom_watchlist || {};
  const ml = res.mailing_label || {};
  const geo = res.geo || {};
  const pathogens = res.candidate_pathogens || [];

  const watchItems = (wl.watch_for || [])
    .map((w) => `<li>${escapeHtml(w)}</li>`).join('');
  const pathogenItems = pathogens
    .map((p) => `<li><strong>${escapeHtml(p.disease)}</strong> &mdash;
                 <em>${escapeHtml(p.name)}</em>
                 ${p.icd10 ? `<code>${escapeHtml(p.icd10)}</code>` : ''}</li>`)
    .join('');

  el.innerHTML = `
    <div class="result-card" role="status" aria-live="polite">
      <h3>Report received.</h3>
      <div class="species">
        ${escapeHtml(sp.common_name || 'Tick species: pending lab')}
        <span class="confidence">confidence ${
          sp.confidence != null ? Math.round(sp.confidence * 100) + '%' : '—'
        }</span>
      </div>
      <div class="sci">${escapeHtml(sp.scientific_name || '')}</div>
      ${sp.verify_with_lab
        ? `<p class="muted small" style="margin:.5rem 0 0">
             First-pass estimate only. Walker Lab species ID supersedes
             this on receipt.
           </p>`
        : ''}
      ${geo.resolved_county
        ? `<p class="kv" style="margin-top:.6rem">
             County: <strong>${escapeHtml(geo.resolved_county)}</strong>
             &middot; Vector control: <strong>${escapeHtml(geo.vector_control_agency || '—')}</strong>
           </p>`
        : ''}
    </div>

    <div class="section-block">
      <h3>Mailing label</h3>
      <p>Download, print, attach to a padded mailer with the tick in a
         sealed plastic bag.</p>
      <a class="btn block" href="${escapeAttr(ml.label_url || '#')}"
         download
         aria-label="Download mailing label PDF for the Great Arizona Tick Check lab">
        Download mailing label (PDF)
      </a>
      <div class="receipt">
        Submission ID: <code>${escapeHtml(ml.submission_id || '—')}</code><br>
        via <code>${escapeHtml(ml.tool || 'great-az-tick-check-mcp')}</code>
      </div>
    </div>

    <div class="section-block">
      <h3>14-day symptom watchlist</h3>
      <p>If any of these show up in the next ${wl.window_days || 14} days,
         tap the button below.</p>
      <ul>${watchItems || '<li>(no watchlist returned)</li>'}</ul>
      <div style="margin-top:.6rem">
        <a class="btn danger block" href="${escapeAttr(wl.if_symptoms_url || '#')}"
           rel="noopener"
           aria-label="If symptoms appear: open the next-steps guide">
          If symptoms appear &rarr;
        </a>
      </div>
    </div>

    <div class="section-block">
      <h3>Why this matters</h3>
      <p>Likely pathogens carried by ticks of this kind:</p>
      <ul>${pathogenItems || '<li>None matched.</li>'}</ul>
      ${res.vectorsurv_context
        ? `<p class="muted small" style="margin-top:.5rem">
             Live context (<code>${escapeHtml(res.vectorsurv_context.tool)}</code>):
             ${escapeHtml(res.vectorsurv_context.summary)}
           </p>`
        : ''}
    </div>

    <div class="section-block">
      <h3>See how your report fits in</h3>
      <div class="cta-grid">
        <a class="btn secondary" href="../../graph/index.html"
           aria-label="Open the pathogen knowledge graph">
          Pathogen graph
        </a>
        <a class="btn secondary" href="../../map/index.html"
           aria-label="Open the Arizona map of agencies and outbreaks">
          AZ map
        </a>
      </div>
      <p class="receipt" style="margin-top:.6rem">
        Edges written:
        <code>${escapeHtml((res.edges_written || []).length.toString())}</code>
        &middot;
        Observation: <code>${escapeHtml(res.observation_id || '—')}</code>
        ${res.mock ? '&middot; <span class="muted">(mock response)</span>' : ''}
      </p>
    </div>

    <div class="cta-grid">
      <a class="btn ghost" href="../index.html">Back to app home</a>
      <a class="btn ghost" href="../../plan/04-data-flows.html#scenario-a--hiker-mails-in-a-tick">
        Read Scenario A
      </a>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Tiny escape helpers
// ---------------------------------------------------------------------------

function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}
function escapeAttr(s) { return escapeHtml(s); }

// Banner in mock mode so demo viewers know it isn't hitting a real API.
if (isMockMode()) {
  console.info('[tick] running in mock mode — see app/mock-responses.json');
}
