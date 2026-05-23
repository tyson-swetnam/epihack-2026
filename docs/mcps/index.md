# MCP servers

Eleven [FastMCP](https://github.com/jlowin/fastmcp) servers, each
wrapping one data source as a set of LLM-callable tools. All eleven run
standalone (`python -m <package>`), share a uniform layout (copied from
`mcp/vectorsurv-mcp/` as the template), and pass tests offline.

!!! info "Naming convention"
    MCP tool names carry a server prefix — `vectorsurv_*`, `kg_*`,
    `mag_*`, `az211_*`, `gattc_*`, `nws_*`, `whispers_*`, `inat_*`,
    `adhs_*`, `sms_*`, `wearable_*`. The orchestrator dispatches on the
    prefix; **collisions silently break the four worked data flows
    A/C/D**, so new servers must pick a fresh prefix.

| Server | Wraps | Tools | Phase |
|---|---|---|---|
| [vectorsurv-mcp](vectorsurv.md) | VectorSurv mosquito/tick API (v1.0.44) | 13 | VBD |
| [knowledge-graph-mcp](knowledge-graph.md) | DuckDB property graph (572 / 791 / 1027) | 12 | both |
| [nws-heatrisk-mcp](nws-heatrisk.md) | NWS HeatRisk + heat-index | 7 | heat |
| [mag-hrn-mcp](mag-hrn.md) | MAG Heat Relief Network | 5 | heat |
| [adhs-mcp](adhs.md) | ADHS public surveillance | 6 | both |
| [211-az-mcp](211-az.md) | 211 Arizona referrals | 6 | heat |
| [whispers-mcp](whispers.md) | USGS WHISPers wildlife events | 6 | VBD |
| [inaturalist-mcp](inaturalist.md) | iNaturalist citizen-science | 6 | VBD |
| [great-az-tick-check-mcp](great-az-tick-check.md) | UA Cooperative Extension tick check | 5 | VBD |
| [sms-entry-mcp](sms-entry.md) | Twilio SMS intake | 6 | both |
| [wearable-mcp](wearable.md) | HealthKit / Health Connect | 4 | heat |

## Standalone use

Each server has a `pyproject.toml` and runs via `uv`:

```bash
cd mcp/<server>
uv sync
uv run pytest          # all offline, canned data on connection error
python -m <package>    # speak MCP over stdio
```

## Used by the orchestrator

`agents/src/onehealth_agents/mcp_client.py` dispatches every tool call
on the server prefix. See the [eight-agent topology](../architecture/agents.md)
for which agent calls which server.

## Used by Claude.ai as custom connectors

`vectorsurv-mcp` is configured to run over `streamable-http` on the
Jetstream2 VM and is registered with Claude.ai as a custom connector.
See [`mcp/vectorsurv-mcp/README.md`](https://github.com/tyson-swetnam/epihack-2026/blob/main/mcp/vectorsurv-mcp/README.md)
for the operator runbook.
