# 05 · Orchestrate the agents

!!! note "Stub"
    Authored in Phase 3. Source: `plan/03-agentic-architecture.md`,
    `plan/04-data-flows.md`, `agents/src/onehealth_agents/`.

## What we wanted

A clear, testable orchestrator that turns an anonymous mobile report into
a triage decision, a knowledge-graph write, and (when appropriate) an
agency notification — without ever diagnosing the user, ever logging raw
observations, and ever leaking precise geo.

## What we built

Eight Pydantic v2 agents behind a FastAPI surface:

1. **IntakeAgent** — schema validation, channel detection.
2. **GeoAgent** — coarsen lat/lon → ZIP or 1 km grid.
3. **ValidationAgent** — privacy contract, EXIF rejection, tribal
   suppression default.
4. **TriageAgent** — never-diagnose routing decisions.
5. **EnrichmentAgent** — MCP fan-out to fetch HeatRisk, cooling centers,
   vector activity, etc.
6. **NotificationAgent** — agency routing.
7. **ClusterAgent** — ZCTA-week / ZCTA-2h aggregation.
8. **KnowledgeUpdateAgent** — writes back to the kg.

## What it looks like

_Screenshots land here from Phase 5._

## Decisions & trade-offs

To be authored.

## Where to go next

[06 · Ship the app →](06-app.md)
