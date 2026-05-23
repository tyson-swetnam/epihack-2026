# Data flows (A / B / C / D)

!!! note "Stub"
    Authored in Phase 3. Source: [`plan/04-data-flows.md`](https://github.com/tyson-swetnam/epihack-2026/blob/main/plan/04-data-flows.md).

The four worked scenarios that every agent + MCP combination is sized to
support:

| | Scenario | Path |
|---|---|---|
| A | Tick photo from a mobile reporter | `app → IntakeAgent → GeoAgent → ValidationAgent → TriageAgent → mail-in instructions` |
| B | Cluster detection over a quiet ZCTA-week | `ClusterAgent → kg.alert → NotificationAgent → ADHS/MCDPH` |
| C | Heat-strain wearable signal | `wearable-mcp → EnrichmentAgent (NWS HeatRisk + MAG HRN) → 211-az-mcp` |
| D | Agency analyst SQL through the dashboard | `dashboard → knowledge-graph-mcp (SELECT-only)` |

The scenarios are wired end-to-end against `FakeMCPClient` (no network)
in `agents/examples/scenario_*.py`.
