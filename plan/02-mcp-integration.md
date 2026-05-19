---
title: "Plan 02 — MCP integration: APIs that feed the Minimum Dataset"
---

# 02 — MCP integration

The app speaks **MCP** to upstream agencies, not bespoke HTTP clients.
Each agency or data source gets one Model Context Protocol server;
the agents in [03-agentic-architecture](./03-agentic-architecture.html)
call them by name. New agency partners join the system by shipping a
server, not by negotiating bilateral integrations.

## MCP server inventory

| Server | Status | Backed by | Feeds vertical |
|---|---|---|---|
| [`vectorsurv-mcp`](../mcp/vectorsurv-mcp/) | ✅ shipped | api.vectorsurv.org (OpenAPI v1.0.44) | VBD |
| `nws-heatrisk-mcp` | ⏳ planned | api.weather.gov HeatRisk + alerts | Heat |
| `mag-hrn-mcp` | ⏳ planned | hrn.azmag.gov (cooling-center registry) | Heat |
| `adhs-mcp` | ⏳ planned | ADHS open-data (heat mortality, arbovirus reports) | Both |
| `great-az-tick-check-mcp` | ⏳ planned | UA Cooperative Extension submission tracker | VBD |
| `whispers-mcp` | ⏳ planned | USGS WHISPers wildlife mortality events | VBD |
| `inaturalist-mcp` | ⏳ planned | iNaturalist API (vectors + wildlife observations) | VBD |
| `211-az-mcp` | ⏳ planned | 211 Arizona resource directory | Heat |
| `knowledge-graph-mcp` | ⏳ planned | This repo's DuckLake graph (read + write) | Both |
| `outbreaks-near-me-mcp` | 🔭 future | Federation with Boston Children's [Outbreaks Near Me](https://outbreaksnearme.org/us/en-US) symptom-cluster platform (successor to Flu Near You). OBNM is the canonical human-symptom-side participatory-surveillance platform; this MCP would let the AZ agents pull symptom-cluster context for a user's ZIP and contribute Sentinel reports back upstream. Gated on a partnership with the HealthMap team. | Both |

## Parameter-by-parameter source map

Where each Minimum-Dataset parameter is allowed to be **populated
from upstream** (vs. always coming from the user):

### General class

| Param | Source | MCP |
|---|---|---|
| Geographical coordinates | Device GPS | — (client) |
| Postal code | Device GPS reverse-geocoded → county/tribe lookup | `knowledge-graph-mcp` (regions) |
| Date of report | App timestamp | — |
| Household member ID | User-entered | — |

### Human class — symptoms

Always user-supplied; the **Enrichment Agent** adds derived
context (e.g. SNOMED CT code, severity score) from
`schema/deep/standards.sql`. No MCP populates symptoms.

### Auxiliary class — digital biomarker

| Param | Source | MCP |
|---|---|---|
| Wearable skin-temp, HRV, sweat rate | HealthKit / Health Connect on device | — (client) — eventually `wearable-mcp` proxy |
| Photo | Camera | — |
| Lab confirmation | User-entered + (later) FHIR HL7 pull | future `fhir-mcp` |

### Environmental class — pulled live

This is where MCPs do the heavy lifting:

| Param | MCP | Endpoint |
|---|---|---|
| Ambient temperature | `nws-heatrisk-mcp` | api.weather.gov gridpoint forecast |
| Humidity | `nws-heatrisk-mcp` | same |
| Heat index | `nws-heatrisk-mcp` | computed client-side from T + RH |
| NWS HeatRisk level | `nws-heatrisk-mcp` | api.weather.gov/products/heatrisk |
| Active heat warning | `nws-heatrisk-mcp` | api.weather.gov/alerts/active |
| Vector density (mosquito) | `vectorsurv-mcp` | `vectorsurv_calculate_abundance` |
| Vector positivity (WNV pools) | `vectorsurv-mcp` | `vectorsurv_calculate_infection_rate` |
| Tick observations nearby | `inaturalist-mcp` | obs?taxon=Ixodida&lat=...&radius=... |
| Wildlife mortality events nearby | `whispers-mcp` | events?bbox=... |
| Standing water / recent rainfall | future `nws-precip-mcp` | precip grid |

