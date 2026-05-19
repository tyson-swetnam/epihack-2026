// today/today.js
// Controller for the AZ One Health Today aggregated dashboard.
//
// Design notes:
//  * Every panel renders independently. A failed feed surfaces an .err
//    block in *its* panel and never blocks the rest of the page.
//  * The hero + the geo strip share a single county state. When the
//    user changes county (via auto-detect or the dropdown) we re-render
//    every panel that depends on it.
//  * Reuses app/shared/i18n.js for the EN/ES bundle convention and
//    extends it with a tiny page-specific bundle.

import {
  fetchHeatRisk,
  fetchWnvPositivity,
  fetchWildlifeSignals,
  fetchCoolingCenters,
  fetchStatewideRollup,
  fmtNumber,
  fmtAsOf,
  isMockMode,
} from './shared/feeds.js';
import { mountGeoStrip, AZ_COUNTIES } from './shared/geo-strip.js';
import { renderSparkline } from './shared/sparkline.js';
import { mountMap } from './shared/map-embed.js';
import {
  t, currentLang, setLang, onLangChange, mountSwitcher, applyAttributes,
} from '../app/shared/i18n.js';

// ---------------------------------------------------------------------------
// Page-specific i18n. Extend the central bundle with our keys. The shape
// mirrors app/shared/i18n.js — keys missing from this small bundle fall
// back to English automatically.
// ---------------------------------------------------------------------------
const PAGE_STRINGS = {
  en: {
    'today.subtitle.statewide': 'Heat, mosquito surveillance, and wildlife — across Arizona.',
    'today.subtitle.county':    'Heat, mosquito surveillance, and wildlife in {county}.',
    'today.heroHeadline.magenta':'Magenta HeatRisk in {area} today',
    'today.heroHeadline.red':    'Red HeatRisk in {area} today',
    'today.heroHeadline.orange': 'Orange HeatRisk in {area} today',
    'today.heroHeadline.yellow': 'Yellow HeatRisk in {area} today',
    'today.heroHeadline.green':  'Low heat risk in {area} today',
    'today.heroHeadline.wnv':    'WNV vector index up {x}x in {area} this week',
    'today.geo.statewide':  'Arizona (statewide)',
    'today.geo.your_area':  'Your area',
    'today.geo.detecting':  'Locating you…',
    'today.geo.detected':   'Showing {county}.',
    'today.geo.saved':      'Showing {county} (saved).',
    'today.geo.denied':     'Location not shared — showing statewide.',
    'today.geo.unsupported':'Location unavailable — showing statewide.',
    'today.geo.outside':    'You appear to be outside Arizona — showing statewide.',
    'today.geo.cleared':    'Showing statewide.',
    'today.heat.title':     'Heat today',
    'today.heat.advice_short':'Stay indoors with AC noon–7pm. Check on neighbors over 65 or unsheltered.',
    'today.heat.centers':   '{n} cooling centers within 5 km in {area}.',
    'today.heat.centers_state':'{n} cooling centers across Maricopa County (and more statewide).',
    'today.vbd.title':      'Vector-borne disease',
    'today.vbd.positives':  '{n} WNV-positive pools (4-week)',
    'today.vbd.context_county':'{county}: {label} ({pos} positive of {total} pools tested in the latest biweek).',
    'today.vbd.context_state':'Statewide: {pos} positive of {total} pools tested in the latest biweek.',
    'today.wild.title':     'Recent wildlife signals',
    'today.rollup.title':   'Statewide snapshot',
    'today.rollup.asof':    'Updated {when}. Refreshes hourly.',
    'today.action.title':   'What can I do right now?',
    'today.foot.title':     'How this works',
    'today.foot.privacy':   'no PII',
    'today.err.fetch':      'Could not load this panel right now.',
    'today.btn.find_center':'Find a cooling center',
    'today.btn.heat_self':  'Heat self-report',
    'today.btn.tick':       "Report what you've seen",
    'today.btn.graph':      'See the pathogen graph',
    'today.btn.map':        'Open the full AZ map',
    'today.btn.tick_short': 'Submit a tick',
    'today.btn.checkin':    'Heat check-in for a friend',
    'today.btn.centers':    'See cooling centers near me',
    'today.trend.up':       'up',
    'today.trend.down':     'down',
    'today.trend.flat':     'flat',
  },
  es: {
    'today.subtitle.statewide':'Calor, vigilancia de mosquitos y vida silvestre — Arizona.',
    'today.subtitle.county':   'Calor, mosquitos y vida silvestre en {county}.',
    'today.heroHeadline.magenta':'Riesgo de calor Magenta en {area} hoy',
    'today.heroHeadline.red':    'Riesgo de calor Rojo en {area} hoy',
    'today.heroHeadline.orange': 'Riesgo de calor Naranja en {area} hoy',
    'today.heroHeadline.yellow': 'Riesgo de calor Amarillo en {area} hoy',
    'today.heroHeadline.green':  'Riesgo de calor bajo en {area} hoy',
    'today.heroHeadline.wnv':    'Índice de VNO subió {x}x en {area} esta semana',
    'today.geo.statewide':  'Arizona (todo el estado)',
    'today.geo.your_area':  'Su área',
    'today.geo.detecting':  'Ubicándole…',
    'today.geo.detected':   'Mostrando {county}.',
    'today.geo.saved':      'Mostrando {county} (guardado).',
    'today.geo.denied':     'Ubicación no compartida — mostrando todo el estado.',
    'today.geo.unsupported':'Ubicación no disponible — mostrando todo el estado.',
    'today.geo.outside':    'Parece estar fuera de Arizona — mostrando todo el estado.',
    'today.geo.cleared':    'Mostrando todo el estado.',
    'today.heat.title':     'Calor hoy',
    'today.heat.advice_short':'Quédese bajo techo con AC de mediodía a 7pm. Revise a vecinos mayores o sin hogar.',
    'today.heat.centers':   '{n} centros de enfriamiento a 5 km en {area}.',
    'today.heat.centers_state':'{n} centros en el condado de Maricopa (y más en el estado).',
    'today.vbd.title':      'Enfermedades por vectores',
    'today.vbd.positives':  '{n} grupos de mosquitos con VNO (4 semanas)',
    'today.vbd.context_county':'{county}: {label} ({pos} positivos de {total} grupos probados en la última quincena).',
    'today.vbd.context_state':'En el estado: {pos} positivos de {total} grupos probados.',
    'today.wild.title':     'Señales recientes de fauna',
    'today.rollup.title':   'Resumen estatal',
    'today.rollup.asof':    'Actualizado {when}. Cada hora.',
    'today.action.title':   '¿Qué puedo hacer ahora?',
    'today.foot.title':     'Cómo funciona esto',
    'today.foot.privacy':   'sin datos personales',
    'today.err.fetch':      'No se pudo cargar este panel ahora.',
    'today.btn.find_center':'Buscar un centro de enfriamiento',
    'today.btn.heat_self':  'Reporte de calor',
    'today.btn.tick':       'Reporte lo que vio',
    'today.btn.graph':      'Ver el grafo de patógenos',
    'today.btn.map':        'Abrir el mapa de AZ',
    'today.btn.tick_short': 'Enviar una garrapata',
    'today.btn.checkin':    'Chequeo por calor para un amigo',
    'today.btn.centers':    'Centros de enfriamiento cerca',
    'today.trend.up':       'sube',
    'today.trend.down':     'baja',
    'today.trend.flat':     'estable',
  },
};

