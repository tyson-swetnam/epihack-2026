---
title: "Changelog"
---

# Changelog

All notable changes to the EpiHack Arizona 2026 repository, grouped
by the five roadmap phases in
[`plan/05-roadmap.md`](./plan/05-roadmap.md). PR numbers correspond
to <https://github.com/tyson-swetnam/epihack-2026/pulls>.

This changelog tracks the rollups that actually landed on `main`;
some PRs (notably the omnibus PR #8) span multiple phases and are
listed under each phase whose deliverables they contain.

## Phase 0 — Hackathon MVP (week 0–2)

Scope: figures + knowledge-graph foundation, one vertical (VBD), one
happy path (mail-in tick), three MCPs, one agent pipeline.

* **PR #1** — Add EpiHack Arizona 2026 reference figures (Figures
  1-4) as structured Markdown with RDF-style triples, plus the
  initial `schema/knowledge_graph.sql` property-graph seed.
* **PR #2** — Add the Wildlife & Vector-Borne Diseases focus-group
  section (`wildlife/`) with four guiding questions and a 30+
  resource catalog.
* **PR #3** — Add the MapLibre GL map and Cytoscape pathogen
  knowledge-graph viewer (`map/`, `graph/`).
* **PR #4** — Land focus groups, the deep AZ data catalog (counties /
  tribes / pathogens / outbreaks / datasets / standards / mcp_servers
  seeds), the interactive map + graph viewers, and the first
  `vectorsurv-mcp` (7 tools).
* **PR #5** — Make `vectorsurv-mcp` endpoint paths env-overridable
  (`VECTORSURV_PATH_*`) so a path drift can be patched without a code
  change.
* **PR #6** — Align `vectorsurv-mcp` with the live OpenAPI spec
  v1.0.44 (Mongoose-style `query[...]` operators, `/v1/` prefix, new
  agency-region-intersect / region / test-target / pools-are-positive
  / case-count tools — 13 tools total). Snapshot the spec under
  `mcp/vectorsurv-mcp/openapi/`.
* **PR #7** — Mobile-responsive map and pathogen-graph viewers
  (flexbox + ≤800px breakpoint + collapsible panel, MapLibre touch
  tuning, Cytoscape pinch-zoom).
* **PR #8 (Phase 0 slice)** — Land the Phase 0 application MVP:
  `app/` tick mail-in flow end-to-end, `agents/` 8-agent pipeline
  (Intake → Geo-Enrichment → Validation → Triage → Enrichment →
  Notification → background Cluster Detection + Knowledge Update),
  `mcp/great-az-tick-check-mcp/` (5 tools), `mcp/knowledge-graph-mcp/`
  (12 tools + SQL escape-hatch), `schema/deep/application.sql`.

## Phase 1 — Heat vertical (month 1–2)

Scope: add the Heat vertical and three more MCPs.

* **PR #8 (Phase 1 slice)** — `mcp/nws-heatrisk-mcp/` (7 tools — NWS
  API + WPC HeatRisk gridded product), `mcp/mag-hrn-mcp/` (5 tools —
  MAG Heat Relief Network with env-overridable ArcGIS Feature
  Service URL), `mcp/adhs-mcp/` (6 tools — canned ADHS heat-mortality
  + arbovirus + reportable conditions). Triage Agent's Heat branch
  with the pinned `HEAT_SCORE_TABLE` and triage-class enumeration.
  Three new app flows: CHW heat check-in, anonymous heat self-report,
  "where can I cool off?". Notification Agent SMS + Spanish bundle.
  Cluster Detection Agent (vertical-scoped, hourly during heat
  season).

## Phase 2 — Tribal partnerships + offline (month 3–6)

Scope: tribal partner engagement, offline + low-bandwidth modes,
linguistic surface, data-sovereignty guardrails. The data-sharing
agreements themselves (MOU / DUA with ITCA-TEC) are external
partnership work and are not on this changelog; the code-level
slice is below.

* **PR #8 (Phase 2 slice)** — `mcp/whispers-mcp/` (6 tools — USGS
  wildlife mortality; canned events including 1993 Four Corners, 2022+
  HPAI, 2024-25 plague), `mcp/inaturalist-mcp/` (6 tools — AZ
  citizen-science observations, place_id 53), `mcp/211-az-mcp/` (6
  tools — referrals + transport dispatch with in-memory dispatch
  tracking), `mcp/sms-entry-mcp/` (6 tools — SMS-only intake with
  pure-function Twilio HMAC verification). PWA offline + sync queue
  via IndexedDB in `app/shared/sync.js` + service worker (`app/sw.js`)
  with three caching strategies and iOS Safari manual-retry fallback.
  Validation Agent row-level tribal-data suppression at write time.
  i18n bundles: English, Spanish (high-coverage), Diné Bizaad +
  Tohono O'odham placeholder bundles flagged for native-speaker
  review. `whispers-mcp` + `inaturalist-mcp` wired into the VBD
  enrichment branch.

## Phase 3 — Maricopa + Coconino pilot (month 6–9)

Scope: real users, real reports, evaluation against Figure 3
timeliness milestones.

