# Knowledge-graph schema

!!! info "Source"
    The schema lives in [`schema/*.sql`](https://github.com/tyson-swetnam/epihack-2026/tree/main/schema)
    and [`schema/deep/*.sql`](https://github.com/tyson-swetnam/epihack-2026/tree/main/schema/deep).

The graph is a property graph:

- `kg.node(id, slug, kind, label, ...)` — entities.
- `kg.edge(id, src_id, dst_id, kind, ...)` — relationships.
- `kg.property(entity_id, key, value_text, value_num, value_json, ...)` — facts.

572 nodes / 791 edges / 1027 properties at the time of archive.

Conventions worth knowing:

- **Every node has a stable dot-namespaced slug** (`pathogen.west_nile`,
  `county.maricopa`). Renames cascade through `agents/`, dashboards, and
  the map/graph viewers.
- **Each `schema/deep/*.sql` seed owns a contiguous edge-ID range**
  (counties 10000-, tribes 11000-, pathogens 12000-, outbreaks 13000-,
  standards 14000-, datasets_apis 15000-, mcp_servers 16000-,
  application 17000-, followups 30000-).
- **Tribal data is suppressed by default.** Opt-in lives in
  `consent_profile` rows, consulted by ValidationAgent at write time.

See [Seed load order](seeds.md) and [Example queries](queries.md).
