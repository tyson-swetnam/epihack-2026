---
title: "AZ One Health Today — public aggregated dashboard"
description: "Citizen-facing aggregated view of today's heat, vector-borne disease, and wildlife signals across Arizona. Built on the same MCP-server substrate as the agency dashboard, but anonymised."
phase: 3
---

# AZ One Health Today

The public-facing complement to the (Phase 3) agency dashboard. Same
data substrate — the DuckLake knowledge graph and the MCP servers —
**aggregated and anonymised** for a non-specialist audience.

Tuned to answer one question on a phone:

> *What's happening near me right now?*

Single page, seven panels:

1. **Hero** — today's date, the user's county (auto-detected with a
   manual override), the headline number. Example:
   *"Magenta HeatRisk in Maricopa County today"* or
   *"WNV vector index up 3x in Maricopa this week"*.
2. **Heat** — current `nws-heatrisk-mcp` tier + 7-day outlook + count
   of `mag-hrn-mcp` cooling centers within 5 km + deep-link to
   `app/heat/cool-off/`.
3. **Vector-borne disease** — trailing 4-week WNV pool positivity for
   the focused county via
   `vectorsurv-mcp.vectorsurv_calculate_infection_rate`; active outbreaks
   from `whispers-mcp` + `knowledge-graph-mcp`; deep-link to
   `app/tick/`.
4. **Recent wildlife signals** — last 10 days of `whispers-mcp` +
   `inaturalist-mcp` records relevant to vectors / reservoirs, shown
   as a list (always) plus a lazy-loaded MapLibre map (progressive
   enhancement).
5. **Statewide rollup** — five-number snapshot (heat-emergency
   dispatches, WNV pools positive, hantavirus YTD, rabies YTD, plague
   YTD). Refreshes hourly.
6. **Action menu** — three buttons: *Submit a tick* / *Heat check-in
   for a friend* / *See cooling centers near me*.
7. **How this works** — short paragraph linking to `plan/`, `figures/`,
   and the MCP-server READMEs. **No personal data ever appears on this
   page.**

## Stack

Plain HTML + ES-module JS + a small CSS file. **No bundler. No
framework.** Same conventions as `app/`, `map/`, `graph/`.

```
today/
  index.html             single page, all 7 panels
  today.js               controller — wires geo + feeds + i18n
  shared/
    style.css            palette mirrors app/shared/style.css; 17 px base
    feeds.js             fetch wrappers (mock by default, real with data-feeds-base)
    geo-strip.js         navigator.geolocation -> AZ county, manual override
    sparkline.js         pure-SVG sparkline (canonical copy; dashboard/ can import it)
    map-embed.js         lazy-loaded MapLibre wrapper for the wildlife layer
  mock/
    heatrisk.json        canned nws-heatrisk-mcp.nws_heatrisk_week
    wnv-positivity.json  canned vectorsurv_calculate_infection_rate
    wildlife-signals.json canned whispers + iNat blend
    cooling-centers.json  canned mag-hrn-mcp.mag_search_centers
    statewide-rollup.json canned 5-number snapshot
```

## Privacy stance

This page is a **public** surface. The hard rule:

> No personal data — no PII, no line-data, no row-level wildlife
> coordinates finer than ~1 km — ever appears here.

We enforce it by construction:

- **No login.** No account creation. No analytics that send PII.
- **No remote geocoder.** County detection is local: the browser's
  `navigator.geolocation.getCurrentPosition` returns a lat/lon that
  *stays on-device*. We match it against the 15 AZ-county bounding
  boxes baked into `shared/geo-strip.js`. The user's coordinates are
  never sent to a server.
- **Aggregation, never line-data.** Every panel calls an aggregation
  feed (counts, rates, biweek totals). The agency-facing dashboard
  (Phase 3, separate) sees the line-data; this page does not.
- **Coordinates are rounded.** Wildlife observations are rounded to
  ~1 km before they hit `today/mock/wildlife-signals.json` (and the
  same rounding applies to the live feed in production).

## Accessibility + UX

- Mobile-first. Phones are the primary device for this audience.
- Large tap targets (44 × 44 minimum) on every button, every link,
  every dropdown.
- Semantic HTML, ARIA labels on every numeric card, status regions
  for the geo strip and the feed loaders.
