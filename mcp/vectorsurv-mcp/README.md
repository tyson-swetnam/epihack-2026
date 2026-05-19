---
title: VectorSurv MCP server
---

# `vectorsurv-mcp` — Model Context Protocol server for VectorSurv

A [Model Context Protocol](https://modelcontextprotocol.io/) server that
exposes the [VectorSurv](https://vectorsurv.org/) vector-borne disease
surveillance API as a set of tools an LLM (Claude Desktop, Claude Code,
Claude API agents, or any other MCP client) can call.

Built for the EpiHack Arizona 2026 [Wildlife & Vector-Borne Diseases
focus group](../../wildlife/index.html).

> **Spec-aligned (v1.0.44).** All paths, query parameters, and
> authentication flow are verified against the OpenAPI spec at
> <https://api.vectorsurv.org/openapi>. A snapshot lives in
> [`openapi/`](./openapi/); diff it against future fetches to detect
> drift.

## What it does

| MCP tool | Backed by |
|---|---|
| `vectorsurv_version` | `GET /version` |
| `vectorsurv_list_agencies` | `GET /v1/agency` |
| `vectorsurv_agency_region_intersect` | `GET /v1/agency-region-intersect` |
| `vectorsurv_list_regions` | `GET /v1/region` |
| `vectorsurv_list_test_targets` | `GET /v1/test/target` |
| `vectorsurv_list_sites` | `GET /v1/site` |
| `vectorsurv_get_collections` | `GET /v1/arthropod/collection` (or `/v1/tick/collection`) |
| `vectorsurv_get_pools` | `GET /v1/arthropod/pool` (with `type=mosquito|tick|nontick`) |
| `vectorsurv_pools_are_positive` | `GET /v1/arthropod/pool/are-positive` |
| `vectorsurv_get_case_counts` | `GET /v1/case-count` |
| `vectorsurv_calculate_abundance` | client-side: `Σ num_count / Σ trap_nights` |
| `vectorsurv_calculate_infection_rate` | client-side MIR or bc-MLE |
| `vectorsurv_calculate_vector_index` | client-side: abundance × IR |

Plus two MCP **resources**: `vectorsurv://disease-acronyms` and
`vectorsurv://query-syntax` (a Mongoose-style cheat-sheet).

## Why this matters for EpiHack

VectorSurv is the leading platform for mosquito and tick surveillance in
the U.S. (Maricopa County Vector Control reports to it; California,
Texas, and many other state and local programs use it as their backbone).
Exposing it as an MCP server lets an LLM:

- Answer ad-hoc surveillance questions in conversational form
  (*"What was the WNV vector index in agency 7 during biweek 18 of 2025?"*).
- Find Arizona agencies in one call (`agency_region_intersect`),
  filter to their pools and collections, and compute the same metrics
  that VectorSurv Gateway shows in its UI.
- Feed real surveillance data into the [DuckLake knowledge
  graph](../../schema/) without writing R or Python glue.

## Authentication

VectorSurv uses HTTP Bearer (JWT). The server obtains a token from
`POST /login` with a JSON body and refreshes it before the one-hour
expiry. Credentials come from environment:

```bash
export VECTORSURV_USERNAME=your_gateway_username
export VECTORSURV_PASSWORD=your_gateway_password
# Optional: point at sandbox or dev
export VECTORSURV_BASE_URL=https://api.vectorsurv.org
# Other endpoints documented in the spec:
#   https://sandbox.api.vectorsurv.org/
#   https://dev.api.vectorsurv.org/
```

A `.env.example` template is included; copy to `.env` and source it.

## Query syntax notes

The API uses **Mongoose-style operators** in the query string. The
client handles this transparently; if you're inspecting requests:

```
GET /v1/arthropod/pool
  ?type=mosquito
  &query[collection_date][$gte]=2024-05-01
  &query[collection_date][$lte]=2024-09-30
  &query[agency]=55
  &populate[0]=test
  &populate[1]=species
  &page=1
  &pageSize=1000
```

Don't pass flat `start_date=...` or `agency_ids=...` — the API doesn't
read them.

## Install &amp; run

### As a Claude Desktop MCP server

1. Install [`uv`](https://docs.astral.sh/uv/) if you don't have it.
2. Drop the snippet in [`examples/claude_desktop_config.json`](./examples/claude_desktop_config.json)
   into your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`
   on macOS, `%APPDATA%\Claude\claude_desktop_config.json` on Windows).
3. Replace the path with the absolute path to this directory.
4. Fill in `VECTORSURV_USERNAME` and `VECTORSURV_PASSWORD`.
5. Restart Claude Desktop.

### Standalone

```bash
cd mcp/vectorsurv-mcp
uv sync
uv run vectorsurv-mcp                 # stdio (default)
MCP_TRANSPORT=streamable-http uv run vectorsurv-mcp  # HTTP
```

### Tests

```bash
cd mcp/vectorsurv-mcp
uv run pytest
```

Unit tests exercise the abundance / MIR / bc-MLE / vector-index math
against synthetic data; they don't require live credentials.

## Endpoint overrides

Every path is overridable via env, so the deployed server can be
corrected without a code change if VectorSurv's spec drifts:
`VECTORSURV_PATH_LOGIN`, `_VERSION`, `_AGENCIES`, `_AGENCY_REGION`,
`_SITES`, `_REGIONS`, `_REGION_TYPES`, `_ARTHRO_COLLECTION`,
`_TICK_COLLECTION`, `_POOLS`, `_TICK_POOLS`, `_POOL_ARE_POSITIVE`,
`_ABUNDANCE_FLAT`, `_CASE_COUNT`, `_TEST_TARGET`, `_TEST_METHOD`,
`_TICK_CALC_ABUND`.

## Calculations

- **Abundance** — `Σ num_count / Σ trap_nights` per interval.
- **MIR (Minimum Infection Rate)** — `scale × positives / mosquitoes_tested`.
- **bc-MLE** — Hepworth bias-corrected MLE assuming roughly equal
  pool sizes. For heterogeneous pool sizes, prefer the
  [`pooltestr`](https://cran.r-project.org/package=pooltestr) R package
  or `PooledInfRate`. VectorSurv also has a server-side tick abundance
  calculation at `POST /v1/tick/calculation/abundance` (async job,
  poll for results) which the client can drive if you need their
  authoritative numbers.
- **Vector Index** — `abundance × infection_rate / scale`, per the
  [Maricopa County and VectorSurv definition](https://vectorsurv.org/docs/tools/calculators/vector-index/).

## License

MIT, alongside the rest of `epihack-2026`.
