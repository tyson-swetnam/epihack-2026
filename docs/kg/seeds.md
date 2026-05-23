# Seed load order

The seeds **must** be loaded in this order. `standards.sql` and
`pathogens.sql` must come first (SNOMED/ICD-10 and pathogen FKs):

```sql
-- 1. core
.read schema/knowledge_graph.sql
.read schema/system_designs.sql
.read schema/world_cafe.sql
.read schema/wildlife_vectors.sql
.read schema/heat.sql
-- 2. standards & pathogens (FK targets)
.read schema/deep/standards.sql
.read schema/deep/pathogens.sql
-- 3. everything else
.read schema/deep/counties.sql
.read schema/deep/tribes.sql
.read schema/deep/outbreaks.sql
.read schema/deep/datasets_apis.sql
.read schema/deep/application.sql
.read schema/deep/followups.sql
```

`knowledge_graph_mcp.loader.discover_schema_files` enforces this order
programmatically; the Ansible `ducklake` role calls it.
