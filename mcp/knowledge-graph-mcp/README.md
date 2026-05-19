---
title: knowledge-graph-mcp
---

# `knowledge-graph-mcp` — Model Context Protocol server for the EpiHack DuckLake knowledge graph

A [Model Context Protocol](https://modelcontextprotocol.io/) server that
gives an LLM (Claude Desktop, Claude Code, the
[agentic architecture](../../plan/03-agentic-architecture.html) for
EpiHack Arizona 2026, or any other MCP client) **read-only** access to
the project's DuckLake knowledge graph (`kg.node` / `kg.edge` /
`kg.property` as seeded under [`schema/`](../../schema/)).

Built for EpiHack Arizona 2026 — supports both the
[Wildlife & Vector-Borne Diseases](../../wildlife/index.html) and
[Heat](../../heat/index.html) focus groups.

> **Read-only.** Mutations to the knowledge graph belong to the
> Validation Agent and dedicated write tooling, not the LLM. The
> single SQL escape hatch (`kg_sql`) rejects anything that isn't a
> `SELECT` / `WITH ... SELECT` statement and caps results at 5000 rows.

## What it does

| MCP tool | Backed by |
|---|---|
| `kg_node_lookup` | `SELECT … FROM kg.node JOIN kg.property` |
| `kg_neighborhood` | iterative `kg.edge` expansion (max depth 3) |
| `kg_path` | BFS over the undirected `kg.edge` projection (max depth 8) |
| `kg_search` | substring match against `label` / `description` / `node_id` |
| `kg_nodes_by_type` | `SELECT … FROM kg.node WHERE node_type = ?` |
| `kg_edges_by_predicate` | `SELECT … FROM kg.edge WHERE predicate = ?` |
| `kg_regions_at_point` | bounding-box lookup against `lat`/`lon` properties on county / tribe / region nodes |
| `kg_pathogens_by_vector` | `kg.edge WHERE predicate = 'transmittedBy' AND object_id = ?` |
| `kg_pathogens_by_focus` | `kg.edge WHERE predicate = 'targetsFocusArea' AND object_id = ?` |
| `kg_outbreak_check` | `causedBy` + optional `occurredIn` filter |
| `kg_resource_lookup` | `kg.edge WHERE predicate = 'informs' AND object_id = ?` |
| `kg_sql` | escape hatch: SELECT-only, 5000-row cap |

Plus three MCP **resources** for discovery:

| Resource URI | Returns |
|---|---|
| `kg://node-types` | distinct `node_type` values currently loaded |
| `kg://predicates` | distinct edge `predicate` values currently loaded |
| `kg://schema` | text rendering of the `kg.node` / `kg.edge` / `kg.property` column shapes |

## Why this matters for EpiHack

The DuckLake knowledge graph is the project's shared memory: it
encodes which parameters belong to which categories, which milestones
precede which outbreaks, which pathogens are transmitted by which
vectors, which counties have which vector-control resources, and which
datasets / APIs inform which world-cafe questions. Exposing it as an
MCP server lets the agents in
[`plan/03-agentic-architecture.md`](../../plan/03-agentic-architecture.html)
answer questions like:

- *"For a `vector.ixodes_scapularis` sighting in `county.coconino`,
  which pathogens should we worry about and is there an active
  outbreak record?"*
- *"What resources `informs` Heat-Q4 (vulnerable populations)?"*
- *"What's the shortest path between `param.symptoms` and
  `pathogen.wnv` in the graph?"*

without writing SQL or shipping bespoke glue per consumer.

## Data sources

Two operating modes:

- **In-memory (default).** Replays every `.sql` file under
  `$KG_SCHEMA_PATH` (defaults to `../../schema` relative to this
  package) into a fresh DuckDB. Load order:
  1. `schema/knowledge_graph.sql`
  2. `schema/system_designs.sql`
  3. `schema/world_cafe.sql`
  4. `schema/wildlife_vectors.sql`
  5. `schema/heat.sql`
  6. every `schema/deep/*.sql` in alphabetical order

  Files that fail to apply are logged and skipped — one broken seed
  won't take the server down.

- **Attached DuckLake.** Set `KG_DUCKLAKE_URI` (e.g.
  `ducklake:postgres:dbname=epihack host=localhost user=epihack`) and
  the server installs/loads the `ducklake` + `postgres` extensions,
  attaches the catalog, and `USE`s it. `KG_DUCKLAKE_DATA_PATH` is
  forwarded as the `DATA_PATH` attach option.

## Install &amp; run

### As a Claude Desktop MCP server

1. Install [`uv`](https://docs.astral.sh/uv/) if you don't have it.
2. Drop the snippet in
   [`examples/claude_desktop_config.json`](./examples/claude_desktop_config.json)
   into your Claude Desktop config
   (`~/Library/Application Support/Claude/claude_desktop_config.json`
   on macOS, `%APPDATA%\Claude\claude_desktop_config.json` on Windows).
3. Replace the path with the absolute path to this directory.
4. Optionally set `KG_SCHEMA_PATH` or `KG_DUCKLAKE_URI`.
5. Restart Claude Desktop.

### Standalone

```bash
cd mcp/knowledge-graph-mcp
uv sync
uv run knowledge-graph-mcp                 # stdio (default)
MCP_TRANSPORT=streamable-http uv run knowledge-graph-mcp   # HTTP
```

### Tests

```bash
cd mcp/knowledge-graph-mcp
uv run pytest
```

Tests use a synthetic in-memory DuckDB graph (six nodes, five edges)
and exercise `kg_node_lookup`, `kg_neighborhood`, `kg_path`, the
domain conveniences, and the SQL escape-hatch's SELECT-only
enforcement. No live data is required.

## Environment variables

| Variable | Default | Effect |
|---|---|---|
| `MCP_TRANSPORT` | `stdio` | `stdio` or `streamable-http` |
| `KG_SCHEMA_PATH` | `<repo>/schema` | Directory of `.sql` files to seed in-memory mode |
| `KG_DUCKLAKE_URI` | unset | Attach a real DuckLake catalog instead of in-memory mode |
| `KG_DUCKLAKE_DATA_PATH` | unset | `DATA_PATH` attach option for the DuckLake catalog |

## Notes &amp; limitations

- `kg_regions_at_point` is a coarse bounding-box lookup against the
  `lat` / `lon` (or `latitude`/`longitude`, or
  `centroid_lat`/`centroid_lon`) numeric properties on county / tribe /
  region nodes. The default `schema/deep/counties.sql` and
  `schema/deep/tribes.sql` seeds **do not** carry centroid properties
  today, so the tool returns an empty list against the stock graph.
  Loading a centroids seed (or attaching a DuckLake catalog that
  carries them) makes the tool light up automatically.
- The SQL escape hatch is a single statement, SELECT-only, and capped
  at 5000 rows; mutations, DDL, `ATTACH`, `COPY`, `PRAGMA`, and
  multi-statement queries are all rejected.

## License

MIT, alongside the rest of `epihack-2026`.
