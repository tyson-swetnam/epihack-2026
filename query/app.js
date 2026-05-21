// EpiHack Arizona 2026 — DuckDB-WASM viewer bootstrap.
//
// Loads DuckDB entirely in the browser, rebuilds the kg.node / kg.edge /
// kg.property property-graph from the same schema/*.sql seeds that feed the
// DuckLake catalog, and runs read-only SQL. Nothing leaves the page.
//
// No bundler: pinned ESM from jsDelivr (DuckDB-WASM ships its own worker +
// wasm bundle locations via getJsDelivrBundles()). Matches the unpkg-pinned
// convention used by map/ (MapLibre) and graph/ (Cytoscape).

import * as duckdb from "https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.29.0/+esm";

// Seed load order mirrors the bootstrap block in CLAUDE.md:
// standards.sql + pathogens.sql must precede the other deep seeds.
const SEED_FILES = [
  "../schema/knowledge_graph.sql",
  "../schema/system_designs.sql",
  "../schema/world_cafe.sql",
  "../schema/wildlife_vectors.sql",
  "../schema/heat.sql",
  "../schema/deep/standards.sql",
  "../schema/deep/pathogens.sql",
  "../schema/deep/counties.sql",
  "../schema/deep/tribes.sql",
  "../schema/deep/outbreaks.sql",
  "../schema/deep/datasets_apis.sql",
  "../schema/deep/mcp_servers.sql",
  "../schema/deep/application.sql",
  "../schema/deep/followups.sql",
  "../schema/deep/audit.sql",
  "../schema/deep/cluster_followups.sql",
  "../schema/deep/outbreaks_near_me.sql",
];

// We pre-create the three core kg tables WITHOUT the foreign keys the seeds
// declare, so the in-browser load is order-tolerant. The seeds' own
// `CREATE TABLE IF NOT EXISTS kg.*` then become no-ops, while auxiliary tables
// (design_answer, agent_run, …) are still created by their files.
const CORE_TABLES = `
CREATE SCHEMA IF NOT EXISTS kg;
CREATE TABLE IF NOT EXISTS kg.node (
  node_id     VARCHAR PRIMARY KEY,
  node_type   VARCHAR,
  label       VARCHAR,
  description VARCHAR,
  source_fig  VARCHAR,
  created_at  TIMESTAMP DEFAULT current_timestamp
);
CREATE TABLE IF NOT EXISTS kg.edge (
  edge_id    BIGINT PRIMARY KEY,
  subject_id VARCHAR,
  predicate  VARCHAR,
  object_id  VARCHAR,
  source_fig VARCHAR
);
CREATE TABLE IF NOT EXISTS kg.property (
  node_id    VARCHAR,
  key        VARCHAR,
  value_text VARCHAR,
  value_num  DOUBLE,
  PRIMARY KEY (node_id, key)
);
`;

const els = {
  status: document.getElementById("status"),
  catalog: document.getElementById("catalog"),
  editor: document.getElementById("editor"),
  run: document.getElementById("run"),
  download: document.getElementById("download"),
  meta: document.getElementById("meta"),
  results: document.getElementById("results"),
};

let conn = null;
let lastResult = null; // { cols, rows } for CSV export

function setStatus(msg, kind = "info") {
  els.status.textContent = msg;
  els.status.className = "status " + kind;
}

// --- SELECT-only guard --------------------------------------------------------
// Mirrors the kg_sql escape hatch in knowledge-graph-mcp: read paths only.
const READONLY_HEAD = /^(select|with|explain|describe|summarize|pragma|show)\b/i;
const FORBIDDEN = /\b(insert|update|delete|drop|create|alter|attach|detach|copy|export|install|load|set|call|truncate|replace|grant|revoke|vacuum|checkpoint)\b/i;

function guard(sql) {
  // strip line + block comments before inspecting
  const bare = sql
    .replace(/--[^\n]*/g, " ")
    .replace(/\/\*[\s\S]*?\*\//g, " ")
    .trim();
  if (!bare) throw new Error("Empty query.");
  if (!READONLY_HEAD.test(bare))
    throw new Error("Read-only viewer: queries must begin with SELECT / WITH / EXPLAIN.");
  if (FORBIDDEN.test(bare))
    throw new Error("Read-only viewer: write/DDL statements are blocked.");
  if (bare.includes(";") && bare.replace(/;\s*$/, "").includes(";"))
    throw new Error("Run one statement at a time.");
  return bare.replace(/;\s*$/, "");
}

// --- SQL splitter for seed loading -------------------------------------------
// Single-quote strings (with '' escape), -- line comments and /* */ blocks.
function splitSql(text) {
  const out = [];
  let buf = "";
  let inStr = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i], c2 = text[i + 1];
    if (inStr) {
      buf += c;
      if (c === "'") {
        if (c2 === "'") { buf += c2; i++; }
        else inStr = false;
      }
      continue;
    }
    if (c === "-" && c2 === "-") { while (i < text.length && text[i] !== "\n") i++; continue; }
    if (c === "/" && c2 === "*") { i += 2; while (i < text.length && !(text[i] === "*" && text[i + 1] === "/")) i++; i++; continue; }
    if (c === "'") { inStr = true; buf += c; continue; }
    if (c === ";") { const s = buf.trim(); if (s) out.push(s); buf = ""; continue; }
    buf += c;
  }
  const tail = buf.trim();
  if (tail) out.push(tail);
  return out;
}

