/* dashboard/shared/cluster-feed.js
 *
 * Polls the Cluster Detection Agent feed (plan/03-agentic-architecture.md
 * #cluster-detection) and renders the top-N most recent cluster events
 * scoped to a given audience.
 *
 * Data shape per row (see mock/cluster-feed.json):
 *
 *   {
 *     "cluster_id": "cluster.coconino_hantavirus_2026w19",
 *     "kg_node_id": "cluster.coconino_hantavirus_2026w19",
 *     "title":       "4 hantavirus-compatible obs / Coconino / 10 d",
 *     "summary":     "Spatial-temporal cluster ...",
 *     "severity":    "alert",            // info | watch | alert | urgent
 *     "audiences":   ["adhs", "coconino"],
 *     "county":      "Coconino",
 *     "pathogen":    "hantavirus",
 *     "count":       4,
 *     "detected_at": "2026-05-17T07:00:00Z",
 *     "observation_query": "SELECT ... FROM kg.node WHERE ..."
 *   }
 *
 * The detection agent does the actual scan-statistic math (Kulldorff,
 * EARS C1/C2/C3, or the BYM2 spatial model depending on the vertical);
 * this module is the analyst-facing read of its output.
 */

import { fetchMock, timeAgo } from './kg-client.js';

const POLL_MS = 60 * 1000; // 60 s; configurable via data-poll-ms

/**
 * Mount the cluster-feed list and start polling.
 *
 * @param {HTMLElement} mount  <ul> or <div> to render into
 * @param {object} opts
 * @param {string} opts.audience          required ("adhs" | "mcdph" | ...)
 * @param {number} [opts.limit=5]
 * @param {string} [opts.mockName="cluster-feed.json"]
 * @returns {() => void} stop function
 */
export function mountClusterFeed(mount, opts) {
  if (!mount) return () => {};
  const audience = opts && opts.audience;
  const limit    = (opts && opts.limit) || 5;
  const mockName = (opts && opts.mockName) || 'cluster-feed.json';
  if (!audience) {
    throw new Error('mountClusterFeed: audience is required');
  }

  let stopped = false;

  async function tick() {
    try {
      const payload = await fetchMock(mockName);
      const rows = (payload.clusters || [])
        .filter(c => !c.audiences || c.audiences.indexOf(audience) >= 0)
        .sort((a, b) => new Date(b.detected_at) - new Date(a.detected_at))
        .slice(0, limit);
      render(mount, rows);
    } catch (err) {
      mount.innerHTML =
        `<li class="cluster-card" data-severity="info">` +
        `<h3>Cluster feed unavailable</h3>` +
        `<p class="summary">${escapeHtml(err.message)}</p></li>`;
    }
  }

  tick();
  const id = setInterval(() => { if (!stopped) tick(); }, POLL_MS);
  return () => { stopped = true; clearInterval(id); };
}

function render(mount, rows) {
  mount.innerHTML = '';
  if (!rows.length) {
    const li = document.createElement('li');
    li.className = 'cluster-card';
    li.dataset.severity = 'info';
    li.innerHTML = `<h3>No active clusters</h3>` +
      `<p class="summary">The Cluster Detection Agent has not flagged ` +
      `anything for your scope in the current polling window.</p>`;
    mount.appendChild(li);
    return;
  }

  rows.forEach(r => {
    const li = document.createElement('li');
    li.className = 'cluster-card';
    li.dataset.severity = r.severity || 'info';
    if (r.kg_node_id) li.dataset.kgNodeId = r.kg_node_id;

    const h = document.createElement('h3');
    h.textContent = r.title || r.cluster_id;
    li.appendChild(h);

    if (r.summary) {
      const p = document.createElement('p');
      p.className = 'summary';
      p.textContent = r.summary;
      li.appendChild(p);
    }

    const meta = document.createElement('div');
    meta.className = 'meta';
    meta.appendChild(badge('severity-badge', (r.severity || 'info').toUpperCase()));
    if (r.county)   meta.appendChild(badge(null, `Geo: ${r.county}`));
    if (r.pathogen) meta.appendChild(badge(null, `Focus: ${r.pathogen}`));
    if (typeof r.count === 'number') meta.appendChild(badge(null, `n=${r.count}`));
    if (r.detected_at) meta.appendChild(badge(null, timeAgo(r.detected_at)));
    li.appendChild(meta);

    if (r.kg_node_id) {
      const kg = document.createElement('span');
      kg.className = 'kg-id';
      kg.textContent = r.kg_node_id;
      li.appendChild(kg);
    }
    mount.appendChild(li);
  });
}

function badge(extraClass, text) {
  const s = document.createElement('span');
  if (extraClass) s.className = extraClass;
  s.textContent = text;
  return s;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}
