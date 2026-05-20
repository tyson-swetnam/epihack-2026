# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

EpiHack Arizona 2026 — the **AZ One Health Sentinel** stack. Four loosely-coupled components share one origin:

| Component | Stack | What it does |
|---|---|---|
| `app/` | Next.js 14 + React 18 + TS, static-exported | Mobile-first anonymous reporting app (tick / heat / cool-off). Published at `/epihack-2026/app/`. |
| `agents/` | Python 3.11 + Pydantic v2 + FastAPI + `anthropic` + `mcp` | Eight-agent orchestrator (Intake → Geo → Validation → Triage → Enrichment → Notification + Cluster + KnowledgeUpdate). Also serves `api/openapi.yaml`. |
| `mcp/<name>-mcp/` | FastMCP + httpx + Pydantic v2, one uv workspace per server | Eleven MCP servers wrapping VectorSurv, NWS HeatRisk, MAG HRN, ADHS, 211 AZ, WHISPers, iNaturalist, Great AZ Tick Check, wearable, SMS, and a read-only DuckDB query MCP. |
| `dashboard/`, `map/`, `graph/`, `figures/`, focus-group dirs | Vanilla HTML + ES modules + one CSS file, **no bundler** | Jekyll-rendered site at `/epihack-2026/`. MapLibre + Cytoscape via unpkg, pinned. |

The knowledge graph itself lives in `schema/*.sql` + `schema/deep/*.sql`, loaded into **DuckDB-on-DuckLake-on-Postgres** (DuckLake = open lakehouse, catalog in Postgres). The graph is property-graph–shaped: `kg.node`, `kg.edge`, `kg.property`.

## Architectural rules that span multiple files

- **`api/openapi.yaml` is the source of truth** for the HTTP contract between `app/` and `agents/`. Edit the spec first; `app/src/lib/api-types.ts` is *generated* (`npm run gen:api`) and `agents/src/onehealth_agents/api/models.py` is validated against it. Never hand-edit `api-types.ts`.
- **MCP tool names carry a server prefix.** `vectorsurv_*`, `kg_*`, `mag_*`, `az211_*`, `gattc_*`, `nws_*`, `whispers_*`, `inat_*`, `adhs_*`, `sms_*`, `wearable_*`. The orchestrator (`agents/src/onehealth_agents/mcp_client.py`) dispatches on the prefix — collisions silently break Scenario A/C/D.
- **Every knowledge-graph node has a stable dot-namespaced slug** (`pathogen.west_nile`, `county.maricopa`). Renames cascade through `agents/`, dashboards, and map/graph viewers. Coordinate in the PR.
- **Each `schema/deep/*.sql` seed owns a contiguous edge-ID range** (counties 10000-, tribes 11000-, pathogens 12000-, outbreaks 13000-, standards 14000-, datasets_apis 15000-, mcp_servers 16000-, application 17000-, followups 30000-). New seeds: pick the next free range, document in the PR.
- **SQL seed load order matters.** `standards.sql` and `pathogens.sql` must load before the rest of `schema/deep/*.sql` (SNOMED/ICD-10 and pathogen FKs).
- **The `kg_sql` escape hatch in `knowledge-graph-mcp` is SELECT-only by parser, not by convention.** Don't weaken that filter.

## Privacy contract (load-bearing — enforced in code, not just docs)

These rules are encoded in `agents/src/onehealth_agents/validation.py` (the single enforcement point) and in `api/openapi.yaml` schema constraints:

1. **No precise lat/lon over the wire.** `CoarseLocation` accepts `zip` or `grid_id` (1 km cell) only. Client coarsens via `app/src/lib/coarse-geo.ts`; server re-coarsens before persisting.
2. **EXIF GPS stripped before upload** (`app/src/lib/exif-stripper.ts`); server rejects with `photo_exif_gps_present` (422) if it slips through.
3. **Tribal data is suppressed by default.** Opt-in lives in `consent_profile` rows in the kg, consulted by ValidationAgent at write time.
4. **Triage is routing, not diagnosis.** A regex output-guard on the server rejects `you have …`, `you may have …`, `diagnos*`. The client renders only the `next_action` enum, never free-form LLM copy as a verdict.
5. **Audit log stores SHA-256 digests of canonicalized JSON, never raw observations.** No PII in `agent_run` rows.
6. **Cluster output uses ZCTA-week / ZCTA-2h aggregations**, never individual observations.

PRs touching `agents/`, `mcp/<server>/`, or `schema/deep/*.sql` must walk the checklist at the bottom of `CONTRIBUTING.md` or are blocked regardless of code review.

## Commands

### Knowledge graph bootstrap
```bash
duckdb
```
```sql
INSTALL ducklake; INSTALL postgres; LOAD ducklake; LOAD postgres;
ATTACH 'ducklake:postgres:dbname=epihack host=localhost user=epihack'
  AS epihack (DATA_PATH 's3://epihack/ducklake/');
USE epihack;
.read schema/knowledge_graph.sql
.read schema/system_designs.sql
.read schema/world_cafe.sql
.read schema/wildlife_vectors.sql
.read schema/heat.sql
.read schema/deep/standards.sql      -- must come first
.read schema/deep/pathogens.sql      -- must come second
.read schema/deep/counties.sql
.read schema/deep/tribes.sql
.read schema/deep/outbreaks.sql
.read schema/deep/datasets_apis.sql
.read schema/deep/application.sql
.read schema/deep/followups.sql
```

