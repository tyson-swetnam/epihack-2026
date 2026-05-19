---
title: Application plan — AZ One Health Sentinel
---

# Plan — AZ One Health Sentinel

A working name for the application this plan describes: a mobile-first
participatory-surveillance + early-warning app for Arizona that operates
across two flagship verticals — **Vector-Borne Disease (VBD)** and
**Heat** — backed by the existing
[DuckLake knowledge graph](../schema/) and driven by an agentic
architecture that consumes real-time data via MCP servers.

## What you're reading

1. [`01-parameter-mapping.md`](./01-parameter-mapping.html) — the
   Figure 2 *Minimum Set of Key Data Parameters* mapped to each
   vertical: which parameters apply, which are additions, which are
   suppressed, and how each parameter lands in DuckLake.
2. [`02-mcp-integration.md`](./02-mcp-integration.html) — the MCP
   server inventory (one built, eight to build) with a parameter-by-
   parameter table showing which API feeds which Minimum-Dataset slot.
3. [`03-agentic-architecture.md`](./03-agentic-architecture.html) —
   the eight-agent topology that turns a community report into a
   triaged, enriched, validated observation in the knowledge graph and
   a personalized response back to the user.
4. [`04-data-flows.md`](./04-data-flows.html) — four worked
   end-to-end scenarios (tick mailed in, sick mosquito-bitten patient,
   unsheltered heat-distress check-in, agency-side cluster detection).
5. [`05-roadmap.md`](./05-roadmap.html) — phased delivery: hackathon
   MVP → 6-month pilot → 12-month evaluation against the
   [Figure 3 timeliness milestones](../figures/03-outbreak-timeliness-metrics.html).
6. [`06-mobile-app.md`](./06-mobile-app.html) — anonymous-first
   Human / Animal / Environmental reporting app: low-text UI,
   EXIF-stripped photos, ZIP/km coarsening, "never diagnose" risk
   boundary, DuckLake snapshots backed by GitHub LFS, web pilot
   → iOS + Android.
7. [`07-auth.md`](./07-auth.html) — optional account system
   (email/password, magic-link, OAuth via Google / Facebook /
   Apple) layered on top of anonymous reporting. Supabase Auth
   backend; right to erasure detaches but does not delete attached
   observations.

## The thesis in one paragraph

The
[Minimum Dataset (Figure 2)](../figures/02-minimum-key-data-parameters.html)
is the **shared data contract** that lets one app serve both
verticals: the *General* class is identical for VBD and Heat, the
*Human* class diverges into infectious symptoms vs. heat-illness
symptoms, the *Exposure* and *Environmental* classes pick up
domain-specific sub-fields, and the *Livestock / Wildlife* classes
matter for VBD but are silent for Heat. Treating the dataset as a
contract — rather than building two apps — means one knowledge graph,
one set of MCP integrations, one agentic pipeline, and two thin
domain-specific UIs on top.

## The architecture in one diagram

```
   ┌──────────────────────────────────────────────────────────────────┐
   │                       Community user (mobile)                   │
   │      VBD UI · Heat UI · SMS fallback · Voice (transcribed)      │
   └─────────────────────────────────┬───────────────────────────────┘
                                     │  free-text / photo / geo / form
                                     ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │                           Agentic layer                          │
   │  Intake → Geo-Enrichment → Validation → Triage → Enrichment      │
   │                            ↓                                     │
   │       Notification ← Cluster Detection ← Knowledge Update        │
   └─────────────┬──────────────────────────┬─────────────────────────┘
                 │                          │
                 ▼                          ▼
   ┌──────────────────────┐     ┌───────────────────────────────────┐
   │  DuckLake knowledge  │     │           MCP servers              │
   │  graph (this repo)   │ ←→  │  vectorsurv-mcp ✅                 │
   │                      │     │  nws-heatrisk-mcp ⏳               │
   │  observations,       │     │  mag-hrn-mcp ⏳                    │
   │  pathogens,          │     │  adhs-mcp ⏳                       │
   │  outbreaks,          │     │  great-az-tick-check-mcp ⏳        │
   │  resources, regions, │     │  whispers-mcp ⏳                   │
   │  tribes, ICD-10, …   │     │  inaturalist-mcp ⏳                │
   │                      │     │  211-az-mcp ⏳                     │
   └──────────────────────┘     │  knowledge-graph-mcp ⏳            │
                                └───────────────────────────────────┘
                 ▲
                 │
   ┌──────────────────────────────────────────────────────────────────┐
   │  Agency analyst / CHW / decision-maker dashboards (web)          │
   │  Backed by the same knowledge graph; recursive-CTE path queries  │
   └──────────────────────────────────────────────────────────────────┘
```

## Why this approach

- **The knowledge graph is the integration substrate.** Every
  observation, MCP-fetched record, and dashboard view goes through
  `kg.node` / `kg.edge` / `kg.property`. New data sources land as
  schema seeds; they don't fork the data model.
- **Agents do the messy work, the graph is the source of truth.**
  LLM agents extract structured Minimum-Dataset rows from free-text
  / voice / photo reports, enrich them with MCP-fetched context, and
  flag anomalies — but the persistent record is always typed and
  queryable in plain SQL.
- **MCP is the live-data bus.** Each upstream agency exposes one MCP
  server; the agents speak MCP, not bespoke clients. New agencies
  join the system by shipping a server, not by negotiating bilateral
  integrations.
- **One app, two verticals, shared contract.** The Figure 2 dataset
  forces both verticals into the same primitives so cross-domain
  analysis (e.g. *do heat days correlate with WNV pool positivity
  three weeks later?*) is a SQL query, not a multi-week ETL project.
- **The Figure 3 timeliness milestones are the success metric.**
  Detect → Notify → Verify → Lab → Respond intervals are computed
  directly from the observation timestamps and the linked outbreak
  record. Every design decision is judged by how much it shortens
  those intervals.

## Status snapshot

| Component | Status |
|---|---|
| Knowledge-graph schema (core + deep seeds) | ✅ shipped |
| MapLibre + Cytoscape viewers | ✅ shipped |
| `vectorsurv-mcp` (spec-aligned to v1.0.44) | ✅ shipped |
| `nws-heatrisk-mcp` | ⏳ planned |
| `mag-hrn-mcp` | ⏳ planned |
| `adhs-mcp` | ⏳ planned |
| `great-az-tick-check-mcp` | ⏳ planned |
| `whispers-mcp`, `inaturalist-mcp`, `211-az-mcp`, `knowledge-graph-mcp` | ⏳ planned |
| Intake / Triage / Enrichment / Notification agents | ⏳ planned |
| Mobile UI (VBD + Heat) | ⏳ planned |
| Agency dashboard | ⏳ planned |
