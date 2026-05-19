---
title: AZ One Health Sentinel — agency dashboard
---

# `dashboard/` — agency-side analyst workspace

This is the **Phase 3 agency dashboard** for the
[AZ One Health Sentinel](../plan/README.html). It implements the
workspace from
[`plan/04-data-flows.md` Scenario D](../plan/04-data-flows.html#scenario-d--agency-side-cluster-review):
an ADHS epi opens a flagged hantavirus cluster overnight, reviews the
co-located WHISPers wildlife mortality events, and follows the chain
of evidence back to its underlying observation nodes in the knowledge
graph.

See
[`plan/05-roadmap.md` Phase 3](../plan/05-roadmap.html#phase-3--maricopa--coconino-pilot-month-69)
for the deliverable this folder fulfills:

> Agency dashboard for MCDPH, ADHS, AZGFD, Coconino HHS — new.

## Audiences

The dashboard is **four-audience** by design, mirroring the agencies
engaged for Phase 3 pilot review boards and the focus-group docs:

| Slug       | Agency | Focus | Scope |
|------------|--------|-------|-------|
| `adhs`     | Arizona Department of Health Services — Vector-Borne &amp; Zoonotic Diseases | Statewide arbovirus + heat mortality | All 15 counties |
| `mcdph`    | Maricopa County Department of Public Health — Heat Surveillance team | Heat clusters + WNV vector index | Maricopa County |
| `azgfd`    | Arizona Game &amp; Fish Department — Wildlife Health Program | WHISPers + AZGFD + iNaturalist | Statewide wildlife |
| `coconino` | Coconino County Health &amp; Human Services | Plague + hantavirus + Grand Canyon NPS coordination | Coconino + GRCA |

Every audience landing page renders the same five components:

1. **Status card** — count of new alerts in the last 24h / 7d / 30d.
2. **Cluster feed** — top 5 recent spatial-temporal clusters from the
   Cluster Detection Agent (the Scenario D hantavirus cluster is the
   canonical example).
3. **Arizona map embed** — recent observations + outbreak pins via
   the same MapLibre runtime [`map/`](../map/) uses, lazy-loaded to
   keep the page fast on analyst workstations.
4. **Case-counts table** — weekly + cumulative, with one SVG
   sparkline per row via the [`sparkline.js`](./shared/sparkline.js)
   component.
5. **"Open the underlying observations" button** — exposes the SQL
   the analyst would run against the read-only
   [`knowledge-graph-mcp`](../mcp/knowledge-graph-mcp/) endpoint.
   The dashboard **never executes the query from the browser**.

## Stack

Plain HTML + ES-module JS + one shared CSS file, same as
[`app/`](../app/), [`map/`](../map/), and [`graph/`](../graph/).
No bundler, no framework, no CSS toolkit.

```
dashboard/
  index.html              landing page with four audience cards
  shared/
    style.css             palette + analyst-table styling + print rules
    kg-client.js          fetch wrapper around knowledge-graph-mcp HTTP transport
    auth-stub.js          stub "Sign in as <agency>" toggle (placeholder for SSO)
    cluster-feed.js       polls the cluster-detection feed
    map-embed.js          lazy-loads MapLibre and renders pin GeoJSON
    sparkline.js          pure-SVG sparkline for time-series cells
  adhs/
    index.html            ADHS statewide arbovirus + heat-mortality dashboard
    arbovirus.html        drill-down: WNV + SLEV vector index by county
    heat-mortality.html   drill-down: weekly + cumulative deaths, disparities
  mcdph/
    index.html            Maricopa heat-surveillance pins + WNV vector index
    heat-clusters.html    drill-down: spatial-temporal ZCTA scan
  azgfd/
    index.html            WHISPers + AZGFD + iNaturalist wildlife overlay
  coconino/
    index.html            plague + hantavirus + Grand-Canyon NPS coordination
  mock/
    cluster-feed.json     canned cluster-detection events
    arbovirus-feed.json   canned WNV/SLEV MIR + cases by county
    heat-mortality.json   canned weekly heat-death + disparity series
    wildlife-events.json  canned WHISPers + AZGFD + iNat overlay
  README.md               this file
```

## Run locally

From the repo root:

```sh
python -m http.server 8000
```

then visit <http://localhost:8000/dashboard/>.

## Wiring to real MCP servers

By default every page renders against the canned JSON under
[`mock/`](./mock). To swap in a live
[`knowledge-graph-mcp`](../mcp/knowledge-graph-mcp/) HTTP endpoint:

```html
<body data-agency="adhs" data-kg-base="http://localhost:8765/mcp">
```

When `data-kg-base` is set, `shared/kg-client.js` issues
`tools/call` JSON-RPC envelopes against the
`MCP_TRANSPORT=streamable-http` mode of `knowledge-graph-mcp`. The
mock-fallback path is preserved unless explicitly opted out.

In a deployed install the dashboard would also be wired to:

- [`vectorsurv-mcp`](../mcp/vectorsurv-mcp/) for live vector-index
  readings (`vectorsurv_calculate_infection_rate`).
- [`adhs-mcp`](../mcp/adhs-mcp/) for ADHS arbovirus + heat-mortality
  summaries.
- [`whispers-mcp`](../mcp/whispers-mcp/) for AZGFD's wildlife
  mortality events.
- [`inaturalist-mcp`](../mcp/inaturalist-mcp/) for citizen-science
  overlays.

A small per-agency proxy (not in this prototype) would consolidate
those calls into the single endpoint pointed to by `data-kg-base`,
so the dashboard never speaks more than one HTTP wire-protocol.

## Read-only by construction

The dashboard is **read-only**. The "Verify outbreak" workflow from
Scenario D step 6 (a `Verify` milestone event written back to the
knowledge graph via `knowledge-graph-mcp`) is described as a
future-work box on every page; it ships as a separate, audited write
workflow outside this folder.

## Authentication

Production wiring will use federated **agency SSO** (ADHS Entra ID,
MCDPH Active Directory, AZGFD employee portal, Coconino HHS) plus a
per-agency **data-use agreement (DUA)**. None of those exist yet, so
the dashboard ships with [`shared/auth-stub.js`](./shared/auth-stub.js)
— a header dropdown that just switches the active landing page and
records the choice in `localStorage`.

## Accessibility &amp; responsive design

- Desktop-first (analyst workstations), but breakpoints kick in at
  ≤ 800px: cluster feed and analyst tables collapse cleanly, the map
  fills the viewport with a panel-toggle button (same pattern as
  [`map/index.html`](../map/index.html)).
- Print-friendly: `@media print` hides nav + interactive controls;
  the case-counts table becomes a clean printable report for
  daily / weekly review packets.
- All cards and tiles use the project palette (`#1F3A93` navy,
  `#C0392B` red, `#E84A2B` heat-orange, `#4CAF50` green) plus a
  `#6A1B9A` Coconino-only accent so agency views stay
  visually distinct without losing the family resemblance.

## Cross-references

- [Scenario D — agency cluster review](../plan/04-data-flows.html#scenario-d--agency-side-cluster-review) — the canonical walk-through.
- [Phase 3 roadmap entry](../plan/05-roadmap.html#phase-3--maricopa--coconino-pilot-month-69) — what this folder fulfills.
- [Agentic architecture](../plan/03-agentic-architecture.html) — the
  Cluster Detection Agent + Notification Agent that put rows on the
  feed.
- [`map/`](../map/) — the geospatial knowledge-graph viewer the map
  embed lazy-loads.
- [`graph/`](../graph/) — pathogen knowledge graph for nodes that
  appear in popups.
- [`app/`](../app/) — the field-facing mobile app whose CHW + tick +
  heat flows feed observations into the same graph.
- [`heat/04-vulnerable-populations.md`](../heat/04-vulnerable-populations.html)
  and [`wildlife/02-zoonotic-surveillance.md`](../wildlife/02-zoonotic-surveillance.html)
  — focus-group docs that drove the audience splits.
