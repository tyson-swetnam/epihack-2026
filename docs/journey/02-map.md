# 02 · Map the data sources

!!! note "Stub"
    Authored in Phase 3. Source: `plan/01-parameter-mapping.md`,
    `plan/02-mcp-integration.md`, and `schema/deep/datasets_apis.sql`.

## What we wanted

A canonical mapping between the eight-class minimum dataset (Figure 2)
and the real-world APIs that could populate it — so every "we should
report this signal" conversation could end with a concrete endpoint.

## What we built

- The **parameter-mapping table** in `plan/01-parameter-mapping.md`
  pinning each minimum-dataset class to one or more data sources.
- **`schema/deep/datasets_apis.sql`** — the seed listing every dataset
  + API we considered, with citations, jurisdiction, freshness, and
  whether we wrapped it as an MCP.
- The **shortlist** that became Phase 1 MCP work: VectorSurv, NWS
  HeatRisk, MAG HRN, ADHS, 211 AZ, WHISPers, iNaturalist, Great AZ Tick
  Check, plus the wearable and SMS *intake* adapters.

## What it looks like

_Screenshots land here from Phase 5._

## Decisions & trade-offs

To be authored.

## Where to go next

[03 · Build the MCPs →](03-mcps.md)
