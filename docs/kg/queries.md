# Example queries

The `knowledge-graph-mcp` server exposes 12 tools plus a SELECT-only SQL
escape hatch (`kg_sql`). The same DuckDB tables are also queryable
client-side via DuckDB-WASM at [`/query/`](https://tyson-swetnam.github.io/epihack-2026/query/).

```sql
-- Pathogens by vector
SELECT n_p.slug AS pathogen, n_v.slug AS vector
FROM kg.edge e
JOIN kg.node n_p ON e.src_id = n_p.id
JOIN kg.node n_v ON e.dst_id = n_v.id
WHERE e.kind = 'transmitted_by'
ORDER BY n_p.slug;
```

See [`mcp/knowledge-graph-mcp/README.md`](https://github.com/tyson-swetnam/epihack-2026/blob/main/mcp/knowledge-graph-mcp/README.md)
for the full tool inventory.
