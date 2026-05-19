---
title: "Plan 03 — Agentic architecture"
---

# 03 — Agentic architecture

The application is a pipeline of specialized LLM-driven agents that
turn a community report into a typed observation in the knowledge
graph, an enriched response back to the user, and an alert to the
right agency if needed. Each agent has a narrow contract, no shared
state, and a single MCP-or-graph dependency.

## Agent topology

```
                          ┌─────────────────────────┐
                          │     Intake Agent        │
                          │ free-text/voice/photo   │
                          │ → Minimum Dataset draft │
                          └──────────┬──────────────┘
                                     │
                          ┌──────────▼──────────────┐
                          │  Geo-Enrichment Agent   │
                          │ GPS → county/tribe/region│
                          │  knowledge-graph-mcp    │
                          └──────────┬──────────────┘
                                     │
                          ┌──────────▼──────────────┐
                          │   Validation Agent      │
                          │ dedupe, anomaly, photo  │
                          │   quality, consent      │
                          └──────────┬──────────────┘
                                     │
                          ┌──────────▼──────────────┐
                          │     Triage Agent        │
                          │ vertical-specific rule  │
                          │ + LLM judgement         │
                          └──────────┬──────────────┘
                                     │
                          ┌──────────▼──────────────┐
                          │   Enrichment Agent      │
                          │ pulls live MCP data,    │
                          │ attaches to observation │
                          └──────────┬──────────────┘
                                     │
              ┌──────────────────────┴──────────────────────┐
              │                                             │
              ▼                                             ▼
   ┌────────────────────┐                       ┌──────────────────────┐
   │ Notification Agent │                       │ Persistence (DuckLake)│
   │ user, CHW, agency  │                       │ observation + edges  │
   └────────────────────┘                       └──────────┬───────────┘
                                                           │
              ┌────────────────────────────────────────────┘
              │
              ▼
   ┌─────────────────────────────┐         ┌───────────────────────────┐
   │ Cluster Detection Agent     │ ◀──nightly──│  Knowledge Update Agent  │
   │ space-time anomalies        │         │  refresh kg from upstream │
   │ over recent observations    │         │  MCP servers              │
   └─────────────────────────────┘         └───────────────────────────┘
```

## Agent contracts

### 1. Intake Agent

| | |
|---|---|
| **Input** | Free text, voice transcript, photo, or structured form |
| **Output** | Minimum-Dataset draft: `{general, human, exposure, auxiliary, environmental, livestock?, wildlife?}` |
| **Model** | Claude Haiku (fast, cheap) with structured-output schema constrained to Figure 2 fields |
| **MCP** | None directly; reads the kg schema for the field list |
| **Decisions** | Vertical classification (vbd | heat | both | neither); consent-profile selection |
| **Failure mode** | "I couldn't parse this" → falls back to a structured form |

### 2. Geo-Enrichment Agent

| | |
|---|---|
| **Input** | Coordinates or ZIP from the intake draft |
| **Output** | Edges to `county.<slug>`, `tribe.<slug>` (if reservation match), `region.<id>` |
| **Model** | Deterministic SQL — no LLM unless the address is free-text |
| **MCP** | `knowledge-graph-mcp.regions_at_point(lat, lon)` |
| **Failure mode** | No exact match → "approximate" coordinate-precision flag (per Figure 2 General class) |

### 3. Validation Agent

| | |
|---|---|
| **Input** | Enriched draft |
| **Output** | One of `{accept, flag-for-review, reject}` + reasons |
| **Checks** | Dedupe (same uuid + 5-min window); spatial anomaly (report ≥ 50 mi from any known user activity); photo quality + species-range sanity (kg.taxonomy + photo-vision); consent-profile enforcement (suppress fields per the flow); tribal-data MOU check |
| **Model** | Claude Haiku for fuzzy checks; Python rules for the deterministic ones |
| **MCP** | `knowledge-graph-mcp` for taxonomy; vision LLM for photo |

### 4. Triage Agent

The vertical-specific brain.

