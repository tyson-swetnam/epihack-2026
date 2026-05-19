---
title: "Phase 1 + 2 execution status"
---

# Phase 1 + 2 — execution status

Six more sub-agents have reported in. All Phase 1 and the
independent slice of Phase 2 (the two non-tribal MCP servers) are
merged on this branch.

## Shipped since Phase 0

### Phase 1 — Heat vertical

| Component | Path | Verification |
|---|---|---|
| `mag-hrn-mcp` (MAG Heat Relief Network) | [`mcp/mag-hrn-mcp/`](../mcp/mag-hrn-mcp/) | **5 tools + 2 resources**, 35/35 offline tests, 12 canned Phoenix-metro cooling centers; `MAG_HRN_FEATURE_SERVICE_URL` env-overrides to the live ArcGIS Feature Service at `geo.azmag.gov/arcgis/rest/services/maps/Heat_Relief_Network/MapServer` |
| `adhs-mcp` (ADHS surveillance summaries) | [`mcp/adhs-mcp/`](../mcp/adhs-mcp/) | **6 tools + 2 resources**, 46/46 tests; canned data sourced from `heat/04-vulnerable-populations.md`, `schema/heat.sql`, and `schema/deep/standards.sql` (990 deaths in 2023, 602 in 2024, ≥4,320 cumulative, 4,298 ER visits/year) |
| `211-az-mcp` (referrals + dispatch) | [`mcp/211-az-mcp/`](../mcp/211-az-mcp/) | **6 tools + 2 resources**, 23/23 tests; in-memory dispatch tracking with chain-of-call consistency; `AZ211_BACKEND_URL` env-override for a real API later |
| **Heat app flows** | [`app/heat/`](../app/heat/) | 3 new flows shipped (CHW check-in, anonymous self-report, "where can I cool off?"); 19 endpoints serve HTTP 200; node --check + html5lib strict + JSON validators all clean; 44×44 touch targets; Spanish bundle via `app/shared/i18n.js`; vulnerability-score thermometer; two-tap confirm-before-dispatch transport button |

### Phase 2 (independent slice) — Wildlife / citizen-science

| Component | Path | Verification |
|---|---|---|
| `whispers-mcp` (USGS wildlife mortality) | [`mcp/whispers-mcp/`](../mcp/whispers-mcp/) | **6 tools + 2 resources**, 15/15 tests; 10 canned events including 1993 Four Corners hantavirus, 2022-23 HPAI, 2024-25 plague, EHDV mule deer near Patagonia; base URL `https://whispers.usgs.gov/api` (env-overridable); silent canned-fallback on network errors |
| `inaturalist-mcp` (citizen-science observations) | [`mcp/inaturalist-mcp/`](../mcp/inaturalist-mcp/) | **6 tools + 2 resources**, 20/20 tests; 21 canned observations covering ticks, mosquitoes, fleas, and rodent reservoirs; AZ `place_id=53`; `INAT_USER_AGENT` requirement enforced at startup |

## Schema follow-ups all merged

The five small follow-ups the Phase 0 sub-agents flagged are now in:

1. **`outbreaks.sql` slug fix** — `pathogen.y_pestis` → `pathogen.yersinia_pestis` (the Coconino 2025 plague outbreak row was orphaning).
2. **`knowledge-graph-mcp` loader order** — pins `deep/standards.sql` and `deep/pathogens.sql` to load *before* the rest of `deep/*.sql` alphabetically, so the SNOMED/ICD-10 crossReferences and pathogen FKs find their parents.
3. **`schema/deep/followups.sql`** — adds SNOMED heat-illness codes (84362002, 52613005, 24079001), LOINC wearable codes (8867-4, 8310-5, 8328-7, 80404-7, 41950-7), and `lat`/`lon` numeric properties on every county.* and tribe.* node (centroid coords from `map/data.js`). Edge IDs 30000-30199.
4. **plan/03 tightening** — triage-class enumeration as a 10-row table, full HEAT_SCORE_TABLE pinned with point values and triage thresholds, formal consent-suppression triggers per profile, full `agent_run` audit-log schema including the four token kinds and input/output digests.
5. **Orchestrator alignment** — `agents/enrichment.py` + `agents/geo.py` + `agents/update.py` + `agents/mcp_client.py` updated to use the canonical per-server-prefixed tool names (`kg_outbreak_check`, `vectorsurv_get_pools`, `gattc_create_submission`, `nws_heatrisk`, `mag_search_centers`, `az211_transport_to_cooling_center`); 29/29 tests pass.

## Updated sub-agent → MCP tool cross-check

Every tool the `agents/` orchestrator calls is now backed by a shipped
MCP server with the matching prefixed name:

| Server | Tool | Status |
|---|---|---|
| `knowledge-graph-mcp` | `kg_regions_at_point` | ✅ |
| `knowledge-graph-mcp` | `kg_outbreak_check` | ✅ |
| `vectorsurv-mcp` | `vectorsurv_agency_region_intersect` | ✅ |
| `vectorsurv-mcp` | `vectorsurv_get_pools` | ✅ |
| `great-az-tick-check-mcp` | `gattc_create_submission` | ✅ |
| `nws-heatrisk-mcp` | `nws_heatrisk` | ✅ |
| `mag-hrn-mcp` | `mag_search_centers` | ✅ |
| `211-az-mcp` | `az211_transport_to_cooling_center` | ✅ |

`whispers-mcp` and `inaturalist-mcp` are shipped but not yet wired
into `agents/enrichment.py` — wiring them is one small commit
queued as Phase 2 follow-up (add the bbox calls under the VBD branch).

## What's left

### Phase 2 — Tribal partnerships + offline

- MOU / DUA framework with ITCA-TEC (external; partnership work).
- Optional `navajo-ec-mcp` proxy (gated behind tribal DUA — not built
  speculatively).
- App offline / sync-on-reconnect for the field flows.
- SMS-only entry point via a short code.
- Indigenous-language UI: Diné Bizaad, Tohono O'odham (with
  native-speaker review — outside the agentic-build scope).
- Validation Agent: row-level tribal-data suppression at write time.
- Wire `whispers-mcp` + `inaturalist-mcp` calls into
  `agents/src/onehealth_agents/enrichment.py`.

### Phase 3 — Maricopa + Coconino pilot

- Agency dashboards for MCDPH / ADHS / AZGFD / Coconino HHS.
- `agent_run` audit table materialized in the DuckLake catalog with
  the Figure-3 milestone join queries.
- Public-facing aggregated dashboard.
- Calibration of cluster-detection thresholds against the historical
  outbreaks already encoded in `schema/deep/outbreaks.sql`.

### Phase 4 — Statewide + evaluation

- 15-county rollout.
- Federated cluster detection with tribal partners.
- Wearable integration (HealthKit / Health Connect).
- Independent evaluation report scored against the Figure 3
  timeliness intervals.