// Small wrapper: try the page bundle first, then fall back to the
// shared i18n.js bundle. The shared one already supports {placeholder}
// substitution; we re-implement it here for the page-local strings.
function ts(key, vars) {
  const lang = currentLang();
  const bundle = PAGE_STRINGS[lang] || PAGE_STRINGS.en;
  if (key in bundle) {
    const raw = bundle[key];
    if (!vars) return raw;
    return raw.replace(/\{(\w+)\}/g, (_, k) =>
      Object.prototype.hasOwnProperty.call(vars, k) ? String(vars[k]) : `{${k}}`);
  }
  return t(key, vars);
}

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
const state = {
  county: null,       // null = statewide
  feeds: {},          // cached feed results
};

const $ = (id) => document.getElementById(id);

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', init);

function init() {
  mountSwitcher(document.querySelector('.today-bar'));
  onLangChange(() => rerenderAll());

  mountGeoStrip({
    select: $('county'),
    status: $('geo-status'),
    onChange: (county) => {
      state.county = county;
      rerenderAll();
    },
    labels: geoLabels(),
  });

  // Kick off all feeds in parallel. Each promise updates its own panel
  // even if other feeds are still pending.
  loadAndRender('heatrisk',        fetchHeatRisk,        renderHeat);
  loadAndRender('wnv',             fetchWnvPositivity,   renderVbd);
  loadAndRender('wildlife',        fetchWildlifeSignals, renderWildlife);
  loadAndRender('cooling_centers', fetchCoolingCenters,  () => renderHeat()); // re-renders heat
  loadAndRender('rollup',          fetchStatewideRollup, renderRollup);

  // Static date string in case heat feed is delayed.
  setHeroDate();

  if (isMockMode()) {
    console.info('[today] running in mock mode — see today/mock/*.json');
  }
}