### Reporting app (`app/`)
```bash
cd app
npm install
npm run gen:api      # regenerate src/lib/api-types.ts from ../api/openapi.yaml
npm run dev          # localhost:3000; NEXT_PUBLIC_API_BASE=mock by default
npm run build        # writes out/ for static deploy
npm run typecheck    # tsc --noEmit
npm run lint
```

Point at a real backend: `NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run dev`.

### Agents / FastAPI backend (`agents/`)
```bash
cd agents
uv sync
ONEHEALTH_AUTH_MOCK=1 uv run uvicorn onehealth_agents.api:app --reload --port 8000

# Worked end-to-end scenarios against FakeMCPClient (no network):
uv run python examples/scenario_a_tick.py
uv run python examples/scenario_c_heat.py

# Tests (offline, no network):
uv run pytest
uv run pytest tests/test_orchestrator.py::test_scenario_a   # single test
```

### MCP servers (one uv workspace each)
```bash
cd mcp/vectorsurv-mcp && uv sync && uv run pytest
cd mcp/knowledge-graph-mcp && KG_DUCKDB_PATH=/path/to/epihack.duckdb uv run python -m knowledge_graph_mcp
```
Every server can run standalone via `python -m <package>`. Tests must pass offline (canned-data fallback on connection errors).

### Lint / format
```bash
uv run ruff check .
uv run black --check .
```
Python: line length 88, pytest-asyncio for async tests. **Tests must not hit the network** — use the per-server `canned_data.py` / `mock_data.py` or `respx`.

### Jekyll site (root)
```bash
bundle install
bundle exec jekyll serve     # localhost:4000/epihack-2026/
# or, for any vanilla-JS subdirectory (map/, graph/, dashboard/):
python -m http.server 8000
```

### OpenAPI spec validation
```bash
redocly lint api/openapi.yaml          # CI runs this on every spec change
redocly preview-docs api/openapi.yaml
```

### Self-host on a VM
```bash
cd ansible
cp inventory.example.yml inventory.yml          # edit ansible_host
cp group_vars/all.vault.example.yml group_vars/all.vault.yml
ansible-vault encrypt group_vars/all.vault.yml
ansible-galaxy install -r requirements.yml
ansible-playbook -i inventory.yml playbook.yml --ask-vault-pass
```

## Deployment

Two GitHub Actions workflows publish to **one** `gh-pages` branch with `keep_files: true`:

- `.github/workflows/deploy-jekyll.yml` — builds the Jekyll root site; triggers on any push except `app/**`, `api/**`.
- `.github/workflows/deploy-app.yml` — builds `app/` and lands it under `gh-pages:/app/`; triggers on `app/**` or `api/openapi.yaml`.

`_config.yml` **excludes** `app/`, `api/`, and `agents/` from Jekyll — those are built separately. Don't add Jekyll frontmatter to files under those directories.

## Conventions worth knowing before editing

- **No bundlers** for `dashboard/`, `map/`, `graph/`, focus-group viewers, or `app/legacy/`. Plain ES modules from the same origin. Third-party JS only via pinned unpkg URLs (MapLibre, Cytoscape).
- **One PR per concern**, ~200-line diffs. Reviewers will ask to split anything larger.
- **Adding an MCP server**: copy `mcp/vectorsurv-mcp/` as the template. Register in (1) `mcp/README.md` index, (2) `schema/deep/mcp_servers.sql`, (3) `plan/02-mcp-integration.md`, and (4) `agents/src/onehealth_agents/mcp_client.py` if any agent will call it.
- **Adding a kg seed**: copy `schema/deep/pathogens.sql`. Cite every fact inline (`-- source: <URL>`). Use `value_text` / `value_num` / `value_json` consistently — lat/lon and ordinals go in `value_num`.
- **MCP credentials are env-var only.** `.env` is gitignored; each server has a `.env.example`.
- **Tribal-data MCP servers need a sunset clause** in `pyproject.toml` description and a `MOU_RENEWED_THROUGH` env-var refusal in `__main__.py`. See `GOVERNANCE.md`.

## Where to look first

- **Plan & roadmap**: `plan/` (numbered 01-07 + EXECUTION-STATUS-*.md). `plan/03-agentic-architecture.md` for the eight-agent contract; `plan/04-data-flows.md` for the four worked scenarios A/B/C/D; `plan/06-mobile-app.md` for the privacy contract; `plan/07-auth.md` for Supabase auth.
- **What's wired vs. what's stubbed**: `plan/EXECUTION-STATUS.md` and `plan/EXECUTION-STATUS-PHASE-1-2.md` track shipped components, MCP tool inventory, and known follow-ups (slug mismatches, missing SNOMED/LOINC codes, etc.).
- **Governance, security, contributing**: `GOVERNANCE.md` (review board, tribal-partner veto, sunset clauses), `SECURITY.md` (five-class threat model), `CONTRIBUTING.md` (PR workflow + privacy checklist).
