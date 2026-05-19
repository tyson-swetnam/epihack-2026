---
title: NWS HeatRisk MCP server
---

# `nws-heatrisk-mcp` — Model Context Protocol server for the NWS public API and the WPC HeatRisk product

A [Model Context Protocol](https://modelcontextprotocol.io/) server that
exposes the U.S. [National Weather Service public
API](https://www.weather.gov/documentation/services-web-api)
(`api.weather.gov`) and the [WPC HeatRisk gridded
product](https://www.wpc.ncep.noaa.gov/heatrisk/) as a set of tools an
LLM (Claude Desktop, Claude Code, Claude API agents, or any other MCP
client) can call.

Built for the EpiHack Arizona 2026 [Heat focus
group](../../heat/index.html). Powers the Heat-vertical scenarios in
[plan 04](../../plan/04-data-flows.html), in particular Scenario C
(unsheltered heat check-in on a Magenta-HeatRisk day).

## What it does

| MCP tool | Backed by |
|---|---|
| `nws_heatrisk` | WPC HeatRisk daily gridded product |
| `nws_heatrisk_week` | WPC HeatRisk (7-day outlook) |
| `nws_forecast` | `GET /points/{lat},{lon}` then the returned `forecast` / `forecastHourly` URL |
| `nws_current_conditions` | `GET /points/{lat},{lon}/stations` then `GET /stations/{id}/observations/latest` |
| `nws_heat_index` | client-side: NWS Rothfusz regression with humidity adjustments |
| `nws_active_heat_alerts` | `GET /alerts/active?area=...&event=...` for each heat event name |
| `nws_alert_zones_for_point` | `GET /points/{lat},{lon}` (extracts the zone IDs) |

Plus two MCP **resources**: `nws://heatrisk-categories` (Green / Yellow
/ Orange / Red / Magenta with HHS-aligned heat-health descriptions) and
`nws://api-base-url` (the active `NWS_BASE_URL` and `User-Agent`).

## Why this matters for EpiHack

The NWS public API is the authoritative live source for U.S. weather
data, and HeatRisk is the only nationally-published forecast that
combines forecast temperature, anomaly from local climatology, and
health-impact thresholds into a single 0-4 category an LLM (or a
clinician) can act on. Exposing both as an MCP server lets an agent:

- Answer "is today dangerous heat for this person?" with a single
  call (`nws_heatrisk(lat, lon)`).
- Cross-check the WPC forecast against any open NWS warnings for the
  exact zone the user is standing in.
- Compute the heat index live from the nearest observation station
  without leaving the conversation.
- Drop the result into the [DuckLake knowledge
  graph](../../schema/) as the `Environmental` block of an
  observation, with full provenance.

## Authentication

**None.** The NWS public API has no token. It *does* require a
descriptive `User-Agent` header that identifies the application and
provides a contact (email or URL). Requests without one are rejected.
The server refuses to start without `NWS_USER_AGENT` set, with a
clear error.

```bash
# Pattern: "<app-name> (<contact email or URL>)"
export NWS_USER_AGENT="epihack-az-2026-sentinel (contact@example.org)"
```

A `.env.example` template is included; copy to `.env` and source it.

## HeatRisk URL drift caveat

NWS HeatRisk is an **experimental** product whose machine-readable
endpoint has moved more than once as the WPC has iterated on its
hosting. The client ships with the best-known URL at build time, but
makes it env-overridable:

```bash
# Override if the default 404s or returns HTML rather than JSON.
export NWS_HEATRISK_URL=https://www.wpc.ncep.noaa.gov/heatrisk/data/heatrisk.json
```

The HeatRisk feed parser accepts a few common shapes (flat list of
daily dicts, GeoJSON FeatureCollection, NWS-style
`properties.values`). If your deployment encounters a new shape,
extend `_iter_records` / `extract_daily` in
[`heatrisk.py`](./src/nws_heatrisk_mcp/heatrisk.py) — those are the
only places that need to know the wire format.

## Endpoint overrides

Every `api.weather.gov` path is overridable via env, so the deployed
server can be corrected without a code release if NWS reorganizes:

```
NWS_PATH_POINTS                 (default /points/{lat},{lon})
NWS_PATH_ALERTS_ACTIVE          (default /alerts/active)
NWS_PATH_STATIONS_FOR_POINT     (default /points/{lat},{lon}/stations)
NWS_PATH_STATION_OBSERVATIONS   (default /stations/{station_id}/observations/latest)
NWS_PATH_ZONE                   (default /zones/{zone_type}/{zone_id})
```

Plus `NWS_BASE_URL` and `NWS_HEATRISK_URL` as above.

## Heat index

`nws_heat_index(temp_f, rh_percent)` is pure computation, no network.
Implements the standard NWS [Rothfusz regression
equation](https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml)
with the documented low-humidity (RH < 13%, 80 < T < 112) and
high-humidity (RH > 85%, 80 < T < 87) adjustments. Returns the heat
index in °F plus the NWS caution band (`Caution` / `Extreme Caution`
/ `Danger` / `Extreme Danger`).

Unit tests in [`tests/test_heat_index.py`](./tests/test_heat_index.py)
verify the canonical table values:

| T (°F) | RH (%) | NWS table HI | computed |
|---|---|---|---|
| 80 | 40 | 80 | ~80 |
| 90 | 70 | 106 | ~106 |
| 100 | 50 | 119 | ~119 |
| 110 | 40 | 136 | ~136 |

## Install & run

### As a Claude Desktop MCP server

1. Install [`uv`](https://docs.astral.sh/uv/) if you don't have it.
2. Drop the snippet in
   [`examples/claude_desktop_config.json`](./examples/claude_desktop_config.json)
   into your Claude Desktop config
   (`~/Library/Application Support/Claude/claude_desktop_config.json`
   on macOS, `%APPDATA%\Claude\claude_desktop_config.json` on
   Windows).
3. Replace the path with the absolute path to this directory.
4. Set `NWS_USER_AGENT` to a real value (your app + a real contact).
5. Restart Claude Desktop.

### Standalone

```bash
cd mcp/nws-heatrisk-mcp
uv sync
NWS_USER_AGENT="epihack-az-2026-sentinel (you@example.org)" \
    uv run nws-heatrisk-mcp                          # stdio (default)
MCP_TRANSPORT=streamable-http uv run nws-heatrisk-mcp  # HTTP
```

### Tests

```bash
cd mcp/nws-heatrisk-mcp
uv run pytest
```

The unit tests verify the heat-index regression against the canonical
NWS table values and check that the client's env-driven configuration
(User-Agent requirement, base URL and path overrides) behaves as
documented. No live NWS connection is required.

## Retry behaviour

`api.weather.gov` returns HTTP 503 under load. The client retries 5xx
responses up to 3 times with exponential backoff (0.5s, 1s, 2s) before
raising. 4xx responses are surfaced immediately — they almost always
indicate a malformed request or a missing User-Agent.

## License

MIT, alongside the rest of `epihack-2026`.