function geoLabels() {
  return {
    statewide:   ts('today.geo.statewide'),
    detecting:   ts('today.geo.detecting'),
    detected:    ts('today.geo.detected'),
    saved:       ts('today.geo.saved'),
    denied:      ts('today.geo.denied'),
    unsupported: ts('today.geo.unsupported'),
    outside:     ts('today.geo.outside'),
    cleared:     ts('today.geo.cleared'),
    pick:        ts('today.geo.your_area'),
  };
}

async function loadAndRender(key, fetcher, render) {
  try {
    const data = await fetcher();
    state.feeds[key] = data;
    render(data);
  } catch (e) {
    console.warn(`[today] feed failed: ${key}`, e);
    renderError(key, e);
  }
}

function renderError(key, err) {
  const host = {
    heatrisk:        'heat-advice',
    wnv:             'vbd-context',
    wildlife:        'wild-list',
    cooling_centers: 'heat-centers',
    rollup:          'rollup-grid',
  }[key];
  const el = host && $(host);
  if (el) el.innerHTML = `<span class="err">${escapeHtml(ts('today.err.fetch'))} (${escapeHtml(key)})</span>`;
}

function rerenderAll() {
  setHeroDate();
  if (state.feeds.heatrisk)        renderHeat(state.feeds.heatrisk);
  if (state.feeds.wnv)             renderVbd(state.feeds.wnv);
  if (state.feeds.wildlife)        renderWildlife(state.feeds.wildlife);
  if (state.feeds.rollup)          renderRollup(state.feeds.rollup);
  // i18n attributes
  applyAttributes(document);
}

// ---------------------------------------------------------------------------
// Hero
// ---------------------------------------------------------------------------
function setHeroDate() {
  const lang = currentLang();
  const today = new Date();
  const opts = { weekday: 'long', month: 'short', day: 'numeric' };
  try {
    const f = new Intl.DateTimeFormat(lang === 'es' ? 'es-MX' : 'en-US', opts).format(today);
    const area = areaName();
    $('hero-date').textContent = `${f} · ${area}`;
  } catch (_) {
    $('hero-date').textContent = today.toDateString();
  }
}

function areaName() {
  return state.county ? state.county.name : ts('today.geo.statewide');
}

