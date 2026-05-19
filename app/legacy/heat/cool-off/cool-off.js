// cool-off.js
// "Where can I cool off?" — a lookup, not an intake. Reads the cached
// mag-hrn-mcp.search_centers fixture from app/heat/mock-responses.json
// (key: "cooling_centers_lookup") and renders the top 5 ranked by
// distance. In production, the same JS swaps to a real fetch against
// /api/cooling-centers?lat=&lon= once data-api-base is set on <body>.

import { requestLocation, isPlausibleZip } from '../../shared/geo.js';
import { loadMockFixture, isMockMode }      from '../../shared/intake-client.js';
import { t, mountSwitcher, onLangChange }   from '../../shared/i18n.js';
import { $, escapeHtml, renderCenterCard, rankCenters } from '../heat-shared.js';

const state = { geo: null, zip: '' };

document.addEventListener('DOMContentLoaded', init);

function init() {
  mountSwitcher(document.querySelector('.heat-header'));
  onLangChange(() => {
    if (state.centers) render(state.centers);
  });

  wireGeo();
  $('search-btn').addEventListener('click', runSearch);
  // Auto-fetch on load so the page is useful even before the user taps anything.
  runSearch().catch(() => { /* error already surfaced */ });
}

function wireGeo() {
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
        `${t('geo.got')}: ${loc.lat.toFixed(4)}, ${loc.lon.toFixed(4)}`;
      runSearch();
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
}

async function runSearch() {
  const results = $('center-list');
  $('results').setAttribute('aria-busy', 'true');

  let fixture;
  try {
    // Mock mode is the only mode this page knows today — the lookup
    // endpoint is not yet wired in the agents/ orchestrator.
    fixture = await loadMockFixture('cooling_centers_lookup', 'heat');
  } catch (e) {
    results.innerHTML = `<li class="center"><p class="error-banner">${escapeHtml(e.message)}</p></li>`;
    $('results').setAttribute('aria-busy', 'false');
    return;
  }

  // If we have a GPS, re-rank by simulated distance; otherwise keep the
  // mock-supplied distance_km values. (Real backend uses ZIP -> centroid
  // and a haversine; both are stubs here.)
  const top5 = rankCenters(fixture.centers || []).slice(0, 5);
  state.centers = top5;
  render(top5);
  $('results').setAttribute('aria-busy', 'false');
}

function render(centers) {
  const list = $('center-list');
  if (!centers || centers.length === 0) {
    list.innerHTML = `<li class="center"><p>${escapeHtml(t('cooloff.list.empty'))}</p></li>`;
    return;
  }
  list.innerHTML = centers.map((c) => renderCenterCard(c)).join('');
}

if (isMockMode()) {
  console.info('[cool-off] running in mock mode — see app/heat/mock-responses.json');
}
