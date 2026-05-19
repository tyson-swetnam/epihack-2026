---
title: "Phase 0 execution status"
---

# Phase 0 — execution status

Snapshot of the Phase-0 deliverables from
[`plan/05-roadmap.md`](./05-roadmap.html). All six in-flight
sub-agents have reported back; the deliverables below are merged on
this branch and ready for review.

## Shipped

| Component | Path | Verification |
|---|---|---|
| Application schema seed | [`schema/deep/application.sql`](../schema/deep/application.sql) | 40 nodes, 75 edges, 73 properties; loads + re-loads idempotently in DuckDB 1.5.2; `kg.v_observation_summary` view returns the expected wide row |
| `knowledge-graph-mcp` (read-only kg query MCP) | [`mcp/knowledge-graph-mcp/`](../mcp/knowledge-graph-mcp/README.html) | 12 MCP tools + 3 resources; 22/22 unit tests pass; smoke-tested against the live schema (572 nodes, 791 edges, 1027 properties loaded) |
| `great-az-tick-check-mcp` (mock submission tracking) | [`mcp/great-az-tick-check-mcp/`](../mcp/great-az-tick-check-mcp/README.html) | 5 tools + 2 resources; 10/10 tests; mock backend with a clean override path for the real Walker-lab API |
| `nws-heatrisk-mcp` (NWS HeatRisk + heat-index) | [`mcp/nws-heatrisk-mcp/`](../mcp/nws-heatrisk-mcp/README.html) | 7 tools + 2 resources; 17/17 heat-index tests against the canonical NWS table values; HeatRisk feed URL env-overridable |
| `agents/` — 8-agent pipeline | [`agents/`](../agents/) | 9 agent modules + orchestrator; 29 unit tests; both Scenario A (tick mail-in) and Scenario C (CHW heat check-in) run end-to-end through the stub agents and assert the expected `TriageDecision` + `Notification`; failing-agent degradation test passes |
| `app/` — Phase-0 UI prototype | [`app/`](../app/) | 10 static files (vanilla HTML+JS+CSS, no build); the full 6-step tick mail-in flow renders cleanly; mock backend short-circuits to a canned response so the success card always renders |

## Sub-agent MCP tool inventory (cross-check)

Each `agents/` module makes the following MCP calls — the
corresponding `mcp/<name>-mcp/` server should expose each:

| Server | Tool | Caller |
|---|---|---|
| `knowledge-graph-mcp` ✅ | `regions_at_point` | `GeoEnrichmentAgent` |
| `knowledge-graph-mcp` ✅ | `outbreak_check` | `EnrichmentAgent` (VBD), `KnowledgeUpdateAgent` |
| `vectorsurv-mcp` ✅ | `agency_region_intersect` | `GeoEnrichmentAgent` |
| `vectorsurv-mcp` ✅ | `get_pools` | `EnrichmentAgent` (VBD), `KnowledgeUpdateAgent` |
| `great-az-tick-check-mcp` ✅ | `create_submission` | `EnrichmentAgent` (mail-to-walker-lab branch) |
| `nws-heatrisk-mcp` ✅ | `heatrisk` | `EnrichmentAgent` (Heat), `KnowledgeUpdateAgent` |
| `mag-hrn-mcp` ⏳ | `search_centers` | `EnrichmentAgent` (cooling center) |
| `211-az-mcp` ⏳ | `transport_to_cooling_center` | `EnrichmentAgent` (dispatch) |

The two ⏳ servers fall through the orchestrator's failure-isolation
boundary today (observation still lands, with a `failed_tools`
record). They're queued for Phase 1.

## Follow-ups flagged by the sub-agents

These are real but small; bundling them into the next PR rather than
holding Phase 0:

1. **`schema/deep/outbreaks.sql`** references `pathogen.y_pestis` but
   `pathogens.sql` defines `pathogen.yersinia_pestis`. Pick one slug
   and update the other.
2. **`schema/deep/application.sql`** references
   `code.snomed.heatstroke` which isn't defined in `standards.sql`.
   Add the SNOMED catalog row.
3. **`schema/deep/counties.sql`** and **`tribes.sql`** lack
   `lat` / `lon` numeric properties, so
   `knowledge-graph-mcp.kg_regions_at_point` returns empty.
   Add a property-only follow-up seed (the tool already accepts
   `lat` / `latitude` / `centroid_lat` aliases).
4. **SNOMED catalog** in `standards.sql` is heatstroke-only; the
   application schema would benefit from `84362002` (heat exhaustion),
   `52613005` (heat cramp), `24079001` (heat syncope) so the heat
   symptoms in `application.sql` chain through SNOMED via the
   existing `crossReferences` edges.
5. **LOINC code nodes** for wearable observations
   (`code.loinc.heart_rate_8867_4`, etc.) so `wearable_metric.*` →
   `mappedTo` → LOINC works without storing the code as a string.

## Plan-document gaps the sub-agents flagged

While building, the agents found six places where the plan was
under-specified:

1. **Triage class list never enumerated** in `plan/03`. Should
   reference `schema/deep/application.sql` or list the ten `tc.*`
   classes inline.
2. **Heat vulnerability score lacks a full factor table.** Scenario
   C in `plan/03` showed five line items; a full `HEAT_SCORE_TABLE`
   covering age 65+, thermo-meds, energy insecurity, and Red /
   Orange HeatRisk levels should be pinned in `plan/01` or `plan/03`.
3. **`consent.tick_mailin`** suppression trigger ("unless the
   submitter has been bitten") isn't formal. The agent treats
   "any Human field already populated → keep them, else zero out."
4. **`AgentRun` audit-log schema** mentions input, output, model id,
   latency, cost but cost / token counts aren't on the model yet.
5. **Notification-ordering "life-threatening" set** isn't enumerated.
   `tc.call_911` is the only entry today; should `tc.urgent_care`
   join it?
6. **Phase-1 MCP slugs** (`mag-hrn-mcp`, `adhs-mcp`, `whispers-mcp`,
   `inaturalist-mcp`, `211-az-mcp`) are referenced by string by the
   orchestrator but don't have folders yet. They'll wire on first
   creation.

## What's next

Phase 0 is functionally complete. Phase 1 (per
[`05-roadmap.md`](./05-roadmap.html)) adds the Heat vertical's
mobile flows, the Cluster Detection Agent, and three more MCP
servers (`mag-hrn-mcp`, `adhs-mcp`, `211-az-mcp`).