function chooseHeadline(heatrisk, wnv) {
  // Headline picks whichever signal is most actionable. We rank by:
  //   1. Magenta or Red HeatRisk anywhere in the focused area
  //   2. WNV trend "up X x" in the focused county (only if county set)
  //   3. Otherwise: today's HeatRisk tier
  const tier = heatrisk && heatrisk.today && heatrisk.today.category
             ? heatrisk.today.category.label : null;

  const countyKey = state.county && state.county.name;
  const countyWnv = countyKey && wnv && wnv.by_county && wnv.by_county[countyKey];
  if (countyWnv && countyWnv.trend_multiple && countyWnv.trend_multiple >= 2.5) {
    return {
      tier: 'red',
      text: ts('today.heroHeadline.wnv', {
        x: countyWnv.trend_multiple.toFixed(1).replace(/\.0$/, ''),
        area: countyKey,
      }),
    };
  }

  if (tier === 'Magenta') return { tier: 'magenta', text: ts('today.heroHeadline.magenta', { area: areaName() }) };
  if (tier === 'Red')     return { tier: 'red',     text: ts('today.heroHeadline.red',     { area: areaName() }) };
  if (tier === 'Orange')  return { tier: 'orange',  text: ts('today.heroHeadline.orange',  { area: areaName() }) };
  if (tier === 'Yellow')  return { tier: 'yellow',  text: ts('today.heroHeadline.yellow',  { area: areaName() }) };
  return { tier: 'green', text: ts('today.heroHeadline.green', { area: areaName() }) };
}

// ---------------------------------------------------------------------------
// Heat panel
// ---------------------------------------------------------------------------
function renderHeat(heatrisk) {
  heatrisk = heatrisk || state.feeds.heatrisk;
  if (!heatrisk) return;

  const tier  = heatrisk.today.category.label;
  const tempF = heatrisk.today.ambient_temp_f;

  // Hero
  const h = chooseHeadline(heatrisk, state.feeds.wnv);
  $('hero').setAttribute('data-tier', h.tier);
  $('hero-headline').textContent = h.text;
  $('hero-sub').textContent = state.county
    ? ts('today.subtitle.county', { county: state.county.name })
    : ts('today.subtitle.statewide');

  // 7-day strip
  const strip = $('hero-week');
  strip.innerHTML = (heatrisk.week || []).map((d) => `
    <div class="day" data-tier="${escapeHtml(d.category)}" title="${escapeHtml(d.date)} ${escapeHtml(d.category)} ${escapeHtml(String(d.high_f))}&deg;F">
      <span class="d">${escapeHtml(shortDay(d.date))}</span>
      <span class="c">${escapeHtml(d.category)}</span>
      <span class="c">${escapeHtml(String(d.high_f))}&deg;</span>
    </div>
  `).join('');

  // Pill + temperature + advice
  const pill = $('heat-pill');
  pill.setAttribute('data-tier', tier);
  pill.textContent = tier;
  pill.setAttribute('aria-label', `HeatRisk today: ${tier}`);
  $('heat-temp').textContent     = `${tempF}°`;
  $('heat-temp-unit').textContent = 'F (forecast high)';
  $('heat-advice').textContent   = heatrisk.today.advice_short || ts('today.heat.advice_short');

  // Cooling-center count
  const cc = state.feeds.cooling_centers;
  if (cc) {
    const county = state.county && state.county.name;
    const n = county && cc.counts_by_county && cc.counts_by_county[county]
            ? cc.counts_by_county[county]
            : (cc.counts_by_county && cc.counts_by_county.Maricopa) || 0;
    $('heat-centers').textContent = county
      ? ts('today.heat.centers',       { n, area: county })
      : ts('today.heat.centers_state', { n });
  }
}

function shortDay(iso) {
  try {
    const d = new Date(iso + 'T12:00:00');
    return new Intl.DateTimeFormat(currentLang() === 'es' ? 'es-MX' : 'en-US',
      { weekday: 'short' }).format(d);
  } catch (_) { return iso.slice(5); }
}

