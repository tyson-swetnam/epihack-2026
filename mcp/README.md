---
title: "MCP servers — index"
---

# MCP servers

This directory holds the family of Model Context Protocol servers
that the EpiHack Arizona 2026 stack uses to stream live (and, where
upstream APIs are absent, mock) agency data into an LLM client like
Claude Desktop or Claude Code, or into the agent pipeline under
[`agents/`](../agents/).

Eleven servers ship today. Every server follows the same shape:

* A `src/<package>/server.py` exposing a [FastMCP](https://gofastmcp.com/)
  `mcp` instance with `@mcp.tool` decorated handlers.
* A `src/<package>/client.py` that wraps the upstream HTTP API
  (or a canned-data fallback) with `httpx` + pydantic v2.
* A per-package `pyproject.toml` you can `uv sync` independently.
* A `README.md` documenting the tool table, env-var configuration,
  and the upstream's auth posture.
* A `tests/` directory that runs offline (`uv run pytest`).

## Index

| Server | Description | Tools | Auth posture | Tests |
|---|---|---:|---|---:|
| [`vectorsurv-mcp/`](./vectorsurv-mcp/) | VectorSurv national mosquito + tick surveillance API; pools, collections, agency-region intersects, vector-index math, case counts | 13 | Username + password → bearer (`VECTORSURV_USERNAME`, `VECTORSURV_PASSWORD`) with auto-refresh | 6 |
| [`knowledge-graph-mcp/`](./knowledge-graph-mcp/) | Read-only DuckDB query MCP over the EpiHack DuckLake kg (572 nodes / 791 edges / 1027 properties); regions-at-point, pathogen-by-vector, outbreak check, SELECT-only SQL escape hatch | 12 | None — local DuckLake catalog via env path (`KG_DUCKDB_PATH`); SELECT-only SQL parser blocks all writes | 22 |
| [`great-az-tick-check-mcp/`](./great-az-tick-check-mcp/) | UA Cooperative Extension Great AZ Tick Check mail-in submission tracking + species feedback (mock backend by default) | 5 | Optional `GATTC_API_TOKEN` for a future real backend; defaults to mock-mode (no auth) | 10 |
| [`nws-heatrisk-mcp/`](./nws-heatrisk-mcp/) | NWS public API + WPC HeatRisk gridded product; current conditions, forecast, active alerts, heat-index calculation | 7 | None — public API; requires a polite `NWS_USER_AGENT` per NOAA guidance | 17 |
| [`mag-hrn-mcp/`](./mag-hrn-mcp/) | MAG Heat Relief Network cooling / hydration / respite / donation centers across Phoenix metro (May 1 – Sep 30); supply status tool is mock-only until MAG ships an occupancy feed | 5 | None — public ArcGIS Feature Service (`MAG_HRN_FEATURE_SERVICE_URL`); defaults to canned dataset of 12 Phoenix sites | 35 |
| [`adhs-mcp/`](./adhs-mcp/) | ADHS public surveillance summaries: heat mortality, arbovirus weekly summaries, reportable conditions (no public REST API today — canned data drawn from ADHS PDFs + ArcGIS dashboards) | 6 | Optional `ADHS_API_TOKEN` for a future real backend; mock-by-default | 46 |
| [`211-az-mcp/`](./211-az-mcp/) | 211 Arizona referrals + cooling-center referrals + transport dispatch with in-memory chain-of-call tracking | 6 | Optional `AZ211_API_KEY` + `AZ211_BACKEND_URL` for a future real backend; mock-by-default | 23 |
| [`whispers-mcp/`](./whispers-mcp/) | USGS WHISPers wildlife mortality events; public read-only listing tools with canned-fallback on network errors | 6 | None for the public listing tools (`WHISPERS_BASE_URL`); env-overridable + silent canned fallback | 15 |
| [`inaturalist-mcp/`](./inaturalist-mcp/) | iNaturalist citizen-science observations (AZ `place_id=53`); ticks, mosquitoes, fleas, rodent reservoirs | 6 | None — public iNaturalist API; requires `INAT_USER_AGENT` per iNat guidance | 8 |
| [`sms-entry-mcp/`](./sms-entry-mcp/) | SMS-only intake adapter; pure-function Twilio HMAC-SHA1 signature check, normalisation, intent parsing | 6 | Optional `SMS_TWILIO_AUTH_TOKEN` for the gateway service; `SMS_MODE=mock` by default | 19 |
| [`wearable-mcp/`](./wearable-mcp/) | HealthKit / Health Connect wearable readings (skin temp, HRV, sweat rate, heart rate); on-device-only privacy posture, mock-by-default | 4 | None — readings stay on-device; mock profiles (`rest`, `heat`) ship inline | 23 |

Tool and test counts are sourced from each server's README and its
`tests/` directory; bumps land in the same PR that ships the change.

## How to add a new MCP server

Use [`vectorsurv-mcp/`](./vectorsurv-mcp/) as the template — it is the most
complete reference in the family and follows every convention
reviewers expect.

### 1. Scaffold

```bash
cd mcp
cp -R vectorsurv-mcp my-new-server-mcp
cd my-new-server-mcp
# rename src/vectorsurv_mcp → src/my_new_server_mcp; update pyproject.toml
```

Target layout:

```
mcp/my-new-server/
├── README.md                  # what / why / tool table / auth / env vars
├── pyproject.toml             # FastMCP + httpx + pydantic v2; uv workspace
├── src/my_new_server_mcp/
│   ├── __init__.py
│   ├── __main__.py            # `python -m my_new_server_mcp` entry
│   ├── server.py              # FastMCP() instance + @mcp.tool definitions
│   └── client.py              # httpx wrapper; env-overridable base URL
├── examples/
│   └── claude_desktop_config.json
└── tests/
    └── test_*.py              # uv run pytest
```

### 2. Conventions reviewers will check

* **Prefix every tool name** with a short server prefix (`vectorsurv_`,
  `kg_`, `mag_`, `az211_`, `gattc_`, `nws_`, `whispers_`, `inat_`,
  `adhs_`, `sms_`, `wearable_`). The orchestrator at
  [`agents/src/onehealth_agents/mcp_client.py`](../agents/src/onehealth_agents/mcp_client.py)
  dispatches on the prefix; collisions silently break end-to-end
  scenarios.
* **Base URL via env var.** Hard-coded URLs are a deploy blocker. Read
  from `os.environ.get("<SERVER>_BASE_URL")` with a sensible default.
  If the upstream has no API today, ship a mock backend behind the
  same env-var contract.
* **Canned-data fallback for tests.** Tests must run with no network.
  Put canned data in a sibling module (`canned_data.py` /
  `mock_data.py`) and silently fall back on connection errors.
* **Versioned OpenAPI snapshot** if the upstream publishes one. Drop
  it in `openapi/` and reference it from the README. PRs that bump
  the snapshot are the changelog the client reacts to.
* **No credentials in source.** All tokens and keys read from
  `os.environ`. `.env.example` next to the server documents what is
  required; `.env` is `.gitignore`d.
* **Mock-by-default for any tool that proxies an unverified upstream.**
  Mark mock-only tools clearly in the README and in the FastMCP tool
  docstring so the LLM does not present mock data as authoritative.
* **Tribal-data proxies need a sunset clause** in `pyproject.toml`
  `description` and the README header naming the MOU the server
  depends on. The `__main__.py` entry must refuse to start past the
  MOU expiry date unless `MOU_RENEWED_THROUGH=<ISO-date>` is set in
  the environment. See [`GOVERNANCE.md`](../GOVERNANCE.md) sunset
  clauses.

### 3. Register the new server

Three places need an entry:

1. **This file** — add a row to the index table above with the tool
   count, auth posture, and test count.
2. **[`schema/deep/mcp_servers.sql`](../schema/deep/mcp_servers.sql)** —
   add a `mcp_server` node plus per-tool nodes, using the next free
   edge-id range.
3. **[`plan/02-mcp-integration.md`](../plan/02-mcp-integration.md)** —
   if the new server unlocks a new agent → MCP tool route.
4. **`agents/src/onehealth_agents/mcp_client.py`** — if any of the
   eight agents will call a tool on the new server, add the route +
   wire up the prefix.

### 4. Test plan in the PR

The PR description must include, at minimum:

* `cd mcp/my-new-server && uv run pytest` output (tool count + test
  count summary).
* A Claude Desktop config snippet (in `examples/claude_desktop_config.json`)
  and a screenshot or transcript showing the tools appear in the
  client.
* For servers that proxy an authenticated upstream: a redacted log
  showing a successful end-to-end call.

See [`CONTRIBUTING.md`](../CONTRIBUTING.md) for the full PR workflow
and the privacy + data-sovereignty checklist.
