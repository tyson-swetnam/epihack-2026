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

**VBD branch:**
- Match observed symptoms to `pathogen.*` nodes via the
  `causes` and `transmittedBy` edges seeded in
  `schema/deep/pathogens.sql`.
- For each candidate pathogen, fetch nearby pool positivity
  (`vectorsurv-mcp`), recent wildlife mortality
  (`whispers-mcp`), and any active outbreak record.
- Emit a triage class: `{self-care, see-clinician, urgent-care,
  report-to-AZGFD, mail-tick-to-walker-lab}`.

**Heat branch:**
- Compute an individualized **heat-vulnerability score** from the
  observation's General + Exposure + Auxiliary fields against the
  vulnerable-population nodes from `schema/heat.sql` (`pop.unsheltered`,
  `pop.older_adults`, `pop.outdoor_workers`, etc.).
- Pull current NWS HeatRisk for the user's location via
  `nws-heatrisk-mcp`.
- Emit a triage class: `{check-in-only, drink-water-advisory,
  go-to-cooling-center, call-911, dispatch-CHW}`.

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
  `agent_run` table with input, output, model id, latency, and
  cost. The Figure 3 timeliness milestones become joins against
  that table.
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
