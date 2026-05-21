/* dashboard/shared/kg-client.js
 *
 * Vanilla fetch wrapper around the knowledge-graph-mcp HTTP transport
 * (see mcp/knowledge-graph-mcp/README.md -- MCP_TRANSPORT=streamable-http).
 *
 * Mock-by-default. The dashboard pages run on GitHub Pages and have no
 * backend, so every call falls back to a canned JSON payload under
 * dashboard/mock/. Flip to the real MCP HTTP transport by setting the
 * data-kg-base attribute on <body>:
 *
 *     <body data-kg-base="http://localhost:8765/mcp">
 *
 * When data-kg-base is set we POST a JSON-RPC envelope shaped after
 * the kg_sql / kg_nodes_by_type tool calls. When it isn't, we resolve
 * with the mock payload immediately.
 *
 * This module never executes SQL itself -- the dashboard renders
 * read-only previews; running the query is an explicit analyst action
 * that happens at the MCP boundary.
 */

const DEFAULT_MOCK_BASE = './mock';

function kgBase() {
  return document.body && document.body.dataset
    ? document.body.dataset.kgBase || null
    : null;
}

function mockBase() {
  // pages live at depth 1 (dashboard/<agency>/<page>.html), so the
  // mock folder is one directory up. The landing page (depth 0) reads
  // dashboard/mock/ directly. We detect by counting "../" in href.
  if (document.body && document.body.dataset && document.body.dataset.mockBase) {
    return document.body.dataset.mockBase;
  }
  // Default: relative path that walks back to dashboard/mock/.
  return DEFAULT_MOCK_BASE;
}

/**
 * Fetch a canned mock payload by filename (e.g. "cluster-feed.json").
 * @param {string} name
 * @returns {Promise<any>}
 */
export async function fetchMock(name) {
  const url = `${mockBase()}/${name}`;
  const res = await fetch(url, { headers: { 'accept': 'application/json' } });
  if (!res.ok) {
    throw new Error(`mock fetch failed: ${url} (${res.status})`);
  }
  return res.json();
}

/**
 * Call an MCP tool on the knowledge-graph-mcp HTTP transport.
 * Falls back to the named mock payload when no data-kg-base is set.
 *
 * @param {string} tool   e.g. "kg_nodes_by_type"
 * @param {object} args   per-tool arguments
 * @param {string} mockName fallback mock filename
 * @returns {Promise<any>}
 */
export async function callKgTool(tool, args, mockName) {
  const base = kgBase();
  if (!base) {
    return fetchMock(mockName);
  }
  const body = {
    jsonrpc: '2.0',
    id: Date.now(),
    method: 'tools/call',
    params: { name: tool, arguments: args || {} }
  };
  const res = await fetch(base, {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'accept': 'application/json' },
    body: JSON.stringify(body)
  });
  if (!res.ok) {
    throw new Error(`kg-mcp call failed: ${tool} (${res.status})`);
  }
  const payload = await res.json();
  if (payload.error) {
    throw new Error(`kg-mcp error: ${payload.error.message || payload.error}`);
  }
  return payload.result;
}

/**
 * Render a SQL statement as a read-only preview block. Never executes
 * the query. The caller wires a click handler to copy / open the
 * underlying observations elsewhere.
 *
 * @param {HTMLElement} mount
 * @param {string} sql
 * @param {string} [caption]
 */
export function renderSqlPreview(mount, sql, caption) {
  if (!mount) return;
  mount.innerHTML = '';
  const wrap = document.createElement('div');
  wrap.className = 'sql-preview';
  const h = document.createElement('h3');
  h.textContent = caption || 'Underlying SQL (preview only)';
  wrap.appendChild(h);
  const pre = document.createElement('pre');
  pre.textContent = sql.trim();
  wrap.appendChild(pre);
  const note = document.createElement('p');
  note.className = 'note';
  note.textContent =
    'This query is shown for transparency. The dashboard never executes ' +
    'SQL from the browser; analysts run it against the read-only ' +
    'knowledge-graph-mcp endpoint configured for their agency.';
  wrap.appendChild(note);
  mount.appendChild(wrap);
}

/**
 * Format an ISO timestamp into a short relative string ("3 h ago").
 * Useful for cluster-feed timestamps.
 */
export function timeAgo(iso, nowMs) {
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return iso;
  const now = nowMs || Date.now();
  const secs = Math.max(0, Math.round((now - t) / 1000));
  if (secs < 60)            return `${secs}s ago`;
  if (secs < 3600)          return `${Math.round(secs / 60)} min ago`;
  if (secs < 86400)         return `${Math.round(secs / 3600)} h ago`;
  if (secs < 86400 * 14)    return `${Math.round(secs / 86400)} d ago`;
  return new Date(iso).toISOString().slice(0, 10);
}