* **PR #8 (Phase 3 slice)** — `dashboard/` four-audience analyst
  workspace for ADHS / MCDPH / AZGFD / Coconino HHS with status
  cards, cluster feed, lazy-loaded MapLibre embed, sparkline
  case-count tables, and a SQL preview round-tripping to
  `knowledge-graph-mcp`. `today/` public-facing aggregated dashboard
  with HeatRisk + 7-day strip, county-level WNV pool-positivity
  sparkline, recent wildlife signals, statewide five-number rollup;
  local AZ-bbox county detection so coordinates never leave the
  device. `schema/deep/audit.sql` plus
  `agents/src/onehealth_agents/audit.py` — `kg.agent_run` table
  (17 columns) and views `kg.v_observation_timeliness`,
  `kg.v_agent_run_cost`, `kg.v_agent_run_failures`. Per-million-token
  prices pinned for Haiku 4.5 / Sonnet 4.6 / Opus 4.7
  (env-overridable). Cluster-detection calibration: two-tier
  deterministic-Poisson + Bayesian Gamma-Poisson detector calibrated
  against 14 historical AZ outbreaks (`schema/deep/outbreaks.sql`);
  100% sensitivity on evaluable outbreaks, 0.0000 FP-rate per
  agency-week across 4,114 simulated null weeks
  (`plan/CLUSTER-CALIBRATION.md`). `mcp/wearable-mcp/` (4 tools —
  mock-only HealthKit / Health Connect adapter, on-device privacy
  posture).

## Phase 4 — Statewide + evaluation (month 9–12)

Scope: open-source release + governance handoff. The 15-county
rollout, the federated cluster-detection prototype with tribal
partners, the wearable HealthKit / Health Connect production
integration, and the independent annual evaluation report are
external work tracked outside this repo.

* **PR #8 (Phase 4 slice)** — `mcp/wearable-mcp/` mock scaffold (4
  tools) so the wearable contract can be exercised end-to-end
  without a real device. SMS contract refinements
  (160-char body cap; PWA photo-blob persistence via IndexedDB).
* **This release** — open-source release prep: `LICENSE`,
  `CONTRIBUTING.md`, `GOVERNANCE.md` (standing review board: ADHS /
  AZGFD / ITCA-TEC / Maricopa Vector Control + tribal-partner veto +
  sunset clauses), `SECURITY.md` (five-class threat model +
  known-gaps register), `CHANGELOG.md`, `mcp/README.md` index, and
  the `NOTICE` attribution roll-up.

## Next

Open items pulled from
[`plan/EXECUTION-STATUS-PHASE-1-2.md`](./plan/EXECUTION-STATUS-PHASE-1-2.md)
and [`plan/CLUSTER-CALIBRATION.md`](./plan/CLUSTER-CALIBRATION.md).

### Phase 2 — tribal partnerships + offline

* MOU / DUA framework with ITCA-TEC (external partnership work).
* Optional `navajo-ec-mcp` proxy, gated behind a signed tribal DUA —
  not built speculatively. Sunset clause encoded in
  [`GOVERNANCE.md`](./GOVERNANCE.md).
* Indigenous-language UI translations for Diné Bizaad and Tohono
  O'odham (placeholder bundles + switcher are wired; native-speaker
  review is outside the agentic-build scope).
* SMS-only entry point operationally connected to a Twilio short
  code (the `sms-entry-mcp` server is in place; the gateway flip
  from `SMS_MODE=mock` to `SMS_MODE=twilio` is pending agency
  procurement).

### Phase 3 — Maricopa + Coconino pilot

* Aggregation-MCP wishlist surfaced by the analyst dashboard:
  `kg_observations_by_window`, `kg_cluster_scan`,
  `kg_milestone_intervals`, `kg_normalize_diagnosis`. These are
  read-only views over `kg.agent_run` + `kg.observation`.
* Quarterly tribal-data suppression tabletop review — required by
  Plan 02 but not yet scheduled.
* CHW + 211 satisfaction surveys for the success-criterion check.

### Phase 4 — statewide + evaluation

* 15-county rollout.
* Federated cluster-detection prototype letting tribal partners
  contribute model gradients without releasing line data.
* Wearable production integration (HealthKit + Health Connect —
  on-device-only, per-metric consent, replacing the `wearable-mcp`
  mock layer with a real device-side bridge).
* Independent annual evaluation report scored against Figure 3
  milestones.

### Cluster-detection follow-ups (from `plan/CLUSTER-CALIBRATION.md`)

* Single-case high-CFR alert tier for `Y. pestis`, hantavirus, viral
  haemorrhagic fevers, anthrax — the 8 documented historical misses
  cannot be caught by a ZCTA-bucketed count scan by construction.
* County- or `region.*`-level scan tier for chronic low-incidence
  pathogens and ZCTA-boundary-straddling cases.
* Multi-seed calibration sweep (~100 seeds) to report mean / variance
  of sensitivity and lag, replacing the current single-seed numbers.
* Pathogen-hint backfill from `mcp_pull` payloads so the
  historical-match back-reference does not fall back to nearest-in-
  time-and-space when the Triage Agent did not run.

### Security follow-ups (from `SECURITY.md`)

* Replace the placeholder vulnerability-disclosure address with a
  published `security@` mailbox and a GitHub Security Advisory
  configuration at v1.0 handoff.
* Add a Content Security Policy to the static site (Jekyll
  `_includes`) restricting script sources to unpkg + self.
* Publish a CycloneDX SBOM alongside [`NOTICE`](./NOTICE).