// ---------------------------------------------------------------------------
// VBD panel
// ---------------------------------------------------------------------------
function renderVbd(wnv) {
  const lang = currentLang();
  const county = state.county && state.county.name;
  const bucket = county && wnv.by_county && wnv.by_county[county]
               ? wnv.by_county[county]
               : { intervals: wnv.statewide.intervals, trend_label: null, trend_multiple: null };

  const intervals = bucket.intervals || [];
  const totalPos = intervals.reduce((a, b) => a + (b.positive_pools || 0), 0);
  const series = intervals.map((b) => b.positive_pools || 0);

  $('vbd-positives').textContent = fmtNumber(totalPos, lang);

  // Trend pill
  const tEl = $('vbd-trend');
  if (bucket.trend_multiple != null && bucket.trend_multiple >= 2) {
    tEl.className = 'trend up';
    tEl.textContent = `↑ ${bucket.trend_multiple.toFixed(1)}x`;
  } else if (series.length >= 2 && series[series.length - 1] > series[0]) {
    tEl.className = 'trend up';
    tEl.textContent = `↑ ${ts('today.trend.up')}`;
  } else if (series.length >= 2 && series[series.length - 1] < series[0]) {
    tEl.className = 'trend down';
    tEl.textContent = `↓ ${ts('today.trend.down')}`;
  } else {
    tEl.className = 'trend flat';
    tEl.textContent = `— ${ts('today.trend.flat')}`;
  }

  // Sparkline
  renderSparkline($('vbd-spark'), series, {
    ariaLabel: `${county || 'Arizona'} WNV positive pools by biweek`,
    stroke: '#C0392B',
    fill: 'rgba(192,57,43,.12)',
  });

  // Context line
  const last = intervals[intervals.length - 1] || {};
  $('vbd-context').textContent = county
    ? ts('today.vbd.context_county', {
        county,
        label: bucket.trend_label || ts('today.trend.flat'),
        pos: last.positive_pools || 0,
        total: last.total_pools || 0,
      })
    : ts('today.vbd.context_state', {
        pos: last.positive_pools || 0,
        total: last.total_pools || 0,
      });

  // Outbreak list
  const outs = wnv.active_outbreaks || [];
  $('vbd-outbreaks').innerHTML = outs.map((o) => `
    <li><strong>${escapeHtml(o.label)}</strong> — ${escapeHtml(o.summary)}
        <span class="muted small">(${escapeHtml(o.started)})</span></li>
  `).join('');
}

// ---------------------------------------------------------------------------
// Wildlife panel
// ---------------------------------------------------------------------------
function renderWildlife(wild) {
  const items = (wild && wild.items) || [];
  // Filter to the focused county if one is set; otherwise show all.
  const focused = state.county
    ? items.filter((i) => i.county && i.county.toLowerCase() === state.county.name.replace(/ County$/, '').toLowerCase())
    : items;
  // Fall back to "all items" if the county filter empties the list.
  const visible = focused.length ? focused : items;

  $('wild-list').innerHTML = visible.slice(0, 10).map((i) => `
    <li>
      <span class="ic" data-icon="${escapeHtml(i.icon || 'default')}" aria-hidden="true"></span>
      <span>
        <strong>${escapeHtml(i.label || i.species)}</strong>
        <span class="meta">${escapeHtml(i.county || '')} &middot; ${escapeHtml(i.date || '')}</span>
      </span>
      <span class="meta">${escapeHtml(i.source)}</span>
    </li>
  `).join('') || `<li><span class="muted">No recent signals.</span></li>`;

  // Lazy-load the map. mountMap is idempotent-friendly: we recreate the
  // host's children each time the data changes.
  const mapHost = $('wild-map');
  mapHost.innerHTML = '';
  mountMap(mapHost, visible.slice(0, 25), { intersect: true });
}

// ---------------------------------------------------------------------------
// Rollup panel
// ---------------------------------------------------------------------------
function renderRollup(rollup) {
  const lang = currentLang();
  const cells = (rollup.items || []).map((it) => `
    <div class="cell" role="group" aria-label="${escapeHtml(it.label)}: ${fmtNumber(it.value, lang)}">
      <span class="v">${fmtNumber(it.value, lang)}</span>
      <span class="l">${escapeHtml(it.label)}</span>
      <span class="t ${escapeHtml(it.trend)}">${escapeHtml(trendArrow(it.trend))}</span>
    </div>
  `).join('');
  $('rollup-grid').innerHTML = cells;
  $('rollup-asof').textContent = ts('today.rollup.asof', { when: fmtAsOf(rollup.as_of, lang) });
}

function trendArrow(t) {
  if (t === 'up')   return '↑';
  if (t === 'down') return '↓';
  return '—';
}

// ---------------------------------------------------------------------------
// Util
// ---------------------------------------------------------------------------
function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}
