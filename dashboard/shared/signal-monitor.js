/* dashboard/shared/signal-monitor.js
 *
 * Renders the statewide signal monitor from a privacy-safe ZCTA-week
 * aggregation exported out of the live DuckLake knowledge graph by
 * scripts/export_signals.py (-> dashboard/data/signals.json).
 *
 * Unlike the canned cluster-feed.js demo, this reads REAL aggregated counts
 * persisted by the intake write-path. It still honours the two load-bearing
 * rules:
 *
 *   1. Observation space only. A "signal" is an above-baseline count of a
 *      *category of report* (febrile/rash, gastrointestinal/food-safety,
 *      animal die-off/bite). It is NEVER labelled with a disease or pathogen.
 *      The dashboard surfaces "this place is reporting more X than expected";
 *      naming a cause is a downstream, human, agency act (Scenario D).
 *   2. ZCTA-week aggregations only — never an individual observation, never a
 *      precise location, never raw notes. Symptom cells are small-cell
 *      suppressed upstream.
 *
 * No backend: the page is static. It fetches the exported JSON snapshot.
 */

import { renderSparkline } from './sparkline.js';
import { renderSqlPreview } from './kg-client.js';

const DEFAULT_SRC = '../data/signals.json';

function srcUrl() {
  const ds = document.body && document.body.dataset;
  return (ds && ds.signalsSrc) || DEFAULT_SRC;
}

function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
}

function badge(extraClass, text) {
  return el('span', extraClass || null, text);
}

/** Fetch the exported snapshot. Throws on network / parse error. */
export async function loadSignals(url) {
  const res = await fetch(url || srcUrl(), { headers: { accept: 'application/json' } });
  if (!res.ok) throw new Error(`signals fetch failed (${res.status})`);
  return res.json();
}

/** Render the provenance line (where the data came from + when). */
export function renderProvenance(mount, data) {
  if (!mount) return;
  mount.innerHTML = '';
  const p = el('p', 'small muted');
  const gen = data._generated_at ? data._generated_at.slice(0, 16).replace('T', ' ') : '—';
  p.innerHTML =
    `<strong>${Number(data.total_observations || 0).toLocaleString()}</strong> ` +
    `reports aggregated &middot; data through <strong>${data.data_through || '—'}</strong> ` +
    `&middot; exported ${gen} UTC from the live DuckLake knowledge graph.`;
  mount.appendChild(p);
  const m = el('p', 'note', data.method || '');
  mount.appendChild(m);
}

/**
 * Render the signal feed as severity-laddered cards (reuses .cluster-card CSS).
 * @param {HTMLElement} mount  a <ul>
 * @param {object[]} signals
 */
export function renderSignalFeed(mount, signals) {
  if (!mount) return;
  mount.innerHTML = '';
  if (!signals || !signals.length) {
    const li = el('li', 'cluster-card');
    li.dataset.severity = 'info';
    li.appendChild(el('h3', null, 'No above-baseline signals'));
    li.appendChild(el('p', 'summary',
      'No ZCTA-week report category is currently exceeding its expected ' +
      'statewide share in the most recent window.'));
    mount.appendChild(li);
    return;
  }

  signals.forEach(s => {
    const li = el('li', 'cluster-card');
    li.dataset.severity = s.severity || 'info';

    li.appendChild(el('h3',
      null,
      `${s.recent_count} ${s.label.toLowerCase()} · ${s.place}` +
      ` · last ${s.recent_window_days} d`));

    if (s.blurb) li.appendChild(el('p', 'summary', s.blurb));

    const meta = el('div', 'meta');
    meta.appendChild(badge('severity-badge', (s.severity || 'info').toUpperCase()));
    if (s.county) meta.appendChild(badge(null, `Geo: ${s.county} County`));
    meta.appendChild(badge(null, `ZCTAs: ${(s.zctas || []).join(', ')}`));
    meta.appendChild(badge(null, `observed n=${s.recent_count}`));
    meta.appendChild(badge(null, `expected ≈${s.expected_count}`));
    meta.appendChild(badge(null, `exceedance z=${s.exceedance_z}`));
    li.appendChild(meta);

    // Observation-space symptom categories (already small-cell suppressed).
    const sym = s.top_symptom_categories || {};
    const keys = Object.keys(sym);
    if (keys.length) {
      const sline = el('p', 'small');
      sline.innerHTML = '<strong>Reported symptom categories:</strong> ' +
        keys.map(k => `${k.replace(/_/g, ' ')} (${sym[k]})`).join(', ');
      li.appendChild(sline);
    }

    // The load-bearing disclaimer, on every card.
    const dx = el('p', 'note');
    dx.textContent =
      'Routing signal only — a count of what was reported, not a diagnosis. ' +
      'No disease or cause is inferred or asserted.';
    li.appendChild(dx);

    mount.appendChild(li);
  });
}

