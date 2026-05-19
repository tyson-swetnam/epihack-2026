---
title: "Contributing to EpiHack Arizona 2026"
---

# Contributing

Thanks for wanting to extend the EpiHack Arizona 2026 One Health
Sentinel stack. This repository was bootstrapped during the EpiHack
Arizona 2026 event hosted by the Ending Pandemics Academy and the
University of Arizona Global Health Institute, and is now maintained
by a multi-agency review board (see [GOVERNANCE.md](./GOVERNANCE.md))
for continued community use.

The repo is intentionally small, agent-friendly, and bundler-free.
Most of what you need to know lives in the file paths themselves;
this guide just calls out the conventions reviewers expect.

> Before opening any PR that touches **observation data** (anything
> flowing through `agents/`, `mcp/<server>/`, or `schema/deep/*.sql`)
> walk the [Privacy + data-sovereignty checklist](#privacy--data-sovereignty-checklist)
> at the bottom of this file. PRs that fail the checklist are blocked
> regardless of code-review status.

## Local environment setup

Everything runs on a laptop. There is no Kubernetes, no Docker
compose, no build step.

```bash
# 1. Python 3.11+ (3.11 is the floor; 3.12 works)
python3.11 --version

# 2. uv (https://docs.astral.sh/uv/) for per-package envs
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. duckdb CLI for the knowledge graph
#    https://duckdb.org/docs/installation/
duckdb --version
```

### Per-package install

Each `mcp/<server>/` and the `agents/` package are independent uv
workspaces with their own `pyproject.toml`. Install only what you
need:

```bash
cd mcp/vectorsurv && uv sync                      # any MCP server
cd agents          && uv sync                     # orchestrator
cd mcp/knowledge-graph-mcp && uv sync             # kg query server
```

### Static site (figures, map, graph, dashboard, today, app)

The site has no JS bundler. Open from the repo root:

```bash
cd /path/to/epihack-2026
python -m http.server 8000
# then visit http://localhost:8000/
```

GitHub Pages serves the same files with Jekyll; the `_config.yml`
preserves the directory layout.

### Knowledge-graph bootstrap

```bash
duckdb
```

```sql
INSTALL ducklake;  INSTALL postgres;
LOAD    ducklake;  LOAD    postgres;
ATTACH 'ducklake:postgres:dbname=epihack host=localhost user=epihack'
  AS epihack (DATA_PATH 's3://epihack/ducklake/');
USE epihack;
.read schema/knowledge_graph.sql
.read schema/system_designs.sql
.read schema/world_cafe.sql
.read schema/wildlife_vectors.sql
.read schema/heat.sql
.read schema/deep/standards.sql        -- load first
.read schema/deep/pathogens.sql        -- load second
.read schema/deep/counties.sql
.read schema/deep/tribes.sql
.read schema/deep/outbreaks.sql
.read schema/deep/datasets_apis.sql
.read schema/deep/application.sql
.read schema/deep/followups.sql
```

Load order matters: `standards.sql` and `pathogens.sql` must precede
the rest of `deep/*.sql` so SNOMED/ICD-10 cross-references and
pathogen FKs find their parents.

## Pull-request workflow

* **One PR per concern.** Small, reviewable, reversible. The current
  history runs at ~200-line diffs per PR; reviewers will ask you to
  split anything larger.
* **Commits are often drafted by Claude Code.** The repo was bootstrapped
  with Claude Code sub-agents; most commit messages name a Claude-led
  change. Human-authored commits are equally welcome — just write them
  in the same style (imperative subject, scope first, then summary).
* **Every PR includes test results.** Paste the relevant `uv run pytest`
  or `python -m http.server` smoke output into the PR body. For
  MCP changes: tool count + test count. For schema changes: row counts
  before/after.
* **Update `plan/EXECUTION-STATUS-PHASE-1-2.md` when relevant.** Any
  PR that closes a roadmap item or unblocks a downstream agent should
  tick the corresponding line and add a `verification` cell.
* **Run linters before pushing** (see [Coding style](#coding-style)).

## Contribution templates

### Adding a new MCP server

Use [`mcp/vectorsurv/`](./mcp/vectorsurv/) as the template — it is the
most complete reference and follows every convention reviewers expect.

```
mcp/<your-server>/
├── README.md                  # what / why / tool table / auth / env vars
├── pyproject.toml             # FastMCP + httpx + pydantic v2; uv workspace
├── src/<your_server>/
│   ├── __init__.py
│   ├── __main__.py            # `python -m <your_server>` entry point
│   ├── server.py              # FastMCP() instance + @mcp.tool definitions
│   └── client.py              # httpx wrapper; env-overridable base URL
├── examples/
│   └── claude_desktop_config.json
└── tests/
    └── test_*.py              # uv run pytest
```

Required conventions:

* **Tool-name prefix.** Every tool name starts with a short server
  prefix (`vectorsurv_*`, `kg_*`, `mag_*`, `az211_*`, `gattc_*`,
  `nws_*`, `whispers_*`, `inat_*`, `adhs_*`, `sms_*`, `wearable_*`).
  The `agents/` orchestrator dispatches on the prefix; collisions
  silently break Scenario A/C/D end-to-end runs.
* **Env-overridable base URL.** Hard-coded URLs are a deploy blocker.
  Read from `os.environ.get("<SERVER>_BASE_URL")` with a sensible
  default. If the upstream has no API today (e.g. ADHS, MAG supply,
  211 dispatch, Great AZ Tick Check), ship a mock backend behind the
  same env-var contract so swapping is a one-line change.
* **Versioned OpenAPI snapshot.** If the upstream publishes an OpenAPI
  spec, drop a snapshot in `openapi/` and reference it from the
  README. PRs that bump the snapshot are the changelog the MCP client
  reacts to.
* **Pure-stdlib mock fallback.** Tests must run with no network. Put
  canned data in a sibling module (`canned_data.py` or `mock_data.py`)
  and silently fall back on connection errors.
* **Register the server in:**
  * [`mcp/README.md`](./mcp/README.md) — one row in the index table.
  * [`schema/deep/mcp_servers.sql`](./schema/deep/mcp_servers.sql) —
    a `mcp_server` node + per-tool nodes.
  * [`plan/02-mcp-integration.md`](./plan/02-mcp-integration.md) —
    if the server unlocks a new agent → MCP route.
  * `agents/src/onehealth_agents/mcp_client.py` — if any of the eight
    agents calls a tool on it.

### Adding a knowledge-graph schema seed

Use [`schema/deep/pathogens.sql`](./schema/deep/pathogens.sql) as the
template — it shows the full pattern (nodes → edges → properties →
cross-references → views).

Required conventions:

* **Stable slugs.** Node IDs are dot-namespaced (`pathogen.west_nile`,
  `county.maricopa`, `tribe.tohono_oodham`). Renames break every
  downstream join; coordinate via PR before renaming.
* **Reserve edge-ID ranges.** Each seed owns a contiguous edge-ID
  range to avoid collisions (`counties.sql` 10000-10999,
  `tribes.sql` 11000-11999, `pathogens.sql` 12000-12999,
  `outbreaks.sql` 13000-13999, `standards.sql` 14000-14999,
  `datasets_apis.sql` 15000-15999, `mcp_servers.sql` 16000-16999,
  `application.sql` 17000-17999, `followups.sql` 30000-30199, etc.).
  Pick the next free range and document it in your PR.
* **Cite every fact.** Inline `-- source: <URL or doc path>` comments
  on rows whose values came from a published agency report. Reviewers
  will ask for citations on anything that looks like a magic number.
* **Property values are typed.** Use `value_text`, `value_num`, or
  `value_json` consistently. Lat/lon, ordinals, counts go in
  `value_num`. URLs, names, slugs go in `value_text`.
* **Update load order** in `README.md` and (where applicable)
  `mcp/knowledge-graph-mcp/` if your seed has FK dependencies on
  another seed.

## Coding style

* **No bundlers.** All client JS is vanilla ES modules served from the
  same origin. The only third-party JS we load are MapLibre GL and
  Cytoscape, both from unpkg pinned to a major.minor.patch.
* **Vanilla ES modules** with native `import` / `export`. No JSX, no
  TypeScript, no transpilation. Files end in `.js` and run in modern
  browsers untouched.
* **Python: pydantic v2 + FastMCP.** Every MCP server uses the FastMCP
  decorator API. Request/response models are pydantic v2
  `BaseModel`s. Async via `httpx.AsyncClient`.
* **Format: `black` defaults + `ruff` defaults.** Run
  `uv run ruff check .` and `uv run black --check .` before pushing.
  Line length defaults (88 / 88). One module per concern.
* **Tests: pytest + pytest-asyncio.** Test files live in `tests/`,
  named `test_<unit>.py`. Async tests use the `pytest.mark.asyncio`
  decorator. Network is forbidden in unit tests — use the canned
  fallback or `respx` mocks.

## Privacy + data-sovereignty checklist

Walk this on every PR that touches observation data. If any box
fails, the PR is blocked.

- [ ] **No tribal data writes by default.** If the code paths touch
  tribal lands (`tribe.*` nodes, ZCTAs intersecting a reservation),
  the default behaviour is suppression. Opt-in is per-tribe and
  per-data-source, configured in `consent_profile` rows in the kg.
- [ ] **`consent_profile` is consulted at write time.** Validation
  Agent (`agents/src/onehealth_agents/validation.py`) is the single
  enforcement point. Bypassing it is a hard reviewer-block.
- [ ] **No raw line data in shared dashboards.** Anything reaching
  `dashboard/` or `today/` has been aggregated or suppressed per the
  rules in `plan/03-agentic-architecture.md`.
- [ ] **No PII in logs or `agent_run` rows.** The audit log captures
  input/output **digests** (SHA-256 of canonicalized JSON), never raw
  observations.
- [ ] **MCP credentials are env-var only.** No tokens, API keys, or
  agency credentials in source. The `.env.example` next to each MCP
  server documents what is required; the `.env` itself is
  `.gitignore`d.
- [ ] **SELECT-only escape hatches stay SELECT-only.** The
  `knowledge-graph-mcp` `kg_sql` tool parses for write keywords and
  rejects them; do not weaken that filter.
- [ ] **MOU expiry is honoured.** Any new MCP server that proxies a
  tribal data source has a sunset comment naming the MOU it depends
  on (see [GOVERNANCE.md](./GOVERNANCE.md) sunset clauses).
- [ ] **Re-identification risk is reviewed.** Cell counts below
  agreed thresholds are suppressed in dashboards; cluster-detection
  output uses ZCTA-week / ZCTA-2h aggregations, never individual
  observations.

If you are unsure whether your change crosses any of these lines, ask
in the PR description — a reviewer from the standing board will weigh
in (see [GOVERNANCE.md](./GOVERNANCE.md)).