**Enumerated triage classes** (canonical source:
`schema/deep/application.sql` `tc.*` nodes — the LLM step is gated to
choose only from this enumeration):

| Class | Vertical | Meaning |
|---|---|---|
| `tc.self_care` | VBD | Symptoms benign; self-monitor. |
| `tc.see_clinician` | VBD | Symptoms warrant a routine clinical visit. |
| `tc.urgent_care` | VBD | Symptoms + local signal warrant same-day care. |
| `tc.call_911` | Both | Life-threatening — call emergency services. |
| `tc.report_to_azgfd` | VBD | Wildlife mortality / unusual animal observation. |
| `tc.mail_to_walker_lab` | VBD | Tick submission for UA Cooperative Extension identification. |
| `tc.check_in_only` | Heat | Person is fine; outreach logs the contact and moves on. |
| `tc.drink_water_advisory` | Heat | Mild risk — advisory message + offer cooling-center info. |
| `tc.go_to_cooling_center` | Heat | Get the person to the nearest open cooling center. |
| `tc.dispatch_chw` | Heat | Send a Community Health Worker (or, with `tc.go_to_cooling_center`, dispatch transport). |

**VBD branch:**
- Match observed symptoms to `pathogen.*` nodes via the
  `causes` and `transmittedBy` edges seeded in
  `schema/deep/pathogens.sql`.
- For each candidate pathogen, fetch nearby pool positivity
  (`vectorsurv-mcp`), recent wildlife mortality
  (`whispers-mcp`), and any active outbreak record.
- Emit one (or more) of the VBD / Both triage classes above.

**Heat branch:**
- Compute an individualized **heat-vulnerability score** from the
  observation's General + Exposure + Auxiliary fields against the
  vulnerable-population nodes from `schema/heat.sql` (`pop.unsheltered`,
  `pop.older_adults`, `pop.outdoor_workers`, etc.).
- Pull current NWS HeatRisk for the user's location via
  `nws-heatrisk-mcp`.
- Emit one (or more) of the Heat / Both triage classes above.

**Heat vulnerability-score factor table** (the canonical
`HEAT_SCORE_TABLE` lives in
`agents/src/onehealth_agents/triage.py`; pin the point values here):

| Factor | Points |
|---|---|
| Currently unsheltered | +3 |
| Age 65+ | +2 |
| NWS HeatRisk **Magenta** today | +3 |
| NWS HeatRisk **Red** today | +2 |
| NWS HeatRisk **Orange** today | +1 |
| No working AC at home | +2 |
| Outdoor occupational exposure today (≥ 4 h) | +2 |
| Energy / utility insecurity | +1 |
| On thermoregulation-affecting medications | +1 |
| Chronic cardiovascular / renal disease | +1 |
| Symptomatic — heat-exhaustion features | +2 |
| Symptomatic — heat-stroke features (confusion, hot-dry skin) | +4 |
| No transport / no phone | +1 |

**Triage-class thresholds** (Heat branch, summed score):

| Score | Class |
|---|---|
| 0 – 2 | `tc.check_in_only` |
| 3 – 5 | `tc.drink_water_advisory` |
| 6 – 9 | `tc.go_to_cooling_center` |
| 10 – 12 | `tc.go_to_cooling_center` + `tc.dispatch_chw` (transport) |
| ≥ 13, or any heat-stroke feature | `tc.call_911` |

**Notification-priority set.** The "user-before-agency" rule has
exactly two exceptions where the agency channel fires first:
`tc.call_911` and any VBD case where the linked outbreak record is
lab-confirmed-positive (LCP). All other triage classes notify the user
first, then the agency dashboard pin (no PII).

**Consent-suppression triggers.**
- `consent.anonymous_heat` (default for CHW / outreach flows) —
  suppresses `param.email`, `param.phone_number`,
  `param.household_member_id`, `param.occupation`,
  `param.absent_work`, `param.absent_school`.
- `consent.tick_mailin` — keeps Exposure + Auxiliary; suppresses
  Human symptom fields **unless** any symptom field is already
  non-null at intake time (i.e., the submitter has been bitten
  with symptoms).
