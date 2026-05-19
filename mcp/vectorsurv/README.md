---
title: VectorSurv MCP server
---

# `vectorsurv-mcp` — Model Context Protocol server for VectorSurv

A [Model Context Protocol](https://modelcontextprotocol.io/) server that
exposes the [VectorSurv](https://vectorsurv.org/) vector-borne disease
surveillance API as a set of tools an LLM (Claude Desktop, Claude Code,
Claude API agents, or any other MCP client) can call.

Built for the EpiHack Arizona 2026 [Wildlife &amp; Vector-Borne Diseases
focus group](../../wildlife/index.html).

## What it does

| MCP tool | What it returns |
|---|---|
| `vectorsurv_list_agencies` | Agencies the authenticated user has access to |
| `vectorsurv_list_sites` | Trap-location bookmarks |
| `vectorsurv_get_collections` | Raw trap-capture records (mosquitoes or ticks) |
| `vectorsurv_get_pools` | Pooled-test results with arbovirus targets |
| `vectorsurv_calculate_abundance` | Abundance per interval = total / trap-nights |
| `vectorsurv_calculate_infection_rate` | MIR or bias-corrected MLE infection rate |
| `vectorsurv_calculate_vector_index` | VI = abundance × infection rate |

Plus an MCP **resource** at `vectorsurv://disease-acronyms` listing the
common arbovirus codes (WNV, SLEV, WEEV, EEEV, DENV, ZIKV, CHIKV, BORR,
ANAP, BABE).

## Why this matters for EpiHack

VectorSurv is the leading platform for mosquito and tick surveillance in
the U.S. (Maricopa County Vector Control reports to it; California,
Texas, and many other state and local programs use it as their backbone).
Exposing it as an MCP server lets an LLM:

- Answer ad-hoc surveillance questions in conversational form
  (*"What was the WNV vector index in agency 7 during biweek 18 of 2025?"*).
- Feed real surveillance data into the [DuckLake knowledge
  graph](../../schema/) without writing R or Python glue.
- Power participatory-surveillance triage workflows where field reports
  are cross-referenced against current VectorSurv signals.

## Authentication

VectorSurv uses Bearer authentication. The server obtains a token from
`POST https://api.vectorsurv.org/login` and refreshes it before the
one-hour expiry. You supply Gateway credentials via environment
variables:

```bash
export VECTORSURV_USERNAME=your_gateway_username
export VECTORSURV_PASSWORD=your_gateway_password
# Optional: point at the Sandbox or a proxy
export VECTORSURV_BASE_URL=https://api.vectorsurv.org
```

A `.env.example` template is included; copy it to `.env` and source it.

## Install &amp; run

### As a Claude Desktop MCP server

1. Install [`uv`](https://docs.astral.sh/uv/) if you don't have it.
2. Drop the snippet in [`examples/claude_desktop_config.json`](./examples/claude_desktop_config.json)
   into your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`
   on macOS, `%APPDATA%\Claude\claude_desktop_config.json` on Windows).
3. Replace `/absolute/path/to/epihack-2026/mcp/vectorsurv` with the
   absolute path on your machine.
4. Fill in `VECTORSURV_USERNAME` and `VECTORSURV_PASSWORD`.
5. Restart Claude Desktop. The `vectorsurv` tools will appear in the
   tool picker.

### Standalone

```bash
cd mcp/vectorsurv
uv sync
uv run vectorsurv-mcp                # stdio (default)
MCP_TRANSPORT=streamable-http uv run vectorsurv-mcp  # HTTP
```

### Tests

```bash
cd mcp/vectorsurv
uv run pytest
```

The included tests exercise the abundance / MIR / BC-MLE / vector-index
math against synthetic data; they don't require live VectorSurv
credentials.

## Endpoints used

| MCP tool | VectorSurv endpoint (default) | Override env var |
|---|---|---|
| (login) | `POST /login?username=…&password=…` | `VECTORSURV_PATH_LOGIN` |
| `vectorsurv_list_agencies` | `GET /agency` | `VECTORSURV_PATH_AGENCIES` |
| `vectorsurv_list_sites` | `GET /v1/site/` | `VECTORSURV_PATH_SITES` |
| `vectorsurv_get_collections` | `GET /v1/arthropod/collection` | `VECTORSURV_PATH_COLLECTIONS` |
| `vectorsurv_get_pools` | `GET /v1/arthropod/pool` | `VECTORSURV_PATH_POOLS` |

> **Paths are inferred, not verified against the live Swagger.** The
> root URL <https://api.vectorsurv.org/> hosts the Swagger UI for the
> live spec; if any of the defaults above disagree with what Swagger
> shows, override the corresponding env var (no code change required).
> Sources for the defaults are the public
> [`vectorsurvR`](https://github.com/UCD-DART/vectorsurvR) R package
> and the [VectorSurv API docs](https://docs.api.vectorsurv.org/). The
> `/login` path is the most confident; `/agency` and `/v1/arthropod/pool`
> are the most likely to drift.

## Calculations

- **Abundance** — `Σ num_count / Σ trap_nights` per interval.
- **MIR (Minimum Infection Rate)** — `scale × positives / mosquitoes_tested`.
- **bc-MLE** — Hepworth bias-corrected MLE assuming roughly equal
  pool sizes. For high-precision work with heterogeneous pool sizes,
  prefer the
  [`pooltestr`](https://cran.r-project.org/package=pooltestr) R package
  or `PooledInfRate`.
- **Vector Index** — `abundance × infection_rate / scale`, per the
  [Maricopa County and VectorSurv definition](https://vectorsurv.org/docs/tools/calculators/vector-index/).

## Limits and caveats

- The API's exact JSON response shapes are not fully public. The client
  is tolerant to both `[...]` and `{"data": [...]}` envelopes and falls
  back to passing through whatever the server returns.
- The server caches the auth token in memory only; restart loses it.
- Rate limits are not documented publicly. Be a good citizen.
- The VectorSurv Sandbox is the right place to develop against.

## License

MIT, alongside the rest of `epihack-2026`.
