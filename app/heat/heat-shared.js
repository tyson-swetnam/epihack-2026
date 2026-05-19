// heat-shared.js
// Bits of UI logic used by both check-in/ and self-report/.
// Imported as a regular ES module; no globals.

import { t, currentLang } from '../shared/i18n.js';

/* ---------------------------------------------------------------------------
   Small DOM helpers
   ------------------------------------------------------------------------ */

export const $  = (id, root = document) => root.getElementById ? root.getElementById(id) : root.querySelector(`#${id}`);
export const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

export function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

/* ---------------------------------------------------------------------------
   "Confirm to dispatch" button. A single accidental tap must not dispatch
   a real vehicle (or call 911 etc.) -- the button has three states:
       idle     -> tap once -> armed (shows "tap again to confirm")
       armed    -> tap again within 4 s -> dispatched (fires the callback)
       armed    -> 4 s of inactivity     -> back to idle
   ------------------------------------------------------------------------ */

export function attachConfirm(btn, { onConfirm, armedLabel, dispatchedLabel,
                                     armedMs = 4000 } = {}) {
  let state = 'idle';
  let timer = null;
  const originalLabel = btn.textContent;

  const setState = (next) => {
    state = next;
    btn.dataset.state = next === 'idle' ? '' : next;
    if (next === 'armed' && armedLabel) btn.textContent = armedLabel;
    else if (next === 'dispatched' && dispatchedLabel) btn.textContent = dispatchedLabel;
    else if (next === 'idle') btn.textContent = originalLabel;
  };

  btn.addEventListener('click', (ev) => {
    ev.preventDefault();
    if (state === 'idle') {
      setState('armed');
      clearTimeout(timer);
      timer = setTimeout(() => setState('idle'), armedMs);
      return;
    }
    if (state === 'armed') {
      clearTimeout(timer);
      setState('dispatched');
      try { onConfirm && onConfirm(); } catch (e) { console.error(e); }
    }
  });

  return { reset: () => { clearTimeout(timer); setState('idle'); } };
}

/* ---------------------------------------------------------------------------
   Vulnerability "thermometer" renderer. Drives the CSS-only horizontal bar.
   ------------------------------------------------------------------------ */

export function renderThermometer(host, score) {
  const total = score && typeof score.total === 'number' ? score.total : 0;
  const max   = score && score.max_possible ? score.max_possible : 15;
  const pct   = Math.max(0, Math.min(100, (total / max) * 100));
  const tier  = total >= 12 ? 'magenta'
              : total >= 9  ? 'red'
              : total >= 5  ? 'orange'
              :              'yellow';
  const comps = (score && score.components) || [];

  const breakdown = comps.map((c) => `
    <li>
      <span>${escapeHtml(c.label || c.factor)}</span>
      <span class="pts">+${c.points}</span>
    </li>`).join('');

  host.innerHTML = `
    <div class="thermo" role="img"
         aria-label="${t('heat.submit.score')}: ${total} ${t('heat.submit.score.outof', { max })}">
      <div class="thermo-head">
        <span><strong>${total}</strong> ${t('heat.submit.score.outof', { max })}</span>
        <span class="max">${escapeHtml(t('heat.submit.score'))}</span>
      </div>
      <div class="thermo-track">
        <div class="thermo-fill" data-tier="${tier}" style="width:${pct}%"></div>
      </div>
      <ul class="thermo-breakdown">${breakdown || '<li><span>—</span><span class="pts">0</span></li>'}</ul>
    </div>
  `;
}

/* ---------------------------------------------------------------------------
   Centre-card renderer. Used both inline (success card -> nearest center)
   and in the cool-off list page.
   ------------------------------------------------------------------------ */

export function renderCenterCard(center, { showActions = true } = {}) {
  const badges = [];
  if (center.open_now)         badges.push(`<span class="badge heat">${escapeHtml(t('cooloff.center.open'))}</span>`);
  if (center.pets_ok)          badges.push(`<span class="badge cool">${escapeHtml(t('cooloff.center.pets'))}</span>`);
  if (center.transport_eligible) badges.push(`<span class="badge magenta">${escapeHtml(t('cooloff.center.transport'))}</span>`);

  const maps   = center.maps_url
    || `https://maps.google.com/?q=${encodeURIComponent(center.address || '')}`;
  const phone  = center.phone || '+1-877-211-8661';
  const actions = showActions ? `
    <div class="actions">
      <a class="btn heat block" href="${escapeHtml(maps)}" target="_blank" rel="noopener"
         aria-label="${escapeHtml(t('cooloff.center.open_maps'))} — ${escapeHtml(center.name)}">
        ${escapeHtml(t('cooloff.center.open_maps'))}
      </a>
      <a class="btn secondary block" href="tel:${escapeHtml(phone.replace(/[^+0-9]/g,''))}"
         aria-label="${escapeHtml(t('cooloff.center.call_211'))}">
        ${escapeHtml(t('cooloff.center.call_211'))}
      </a>
    </div>` : '';
  return `
    <li class="center">
      <h3>${escapeHtml(center.name)}</h3>
      <div class="meta">
        ${center.distance_km != null ? escapeHtml(t('cooloff.center.distance', { km: center.distance_km.toFixed(1) })) + ' &middot; ' : ''}
        ${escapeHtml(center.hours_today || '')}
      </div>
      <div class="meta">${escapeHtml(center.address || '')}</div>
      ${(center.services && center.services.length)
        ? `<div class="meta"><em>${center.services.map(escapeHtml).join(' &middot; ')}</em></div>`
        : ''}
      <div class="badges">${badges.join(' ')}</div>
      ${actions}
    </li>`;
}

/* ---------------------------------------------------------------------------
   Triage-class human label. Maps a tc.* string to an i18n key.
   ------------------------------------------------------------------------ */

export function triageLabel(tc) {
  return t(tc) || tc;
}

/* ---------------------------------------------------------------------------
   Sort cooling centers by distance, then by transport eligibility.
   ------------------------------------------------------------------------ */

export function rankCenters(centers) {
  return (centers || []).slice().sort((a, b) => {
    const da = a.distance_km ?? 99;
    const db = b.distance_km ?? 99;
    if (da !== db) return da - db;
    return (b.transport_eligible ? 1 : 0) - (a.transport_eligible ? 1 : 0);
  });
}