// --- result rendering ---------------------------------------------------------
function fmt(v) {
  if (v === null || v === undefined) return "";
  if (typeof v === "bigint") return v.toString();
  return String(v);
}

function render(table) {
  const { cols, rows } = table;
  if (!rows.length) {
    els.results.innerHTML = '<p class="empty">Query ran — 0 rows.</p>';
    return;
  }
  const head = cols.map((c) => `<th>${escapeHtml(c)}</th>`).join("");
  const body = rows
    .map(
      (r) =>
        "<tr>" +
        cols.map((c) => `<td>${escapeHtml(fmt(r[c]))}</td>`).join("") +
        "</tr>"
    )
    .join("");
  els.results.innerHTML = `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

function escapeHtml(s) {
  return s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function toCSV(table) {
  const esc = (v) => {
    const s = fmt(v);
    return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  const lines = [table.cols.join(",")];
  for (const r of table.rows) lines.push(table.cols.map((c) => esc(r[c])).join(","));
  return lines.join("\n");
}

// --- run a user query ---------------------------------------------------------
async function runQuery() {
  if (!conn) { setStatus("Database still loading…", "info"); return; }
  let sql;
  try {
    sql = guard(els.editor.value);
  } catch (e) {
    setStatus(e.message, "error");
    return;
  }
  els.run.disabled = true;
  setStatus("Running…", "info");
  const t0 = performance.now();
  try {
    const res = await conn.query(sql);
    const cols = res.schema.fields.map((f) => f.name);
    const rows = res.toArray().map((r) => {
      const o = r.toJSON();
      for (const k of Object.keys(o)) if (typeof o[k] === "bigint") o[k] = o[k];
      return o;
    });
    lastResult = { cols, rows };
    render(lastResult);
    const ms = (performance.now() - t0).toFixed(0);
    els.meta.textContent = `${rows.length} row${rows.length === 1 ? "" : "s"} · ${ms} ms`;
    els.download.disabled = rows.length === 0;
    setStatus("Ready", "ok");
  } catch (e) {
    els.results.innerHTML = "";
    els.meta.textContent = "";
    els.download.disabled = true;
    setStatus("SQL error: " + e.message, "error");
  } finally {
    els.run.disabled = false;
  }
}

// --- catalog ------------------------------------------------------------------
function buildCatalog() {
  const byCat = new Map();
  for (const q of window.EPIHACK_QUERIES) {
    if (!byCat.has(q.category)) byCat.set(q.category, []);
    byCat.get(q.category).push(q);
  }
  for (const [cat, list] of byCat) {
    const h = document.createElement("h3");
    h.textContent = cat;
    els.catalog.appendChild(h);
    for (const q of list) {
      const b = document.createElement("button");
      b.className = "q";
      b.innerHTML = `<span class="q-name">${escapeHtml(q.name)}</span><span class="q-desc">${escapeHtml(q.desc)}</span>`;
      b.addEventListener("click", () => {
        els.editor.value = q.sql;
        runQuery();
        if (window.matchMedia("(max-width: 820px)").matches)
          els.editor.scrollIntoView({ behavior: "smooth" });
      });
      els.catalog.appendChild(b);
    }
  }
}

// --- bootstrap ----------------------------------------------------------------
async function boot() {
  buildCatalog();
  els.editor.value = window.EPIHACK_QUERIES[0].sql;

  els.run.addEventListener("click", runQuery);
  els.editor.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); runQuery(); }
  });
  els.download.addEventListener("click", () => {
    if (!lastResult) return;
    const blob = new Blob([toCSV(lastResult)], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "epihack-query.csv";
    a.click();
    URL.revokeObjectURL(url);
  });

  try {
    setStatus("Loading DuckDB-WASM…", "info");
    const bundles = duckdb.getJsDelivrBundles();
    const bundle = await duckdb.selectBundle(bundles);
    const workerUrl = URL.createObjectURL(
      new Blob([`importScripts("${bundle.mainWorker}");`], { type: "text/javascript" })
    );
    const worker = new Worker(workerUrl);
    const db = new duckdb.AsyncDuckDB(new duckdb.ConsoleLogger(duckdb.LogLevel.WARNING), worker);
    await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
    URL.revokeObjectURL(workerUrl);
    conn = await db.connect();

    await conn.query(CORE_TABLES);

    let nStmts = 0;
    for (let i = 0; i < SEED_FILES.length; i++) {
      const file = SEED_FILES[i];
      setStatus(`Loading knowledge graph… (${i + 1}/${SEED_FILES.length})`, "info");
      const resp = await fetch(file);
      if (!resp.ok) throw new Error(`fetch ${file} → ${resp.status}`);
      const stmts = splitSql(await resp.text());
      for (const s of stmts) {
        try { await conn.query(s); nStmts++; }
        catch (e) { console.warn(`seed stmt failed in ${file}:`, e.message); }
      }
    }

    const counts = await conn.query(
      "SELECT (SELECT COUNT(*) FROM kg.node) AS nodes, (SELECT COUNT(*) FROM kg.edge) AS edges, (SELECT COUNT(*) FROM kg.property) AS props"
    );
    const c = counts.toArray()[0].toJSON();
    setStatus(`Loaded ${c.nodes} nodes · ${c.edges} edges · ${c.props} properties. Ready.`, "ok");
    runQuery();
  } catch (e) {
    setStatus("Failed to load DuckDB: " + e.message, "error");
    console.error(e);
  }
}

boot();
