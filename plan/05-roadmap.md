---
title: "Plan 05 — Roadmap"
---

# 05 — Roadmap

Five phases from hackathon MVP to a 12-month pilot evaluation. Each
phase ships shippable artifacts and is judged by an explicit
success criterion tied back to the
[Figure 3 timeliness milestones](../figures/03-outbreak-timeliness-metrics.html).

## Phase 0 — Hackathon MVP (week 0–2)

**Scope.** One vertical (VBD), one happy path (mail-in tick), three
MCPs, one agent pipeline.

| Ship | Owner |
|---|---|
| `schema/deep/application.sql` — new node types: `observation`, `symptom`, `exposure_factor`, `consent_profile`, `wearable_metric` | repo |
| `mcp/great-az-tick-check-mcp/` — submission tracking + species feedback (mock if Walker lab API isn't ready) | repo |
| `mcp/knowledge-graph-mcp/` — read-only kg query over DuckLake (`regions_at_point`, `pathogen_by_vector`, `outbreak_check`) | repo |
| `app/` — Next.js / React Native shell with the **tick mail-in flow** end-to-end | repo |
| **Agents:** Intake, Geo-Enrichment, Validation, Triage (VBD only), Enrichment (vectorsurv + greatAZtickcheck + kg), Notification (in-app + email) | repo |
| Live integration with `vectorsurv-mcp` for nearby pool context | already shipped |

**Success criterion.** A user can mail in a tick using the app in
under 3 minutes from open-to-confirmation, with a mailing label
and a 14-day symptom watchlist generated. The observation lands
in the kg with edges to pathogen, county, resource, and focus
nodes. Detect milestone fires automatically.

## Phase 1 — Heat vertical (month 1–2)

**Scope.** Add the Heat vertical and three more MCPs.

| Ship | |
|---|---|
| `mcp/nws-heatrisk-mcp/` — daily HeatRisk + active alerts | new |
| `mcp/mag-hrn-mcp/` — Heat Relief Network locations + (where available) supply / occupancy | new |
| `mcp/adhs-mcp/` — read-only ADHS arbovirus + heat-mortality summaries | new |
| Triage Agent — Heat branch with the vulnerability-score model | extend |
| App — three new flows: **CHW heat check-in**, **anonymous heat self-report**, **"where can I cool off?"** | extend |
| Notification Agent — SMS fallback + Spanish localization | extend |
| Cluster Detection Agent (vertical-scoped, hourly during heat season) | new |

**Success criterion.** A CHW with the field app can take an
unsheltered check-in and dispatch transport to a cooling center in
under 90 seconds. A clustering of 5 heat-exhaustion check-ins in
one ZCTA / 2 h triggers a county heat-emergency alert to MCDPH.

## Phase 2 — Tribal partnerships + offline (month 3–6)

**Scope.** Engage tribal partners, add offline + low-bandwidth modes,
expand the linguistic surface, and harden data-sovereignty guardrails.

| Ship | |
|---|---|
| MOU + DUA framework with ITCA-TEC | external |
| Optional `navajo-ec-mcp` proxy, gated by tribal DUA | new (gated) |
| Field app: full offline capture, sync-on-reconnect | extend |
| SMS-only flow for users with no smartphone (Twilio / agency short code) | new |
| Multi-lingual UI: Spanish, Diné Bizaad, Tohono O'odham (with native-speaker review) | extend |
| Validation Agent: row-level tribal-data suppression at write time | extend |
| `whispers-mcp` and `inaturalist-mcp` for wildlife mortality + citizen-science context | new |
| `211-az-mcp` for utility-assistance + transport referrals | new |

**Success criterion.** A pilot tribal community can use the app
end-to-end in the local language without uploading any data to
shared infrastructure unless explicitly opted in. Tribal-data
suppression audit passes a tabletop review.

## Phase 3 — Maricopa + Coconino pilot (month 6–9)

**Scope.** Real users, real reports, evaluation against Figure 3
timeliness milestones.

| Ship | |
|---|---|
| Agency dashboard for MCDPH, ADHS, AZGFD, Coconino HHS | new |
| `agent_run` audit table + Figure-3-milestone joins | new |
| Cluster-detection thresholds calibrated to historical AZ data (1993 Four Corners, 2021 Maricopa WNV, 2023/2024 heat seasons, 2025 Coconino plague) | calibration |
| Public-facing aggregated dashboard ("AZ One Health Today") | new |
| `inaturalist-mcp` + AZGFD wildlife-mortality cross-references on every wildlife observation | extend |

**Success criterion.** During the heat season and the WNV season,
the median **Detect → Notify** interval for reports flowing
through the app is at least 30% shorter than the 2024 baseline
for the same counties. CHW + 211 satisfaction surveys ≥ 4 / 5.

## Phase 4 — Statewide + evaluation (month 9–12)

**Scope.** Statewide expansion, federated learning with tribal
partners, formal evaluation.

| Ship | |
|---|---|
| 15-county deployment | rollout |
| Federated cluster-detection that lets tribal partners contribute model gradients without releasing line data | new |
| Wearable integration: HealthKit + Health Connect skin-temp, HRV, sweat-rate (for Heat) | new |
| Annual evaluation report scored against Figure 3 milestones, with sector-by-sector intervals | external |
| Open-source release notes + governance handoff | external |

**Success criterion.** Independent evaluation against the Figure 3
milestone framework shows measurable timeliness improvement for
both verticals, with no significant disparities by county, tribal
status, or demographic group.

## Cross-cutting tracks

These run across every phase.

- **Governance.** ADHS / AZGFD / ITCA-TEC / Maricopa Vector
  Control as the standing review board. All algorithmic changes
  pass through this group before deployment.
- **Privacy & consent.** Quarterly audits of the
  `consent_profile` enforcement; immediate-revoke pathway for
  any user.
- **Cost.** Cap on per-report LLM spend, with cheap models on
  high-volume agents (Intake = Haiku) and expensive models only
  where stakes are highest (Triage on potentially severe cases =
  Opus / Sonnet).
- **Bias monitoring.** Disparity dashboards by demographic and
  geography reviewed monthly.
- **Open data.** Wherever upstream licensing allows, aggregated
  outputs are republished back into the open-data ecosystem
  (GBIF, HealthData.gov, the
  [`schema/deep/datasets_apis.sql`](../schema/deep/datasets_apis.sql)
  catalog).

## Risk register (top five)

| Risk | Mitigation |
|---|---|
| Upstream API drift breaks an MCP integration | Versioned OpenAPI snapshots in each `mcp/<name>/openapi/`; nightly diff alerts; env-overridable paths so a fix is deploy-without-rebuild |
| VectorSurv credentials expire / rotate | MCP server runs token refresh; key rotation playbook documented in each `.env.example` |
| Tribal partners object to a feature | Governance board has hard veto; tribal-data MOU is opt-in per tribe |
| LLM hallucinates a triage class | Triage Agent's output is gated by a deterministic rule layer that maps {pathogen, vulnerability, current-MCP-readings} to a small enumerated class — LLM can only choose from the enumeration |
| Cost / token blow-up under heat-season load | Per-agent budgets in the orchestrator; Intake uses Haiku exclusively; aggressive caching of MCP responses |
