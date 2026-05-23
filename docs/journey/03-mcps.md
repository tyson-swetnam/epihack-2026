# 03 · Build the MCPs

!!! note "Stub"
    Authored in Phase 3. Source: `mcp/README.md`,
    `plan/02-mcp-integration.md`, every `mcp/<server>/README.md`.

## What we wanted

Eleven LLM-callable data adapters that the agent orchestrator can dispatch
on a per-prefix basis — `vectorsurv_*`, `kg_*`, `mag_*`, `az211_*`,
`gattc_*`, `nws_*`, `whispers_*`, `inat_*`, `adhs_*`, `sms_*`, `wearable_*` —
all testable offline.

## What we built

Eleven FastMCP servers, all built from the `mcp/vectorsurv-mcp/` template:

| Server | Wraps | Tools |
|---|---|---|
| [vectorsurv-mcp](../mcps/vectorsurv.md) | VectorSurv mosquito/tick surveillance | 13 |
| [knowledge-graph-mcp](../mcps/knowledge-graph.md) | DuckDB property graph (572 nodes / 791 edges) | 12 |
| [nws-heatrisk-mcp](../mcps/nws-heatrisk.md) | NWS HeatRisk + heat-index calculator | 7 |
| [mag-hrn-mcp](../mcps/mag-hrn.md) | MAG Heat Relief Network cooling centers | 5 |
| [adhs-mcp](../mcps/adhs.md) | ADHS public surveillance summaries | 6 |
| [211-az-mcp](../mcps/211-az.md) | 211 AZ referrals | 6 |
| [whispers-mcp](../mcps/whispers.md) | USGS WHISPers wildlife mortality | 6 |
| [inaturalist-mcp](../mcps/inaturalist.md) | iNaturalist citizen-science observations | 6 |
| [great-az-tick-check-mcp](../mcps/great-az-tick-check.md) | Great AZ Tick Check submissions | 5 |
| [sms-entry-mcp](../mcps/sms-entry.md) | Twilio SMS intake adapter | 6 |
| [wearable-mcp](../mcps/wearable.md) | HealthKit / Health Connect readings | 4 |

## What it looks like

_Screenshots land here from Phase 5._

## Decisions & trade-offs

To be authored.

## Where to go next

[04 · Stand up the store →](04-store.md)