- `consent.wearable_only` — records only `auxiliary.digital_biomarker`
  + coarse postal-code geo; everything else suppressed.
- `consent.full_followup` — no suppression; explicit opt-in for the
  observation to be retrievable by the user later.

### 5. Enrichment Agent

| | |
|---|---|
| **Input** | Triaged observation |
| **Output** | Same observation with edges to live-data records (pool, alert, cooling-center, outbreak) |
| **Model** | LLM-orchestrated MCP tool calls |
| **MCP** | All of them — calls the right tools based on vertical + triage class |
| **Idempotent** | Repeated runs hydrate the same edges, don't duplicate |

### 6. Notification Agent

| | |
|---|---|
| **Input** | Triaged + enriched observation |
| **Output** | Notifications to user, CHW, agency analyst, or 211 line |
| **Channels** | App push, SMS, voice callback, agency dashboard pin |
| **Prioritization** | User notification before agency notification *except* for life-threatening triage classes (call-911, lab-confirmed-positive outbreak) |
| **Localization** | English / Spanish / Diné Bizaad / Tohono O'odham — falls back to image-rich card if literacy is a barrier |

### 7. Cluster Detection Agent

| | |
|---|---|
| **Input** | Rolling window of `observation` nodes |
| **Output** | New `outbreak.<slug>` nodes when a space-time anomaly crosses threshold |
| **Algorithm** | SaTScan-style scan statistic on observations per ZCTA per week, vertical-scoped (don't merge VBD + Heat clusters) |
| **Cadence** | Hourly during heat season, daily otherwise |
| **MCP** | Writes back via `knowledge-graph-mcp` |
| **Backstop** | Always defers final outbreak declaration to human review at ADHS / AZGFD (per Figure 3 *Verify* milestone) |

### 8. Knowledge Update Agent

| | |
|---|---|
| **When** | Nightly + on-demand |
| **What** | Pulls recent records from every MCP (vectorsurv pools, whispers events, ADHS reports) and adds them as `observation` nodes with `source = "mcp_pull"` |
| **Why** | Keeps the kg current so community reports can be evaluated against fresh agency context. This is *the* property that makes the database "living." |
| **MCP** | Every MCP server with a list/query endpoint |

## Why agents and not a monolith

- **Auditability.** Every agent's decision is a row in an
  `agent_run` table with the schema:

  | Column | Type |
  |---|---|
  | `run_id` | uuid |
  | `agent_name` | text |
  | `observation_id` | uuid (FK → `observation.*`) |
  | `started_at` / `ended_at` | timestamp |
  | `model_id` | text (e.g. `claude-haiku-4-5`, `claude-sonnet-4-6`) |
  | `prompt_tokens` / `completion_tokens` / `cache_read_tokens` / `cache_creation_tokens` | int |
  | `cost_usd` | numeric |
  | `latency_ms` | int |
  | `outcome` | text (`success` / `degraded` / `error`) |
  | `input_digest` / `output_digest` | text (sha256 of canonical JSON) |
  | `error_message` | text (nullable) |

  Figure 3 timeliness milestones become joins against this table.
- **Failure isolation.** If `whispers-mcp` is down, the Enrichment
  Agent drops that edge but the observation still lands. A
  monolithic prompt would refuse the whole report.
- **Replaceability.** Each agent has a narrow contract; the Triage
  Agent can be swapped for a domain expert's rule engine without
  touching Intake or Notification.
- **Cost shaping.** Cheap models (Haiku) on high-volume agents
  (Intake), expensive models (Opus) only on the Triage and Cluster
  Detection agents where the stakes are highest.

## Where Claude Code itself fits

The agents above run in production. **Claude Code** runs in this
repository — drafting the schema seeds, adding new MCP servers,
keeping the docs in sync. Production agents and Claude Code share
the same MCP surface, so a fix prototyped in the IDE (e.g. "add a
new test_target to the knowledge graph and re-deploy") is one PR
away from production.