- `prefers-reduced-motion` honoured on every animation (sparklines,
  skeleton shimmer, map fly-to).
- 17 px base font and high-contrast colours for outdoor reading.
- **English + Spanish** via the existing `app/shared/i18n.js` pattern
  (the page extends the central bundle with a small page-specific
  set of strings).
- **Works without JavaScript** for the first screen: a noscript block
  surfaces today's Magenta HeatRisk text, a static three-row cooling
  -center list, and the action menu as plain `<a>` links. The
  interactive map and county-auto-detect are progressive enhancements.

## Wire to real MCPs

The page swaps in real data with one HTML attribute:

```html
<body data-feeds-base="https://sentinel.example.org/api">
```

Each feed module then fetches `${base}/today/<key>` (see
`shared/feeds.js`). The expected shapes match the canned fixtures
under `mock/`, which in turn match the MCP-tool outputs you can
discover with `mcp/<server>/README.md`.

| Panel | Live source | Notes |
|---|---|---|
| Hero / 7-day | `nws-heatrisk-mcp.nws_heatrisk_week(lat,lon)` for the *county centroid* (not the user) so no PII leaves the page. | Page-local logic picks the headline. |
| Heat / centers | `mag-hrn-mcp.mag_search_centers(lat=county_centroid, radius_km=5)`. Page reads only the count. | The deep-link to `app/heat/cool-off/` is where the user's *own* lat/lon enters the system. |
| VBD | `vectorsurv-mcp.vectorsurv_calculate_infection_rate(target="WNV", interval="Biweek", start_date=T-56d, end_date=T)` joined with `whispers-mcp.whispers_search_events` + `knowledge-graph-mcp.kg_node_lookup(outbreak.*)`. | The page asks for per-county and statewide tracks in a single rollup. |
| Wildlife | `whispers-mcp.whispers_search_events(state="AZ", since=T-10d)` ∪ `inaturalist-mcp.inat_observations(place_id=53, since=T-10d)` for tick / mosquito / reservoir taxa. | Coordinates rounded to 1 km. |
| Rollup | small ad-hoc fan-out across `adhs-mcp` + `vectorsurv-mcp` + `211-az-mcp`. | **See below — a single aggregation MCP would simplify this.** |

### Places we'd want a richer aggregation MCP

The current per-tool calls work, but for a public dashboard refreshing
hourly we'd ideally have a **`today-rollup-mcp`** with one tool per
panel:

- `today.heat_for_county(county_id) -> { tier, advice, week, cooling_count_5km }`
- `today.wnv_for_county(county_id) -> { intervals[8], trend_multiple, statewide_intervals[8] }`
- `today.wildlife_recent(state="AZ", days=10) -> { items: [...], by_icon: {...} }`
- `today.statewide_rollup() -> { items: [{key, value, label, trend, sources}] }`

Each tool would precompute the rollup against a 1-hour cache (with
the cadence visible to the client). The benefits:

1. **One round-trip per panel** instead of three or four — the page
   stays responsive on slow cellular.
2. **One place to enforce the privacy ceiling** (county-level
   aggregation, 1-km coordinate rounding, no outlier rows).
3. **One audit log** (`agent_run` table from Phase 3 of the plan) per
   public-page render.

For now we cover this with mock fixtures and the per-row queries; a
small aggregation server is an early Phase-3 deliverable.

## Verification

- `python -m http.server` from the repo root serves every file with
  HTTP 200. (The HTML, the CSS, and the JS modules all resolve
  relative paths cleanly.)
- `node --check` passes on every JS module under `shared/` plus
  `today.js`.
- `python -c "import html5lib, sys; html5lib.parse(open(sys.argv[1]), namespaceHTMLElements=False)" today/index.html`
  parses with no errors.
- With `navigator.geolocation` disabled, the page stays on the
  *Arizona (statewide)* view; the statewide rollup, the action menu,
  and the heat panel all render.

## Cross-references

- `app/` — the action menu deep-links to the four flow pages.
- `map/` — the deeper geospatial view (county polygons, tribal
  nations, agency HQs, outbreak history).
- `graph/` — the pathogen knowledge graph.
- `plan/` — the architecture and the Phase-3 placement of this page.
- `mcp/` — the per-source READMEs.
