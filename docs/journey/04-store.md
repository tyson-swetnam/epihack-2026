# 04 · Stand up the store

!!! note "Stub"
    Authored in Phase 3. Source: `plan/09-mobile-datastore.md`,
    `schema/knowledge_graph.sql`, `schema/deep/*.sql`.

## What we wanted

A single source of truth for the knowledge graph, queryable both from
inside the agents (server-side) and from the browser (client-side, via
DuckDB-WASM) — and a mobile-friendly write path that doesn't sacrifice
write latency for analytical query power.

## What we built

A **dual-sink datastore**:

- **DuckLake-on-Postgres** for web + analytics (catalog in Postgres, data
  in S3-style storage, queries in DuckDB).
- **MongoDB** for mobile writes — schemaless, low-latency, synced back
  into DuckLake.
- An **`X-Client-Channel`** header on the API routes mobile writes to
  Mongo and web writes to DuckLake.

The knowledge graph itself is property-graph-shaped: `kg.node`, `kg.edge`,
`kg.property`. 572 nodes, 791 edges, 1027 properties seeded from
`schema/*.sql` and `schema/deep/*.sql`.

## What it looks like

_Screenshots land here from Phase 5._

## Decisions & trade-offs

To be authored.

## Where to go next

[05 · Orchestrate the agents →](05-orchestrate.md)