/**
 * Render the ZCTA-week count matrix as an analyst table with sparklines.
 * @param {HTMLElement} tbody
 * @param {object[]} matrix  rows of {zcta, place, label, weeks, counts}
 */
export function renderMatrixTable(tbody, matrix) {
  if (!tbody) return;
  tbody.innerHTML = '';
  (matrix || []).forEach(row => {
    const tr = document.createElement('tr');
    tr.appendChild(el('td', null, row.zcta));
    tr.appendChild(el('td', null, row.place));
    tr.appendChild(el('td', null, row.label));

    const total = (row.counts || []).reduce((a, b) => a + b, 0);
    const recent = (row.counts || []).slice(-2).reduce((a, b) => a + b, 0);
    const tdTotal = el('td', 'num', String(total));
    const tdRecent = el('td', 'num', String(recent));
    tr.appendChild(tdRecent);
    tr.appendChild(tdTotal);

    const tdSpark = el('td', 'spark');
    const lastWeek = (row.weeks || []).slice(-1)[0] || '';
    tdSpark.appendChild(renderSparkline(row.counts || [], {
      title: `${row.label} in ${row.zcta}: ${(row.counts || []).join(', ')} ` +
             `(weekly, through ${lastWeek})`,
    }));
    tr.appendChild(tdSpark);

    tbody.appendChild(tr);
  });
}

/** Wire the "Show SQL preview" button to reveal the aggregation query. */
export function wireSqlPreview(button, mount) {
  if (!button || !mount) return;
  const sql = `
-- The aggregation behind this dashboard (run by scripts/export_signals.py
-- against the read-only knowledge-graph-mcp endpoint). ZCTA-week counts of
-- REPORT CATEGORIES only — no observation rows, no precise location, no
-- disease label.
WITH obs AS (
  SELECT n.node_id,
         MAX(p.value_text) FILTER (WHERE p.key='event_class') AS event_class,
         MAX(p.value_text) FILTER (WHERE p.key='coarse_zip')  AS zip,
         MAX(p.value_text) FILTER (WHERE p.key='event_date')  AS event_date
  FROM kg.node n JOIN kg.property p USING(node_id)
  WHERE n.node_type = 'observation'
  GROUP BY n.node_id
)
SELECT zip,
       date_trunc('week', CAST(event_date AS DATE)) AS week,
       CASE
         WHEN event_class IN ('human.fever_chills','human.rash_or_bite')
              THEN 'febrile_or_rash'
         WHEN event_class IN ('human.gastrointestinal','env.food_safety')
              THEN 'gi_or_food'
         WHEN event_class IN ('animal.dead_wildlife','animal.mass_die_off',
              'animal.dead_livestock','animal.sick_unusual_behaviour',
              'human.animal_bite_scratch') THEN 'animal_dieoff_or_bite'
       END AS signal_group,
       count(*) AS n
FROM obs
WHERE zip IS NOT NULL AND signal_group IS NOT NULL
GROUP BY 1, 2, 3
ORDER BY week DESC, n DESC;`;
  let shown = false;
  button.addEventListener('click', () => {
    shown = !shown;
    if (shown) {
      renderSqlPreview(mount, sql, 'ZCTA-week aggregation (preview only)');
      button.textContent = 'Hide SQL preview';
    } else {
      mount.innerHTML = '';
      button.textContent = 'Show SQL preview';
    }
  });
}

/** One-call bootstrap for the signals page. */
export async function mountSignalMonitor(opts) {
  const o = opts || {};
  try {
    const data = await loadSignals(o.src);
    renderProvenance(o.provenanceMount, data);
    renderSignalFeed(o.feedMount, data.signals);
    renderMatrixTable(o.tableBody, data.zcta_week_matrix);
    if (o.sqlButton) wireSqlPreview(o.sqlButton, o.sqlMount);
    return data;
  } catch (err) {
    if (o.feedMount) {
      o.feedMount.innerHTML =
        `<li class="cluster-card" data-severity="info">` +
        `<h3>Signal monitor unavailable</h3>` +
        `<p class="summary">${String(err.message)}</p>` +
        `<p class="note">Run <code>scripts/export_signals.py</code> to ` +
        `regenerate <code>dashboard/data/signals.json</code>.</p></li>`;
    }
    throw err;
  }
}
