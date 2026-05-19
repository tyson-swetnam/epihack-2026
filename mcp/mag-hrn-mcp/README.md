---
title: MAG Heat Relief Network MCP server
---

# `mag-hrn-mcp` — Model Context Protocol server for the MAG Heat Relief Network

A [Model Context Protocol](https://modelcontextprotocol.io/) server that
exposes the [Maricopa Association of Governments **Heat Relief
Network**](https://hrn.azmag.gov/) — ~200+ cooling, hydration, respite,
and donation-drop-off sites across the Phoenix metro that operate each
year from **May 1 through September 30** — as a set of tools an LLM
(Claude Desktop, Claude Code, Claude API agents, or any other MCP
client) can call.

Built for the EpiHack Arizona 2026 [Heat focus
group](../../heat/index.html). Powers the Heat-vertical scenarios in
[plan 04](../../plan/04-data-flows.html), in particular **Scenario C**
(unsheltered heat check-in on a Magenta-HeatRisk day) — the
`mag_search_centers(lat, lon, radius=2km, open_now=true,
pets_ok=false)` call in step 7.

> **Mock-by-default.** This server ships with a small canned dataset of
> 12 realistic Phoenix-metro sites (Burton Barr Central Library, Andre
> House of Hospitality, Mesa Main Library, Tempe Public Library, etc.)
> so the rest of the EpiHack stack can develop against it without
> hitting MAG infrastructure. Set `MAG_HRN_FEATURE_SERVICE_URL` in the
> environment to flip to the real MAG ArcGIS service (see
> [Pointing at the real ArcGIS service](#pointing-at-the-real-arcgis-service)
> below).

## What it does

| MCP tool | What it returns |
|---|---|
| `mag_search_centers` | Centers within `radius_km` of `(lat, lon)`, filtered by `open_now`, `pets_ok`, and `services`. Each row: `{id, name, address, city, postal_code, lat, lon, services, hours_today, pets_ok, distance_km, kg_node_id}`. |
| `mag_center_detail` | Full record for a center including hours-by-day, operator, notes, and a placeholder `kg_node_id`. |
| `mag_list_open_now` | Snapshot of every center currently open (optionally pinned to a specific timestamp). |
| `mag_supply_status` | **MOCK** supply / occupancy heads-up: `{water_status, seats_available, last_updated_iso, source}`. See [Heat-Q2](../../plan/01-parameter-mapping.html). |
| `mag_search_by_text` | Free-text lookup ("library", "church", "donation") with optional `[lat, lon]` distance-sort hint. |

Plus two MCP **resources**:

- `mag://service-types` — reference text for `cooling | hydration | respite | donation` (the tight 4-value vocabulary the client normalizes onto).
- `mag://operating-window` — the May 1 – September 30 season convention and the off-season-returns-empty contract.

## Why this matters for EpiHack

The Heat Relief Network is the only network in the country, at this
scale, that has stood up regional cooling/hydration coordination
across municipal boundaries every summer for over a decade. Wrapping
it as an MCP server lets an agent:

- Answer "where can I cool off right now?" in one call
  (`mag_search_centers(lat, lon)`), bounded to the operating season.
- Surface the Scenario-C transport hand-off to 211 Arizona
  (`mag_search_centers` → `211-az-mcp.transport_to_cooling_center`).
- Pre-stage the supply-feed contract (`mag_supply_status`) so when MAG
  ships a real-time feed the rest of the stack already knows the
  shape — that's [Heat-Q2 in plan/01](../../plan/01-parameter-mapping.html).

## Service-type vocabulary

| Value | Meaning |
|---|---|
| `cooling` | Indoor air-conditioned cooling center. |
| `hydration` | Walk-up water-bottle distribution (may be outdoors). |
| `respite` | Cooling center where uninterrupted rest is permitted. |
| `donation` | Drop-off site for public donations (not a relief site for those in need). |

Real MAG ArcGIS rows arrive with various labels (`LocationType`,
`Type`, `CenterType`, etc.); the client's `_normalize_services` maps
them onto these four values. One center can carry more than one type
(a library is often `cooling` + `hydration`).

## Operating window

The HRN runs **May 1 through September 30** each year. Outside this
window every tool returns an empty `centers` list and `off_season:
true`. The 2026 launch date is
[official](https://ein.az.gov/2026-heat-relief-network-launches-may-1-protect-residents-during-extreme-heat).
Phoenix doesn't observe DST, so all open-now math runs in MST (UTC-7).

## Mock dataset

The canned 12-site dataset covers Phoenix, Mesa, Tempe, Glendale,
Scottsdale, Chandler, Surprise, and Goodyear — a reasonable cross-
section of the real network's geography. Site names, addresses, and
coordinates are based on real, well-known locations so the multi-MCP
join in Scenario C feels right; **operating hours and supply notes are
plausible but synthetic** — defer to [hrn.azmag.gov](https://hrn.azmag.gov/)
for authoritative data.

## Pointing at the real ArcGIS service

Public probing of `geo.azmag.gov` (May 2026) shows the HRN's ArcGIS
service at:

```
https://geo.azmag.gov/arcgis/rest/services/maps/Heat_Relief_Network/MapServer
```

with at least a "Respite Center" layer at ID 1; per-season layer
indexes for cooling, hydration, and donation drop-off sit alongside.
A `FeatureServer` flavour of the same service may also exist (MAG has
historically published both). The exact URL drifts every season, so
the client reads it from `MAG_HRN_FEATURE_SERVICE_URL`:

```bash
export MAG_HRN_FEATURE_SERVICE_URL=https://geo.azmag.gov/arcgis/rest/services/maps/Heat_Relief_Network/MapServer
export MAG_HRN_FEATURE_LAYER=all   # walks every layer the service advertises
# Optional bearer token if a partner-only feed eventually requires one.
# export MAG_HRN_API_TOKEN=...
```

The client's `_ArcGISBackend`:

1. Hits `<service_url>?f=json` to enumerate layers when `MAG_HRN_FEATURE_LAYER=all`.
2. For each layer (or just the configured one), issues a single
   `GET <service_url>/<layer>/query?where=1=1&outFields=*&outSR=4326&f=json`.
3. Maps each feature's attributes through a tolerant alias map
   (`Name`/`SiteName`/`FACILITY`, `Address`/`ADDRESS1`/`Street`,
   `LocationType`/`Type`/`CenterType`, etc.) onto the canonical row
   shape the MCP tools return.

If MAG renames attributes mid-season, extend the
`_NAME_FIELDS` / `_ADDR_FIELDS` / `_TYPE_FIELDS` aliases in
[`client.py`](./src/mag_hrn_mcp/client.py).

A `.env.example` template is included; copy to `.env` and source it.

## The `mag_supply_status` mock — Heat-Q2

`mag_supply_status` is currently **mock-only**. MAG does not yet
publish a real-time occupancy/supply feed, and that gap is the entire
subject of [Heat-Q2 (Real-time resource sharing between cooling
centers)](../../plan/01-parameter-mapping.html). The MCP tool exists
now so the rest of the EpiHack stack can develop against the eventual
feed's *shape*:

```jsonc
{
  "center_id": "mag.hrn.mock.0002",
  "found": true,
  "name": "Andre House of Hospitality",
  "water_status": "low",          // ok | low | out
  "seats_available": 7,           // int or null
  "last_updated_iso": "2026-07-18T14:05:00",
  "source": "mock",               // flips to "feed" once a real feed ships
  "note": "MOCK feed. MAG does not yet publish a real-time supply feed; see plan/01-parameter-mapping.html Heat-Q2."
}
```

The mock derives its values deterministically from the center ID so
multiple calls in the same session return stable values for a demo.

## Install & run

### As a Claude Desktop MCP server

1. Install [`uv`](https://docs.astral.sh/uv/) if you don't have it.
2. Drop the snippet in
   [`examples/claude_desktop_config.json`](./examples/claude_desktop_config.json)
   into your Claude Desktop config
   (`~/Library/Application Support/Claude/claude_desktop_config.json`
   on macOS, `%APPDATA%\Claude\claude_desktop_config.json` on Windows).
3. Replace the path with the absolute path to this directory.
4. Leave `MAG_HRN_FEATURE_SERVICE_URL` empty to run in mock mode, or
   point it at the active MAG ArcGIS service for live data.
5. Restart Claude Desktop.

### Standalone

```bash
cd mcp/mag-hrn-mcp
uv sync
uv run mag-hrn-mcp                                # stdio (default)
MCP_TRANSPORT=streamable-http uv run mag-hrn-mcp  # HTTP
```

### Tests

```bash
cd mcp/mag-hrn-mcp
uv run pytest
```

The test suite is fully offline. It exercises the haversine math, the
open-now / pets-ok / services filters, the free-text search, the
off-season-returns-empty contract, and the mock supply-status response
shape (`source: "mock"`).

## License

MIT, alongside the rest of `epihack-2026`.