### Livestock / Wildlife class — both user and MCP

| Param | MCP |
|---|---|
| Species ID (from photo) | `knowledge-graph-mcp` (taxonomy lookup) + Claude Vision |
| Number of sick/dead animals | User-entered |
| Date / location of incident | Device GPS + user |
| Cross-reference to current outbreak | `knowledge-graph-mcp` + `whispers-mcp` + `vectorsurv-mcp` |

## Cooling-center awareness (Heat-Q1) — multi-MCP join

Heat-Q1's "where can I cool off?" answer is a join across three
MCPs and the knowledge graph:

```
user_location  →  mag-hrn-mcp.search_centers(lat,lon,radius)
              →  211-az-mcp.utility_assistance_nearby(zip)
              →  knowledge-graph-mcp.match_focus_area("cooling_centers")
              →  knowledge-graph-mcp.population_priority(user.demographic)
              →  ranked list of {center, distance, services, transport_available}
```

The Notification Agent renders the result with the highest-priority
match (per the
[Q4 vulnerable-populations data](../heat/04-vulnerable-populations.html))
first.

## VBD triage (Wildlife-Q4) — multi-MCP join

A community VBD report goes through:

```
user_report   →  vectorsurv-mcp.list_test_targets()
                 (look up matching pathogen by symptom + vector)
              →  vectorsurv-mcp.get_pools(near user.county, last 30 days)
                 (any positive pools nearby?)
              →  whispers-mcp.events(bbox=user.bbox, last 90 days)
                 (any wildlife die-offs nearby?)
              →  knowledge-graph-mcp.outbreak_check(pathogen, county)
                 (active outbreak record?)
              →  knowledge-graph-mcp.resource_lookup(pathogen,
                                                    user.tribe?)
                 (Great AZ Tick Check, AZGFD, ADHS, ITCA-TEC)
              →  Triage Agent decision: self-care | see clinician |
                 report to AZGFD | mail tick to Walker lab
```

## MCP server spec template (for each new server)

To keep new MCP servers consistent with `vectorsurv-mcp`:

```
mcp/<name>/
  ├── README.md                 # what it does, install, env vars
  ├── pyproject.toml            # mcp[cli] + httpx + pydantic
  ├── .env.example              # credentials + PATH_* overrides
  ├── examples/
  │   └── claude_desktop_config.json
  ├── openapi/                  # versioned upstream-spec snapshots
  │   └── snapshot-<version>.json
  ├── src/<pkg>/
  │   ├── __init__.py
  │   ├── __main__.py           # stdio + streamable-http entry
  │   ├── client.py             # paths in env-overridable PATHS dict
  │   └── server.py             # FastMCP tools + resources
  └── tests/
      └── test_*.py             # synthetic-data tests, no live creds
```

Every server also drops a schema seed under `schema/deep/` documenting
its tools as graph nodes (`mcp_server`, `mcp_tool`, `api`,
`operatedBy`, `wraps`, `exposedBy`, `informs`) so the knowledge graph
itself can be queried for "what MCP tools answer Heat Q1?".

## Auth + data-sovereignty notes

- **VectorSurv** requires a Gateway account; the token is held in
  the MCP-server process, never sent to the LLM. The MCP boundary is
  the auth boundary.
- **Tribal data** lives behind tribal sovereignty. MCP servers
  proxying tribal data (e.g. a future Navajo Epidemiology Center
  feed) operate under tribal DUAs and never expose row-level data
  without an explicit MOU. The Validation Agent enforces row-level
  cell suppression at write time.
- **211 Arizona** call records are sensitive; the `211-az-mcp`
  exposes aggregated resource availability and *not* caller PII.
- **Personally-identifying observation data** never leaves the app
  client unless the user explicitly opts into a verified outreach
  contact. Default flows are anonymous + ZIP-coarse.
