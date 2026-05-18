# epihack-2026

EpiHack AZ 2026 &mdash; a working repository for the
[EpiHack Arizona](https://endingpandemicsacademy.arizona.edu/trainings-events/epihack-arizona)
event hosted by the Ending Pandemics Academy and the University of Arizona
Global Health Institute.

## Contents

```
figures/        Structured transcriptions of the EpiHack reference figures
  ├── 01-purpose-one-health-participatory-system.md
  ├── 02-minimum-key-data-parameters.md
  ├── 03-outbreak-timeliness-metrics.md
  ├── 04-designing-launching-participatory-surveillance.md
  └── index.html              -- combined HTML rendering of all four figures
schema/
  └── knowledge_graph.sql     -- DuckLake/DuckDB seed for the knowledge graph
```

The Markdown files use YAML frontmatter and explicit `subject | predicate |
object` tables so they can be parsed directly into the knowledge-graph
tables defined in `schema/knowledge_graph.sql`.

## Knowledge framework: DuckLake + DuckDB + Postgres

The figures encode three reusable conceptual frameworks that we want to
operationalize as a queryable knowledge graph:

1. **Figure 1** &mdash; the *purpose* of a One Health participatory system.
2. **Figure 2** &mdash; the *minimum key data parameters* (a typed data
   dictionary across General / Human / Severity / Exposure / Auxiliary /
   Environmental / Livestock / Wildlife).
3. **Figure 3** &mdash; the *outbreak timeliness milestones* used to compute
   inter-milestone intervals.
4. **Figure 4** &mdash; the *12-step lifecycle* for designing and launching
   participatory surveillance.

These are all relational by nature (parameters belong to categories,
milestones precede milestones, steps precede steps, sectors emit signals)
which is why a property-graph encoding is a natural fit.

### Why DuckLake + DuckDB + Postgres

| Layer | Role |
|---|---|
| **Postgres** | DuckLake catalog: snapshot metadata, schema evolution, ACID transactions over the lakehouse. |
| **DuckLake** | Open lakehouse format on top of Parquet, catalog in Postgres. Gives us time travel, branches, and multi-writer concurrency without standing up Iceberg/Hudi infrastructure. |
| **DuckDB** | Embedded query engine. Reads/writes DuckLake natively; can join Parquet, Postgres, and CSV in a single SQL statement; works on a laptop and at hack-day scale. |

### Bootstrap

```bash
# 1. Postgres for the DuckLake catalog
createdb epihack

# 2. DuckDB session
duckdb
```

```sql
-- Inside DuckDB:
INSTALL ducklake;  INSTALL postgres;
LOAD    ducklake;  LOAD    postgres;

ATTACH 'ducklake:postgres:dbname=epihack host=localhost user=epihack'
  AS epihack
  (DATA_PATH 's3://epihack/ducklake/');     -- or a local path for laptop dev

USE epihack;
.read schema/knowledge_graph.sql
```

After loading, the graph is queryable in plain SQL. Examples:

```sql
-- All parameters in the Exposure class
SELECT n.label
FROM   kg.edge e
JOIN   kg.node n ON n.node_id = e.subject_id
WHERE  e.predicate = 'belongsTo'
  AND  e.object_id = 'category.exposure';

-- Milestone ordering for timeliness metrics
SELECT n.label, p.value_num AS ordinal
FROM   kg.node n
JOIN   kg.property p ON p.node_id = n.node_id AND p.key = 'ordinal'
WHERE  n.node_type = 'milestone'
ORDER  BY p.value_num;

-- Lifecycle chain via recursive CTE
WITH RECURSIVE chain AS (
  SELECT subject_id, object_id, 1 AS depth
  FROM   kg.edge
  WHERE  predicate = 'precedes' AND subject_id = 'step.01_assess_needs'
  UNION ALL
  SELECT e.subject_id, e.object_id, c.depth + 1
  FROM   kg.edge e
  JOIN   chain c ON e.subject_id = c.object_id
  WHERE  e.predicate = 'precedes'
)
SELECT * FROM chain;
```

### Next steps for the EpiHack build

- [ ] Wire incoming participatory-surveillance reports into a `report` fact
      table whose columns are the parameters from Figure 2.
- [ ] Compute timeliness intervals (Figure 3) as a `metric` view between
      milestone-date columns on the `outbreak` table.
- [ ] Expose the graph as a GraphQL or Cypher-style API for the hackathon
      teams &mdash; DuckDB's recursive CTEs handle the path queries.
- [ ] Track the lifecycle (Figure 4) as project state for each pilot
      community deployment.

## License

See [LICENSE](./LICENSE).
