---
title: "onehealth-agents -- the eight-agent OneHealth pipeline"
---

# onehealth-agents

Python package that implements the eight-agent pipeline from
[`plan/03-agentic-architecture.md`](../plan/03-agentic-architecture.md).
Every community report, MCP pull, and agency case becomes a typed
`Observation` (Pydantic), routed through eight narrow-contract agents
that the rest of the team can swap out one at a time.

## Topology

```
   raw input (text | dict)
            |
            v
       IntakeAgent       (LLM-driven in prod; regex stub here)
            |
            v
  GeoEnrichmentAgent     (knowledge-graph-mcp.regions_at_point)
            |
            v
    ValidationAgent      (dedupe, spatial sanity, consent enforcement)
            |
            v
       TriageAgent       (HeatTriage | VBDTriage -- each gated by
            |             the tc.* enumeration from
            |             schema/deep/application.sql)
            v
     EnrichmentAgent     (vectorsurv-mcp, nws-heatrisk-mcp,
            |             mag-hrn-mcp, 211-az-mcp,
            |             great-az-tick-check-mcp, knowledge-graph-mcp)
            v
    NotificationAgent    (user / CHW / agency_analyst / 211 / center)
            |
            v
       Observation       (with .triage, .enrichments, .notifications,
                          .validation_status, .agent_runs populated)

  separately, on a schedule:
    KnowledgeUpdateAgent (nightly MCP pull -> Observation kind=mcp_pull)
    ClusterDetectionAgent (Poisson scan over the rolling buffer ->
                          ClusterAlert nodes; declared by humans, not us)
```

## Layout

| File | What it ships |
|---|---|
| `contracts.py` | One Pydantic model per Figure-2 class + the application-runtime extensions (heat symptoms, VBD exposure factors, consent profiles). The `TriageClass` and `ConsentProfile` enums mirror the `tc.*` and `consent.*` nodes seeded in `schema/deep/application.sql`. |
| `orchestrator.py` | `Orchestrator.process(raw)` -- runs the eight agents in order under per-agent `try`/`except` boundaries; populates `Observation.agent_runs`. |
| `intake.py` | `IntakeAgent` -- accepts dict or free text; routes consent profile per channel. |
| `geo.py` | `GeoEnrichmentAgent` -- MCP first, fallback ZCTA table. |
| `validation.py` | `ValidationAgent` -- dedupe + spatial bbox + consent suppression audit. |
| `triage.py` | `TriageAgent` dispatcher + `HeatTriage` (vulnerability score) + `VBDTriage` (candidate pathogen enumeration). Both branches output `tc.*` from the right subset only. |
| `enrichment.py` | `EnrichmentAgent` -- idempotent MCP hydration keyed on `(server, tool)`. |
| `notification.py` | `NotificationAgent` -- channel/audience selection; life-threatening flows surface agency first. |
| `cluster.py` | `ClusterDetectionAgent` -- Poisson scan stub per (vertical, ZCTA, window). |
| `update.py` | `KnowledgeUpdateAgent` -- shapes MCP records into `kind=mcp_pull` observations. |
| `mcp_client.py` | `MCPClient` protocol, `FakeMCPClient` (canned for the worked scenarios), `StdioMCPClient` (real `mcp`-package wrapper). |

## Quick start

```bash
pip install -e agents

# Run the worked scenarios end-to-end against the FakeMCPClient.
python agents/examples/scenario_a_tick.py
python agents/examples/scenario_c_heat.py

# Run the test suite -- offline, no network required.
pytest agents/tests
```

## Wiring up real MCP servers

```python
from onehealth_agents import Orchestrator, StdioMCPClient

mcp = StdioMCPClient(
    server_commands={
        "knowledge-graph-mcp": ["python", "-m", "knowledge_graph_mcp"],
        "nws-heatrisk-mcp":    ["python", "-m", "nws_heatrisk_mcp"],
        "vectorsurv-mcp":      ["python", "-m", "vectorsurv_mcp"],
        # ...
    }
)
orchestrator = Orchestrator(mcp=mcp)
```

## Extending

* **Add a new triage class:** seed it as a `tc.*` row in
  `schema/deep/application.sql`, then add the enum member in
  `contracts.TriageClass` and the subset frozenset
  (`HEAT_TRIAGE_CLASSES` or `VBD_TRIAGE_CLASSES`). The
  rule layer in `triage.py` is what gates the LLM output;
  unknown classes can't escape.
* **Add a new MCP server:** register a handler on
  `FakeMCPClient` for tests, and add a branch to `EnrichmentAgent.run`
  (or `KnowledgeUpdateAgent` for nightly pulls).
* **Replace a stub with a real LLM step:** every agent's `run()` (or
  `decide()` on Triage branches) is the only seam. The contracts
  freeze the in/out shape, so the LLM call has no other surface area
  to widen.
