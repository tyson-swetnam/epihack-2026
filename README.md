---
title: EpiHack Arizona 2026
---

# epihack-2026

EpiHack AZ 2026 &mdash; a working repository for the
[EpiHack Arizona](https://endingpandemicsacademy.arizona.edu/trainings-events/epihack-arizona)
event hosted by the Ending Pandemics Academy and the University of Arizona
Global Health Institute.

## Contents

```
index.html      Top-level site landing page (linked from GitHub Pages)
map/            MapLibre GL map of AZ pinning counties, tribes, NEON
                sites, agency HQs, federal lands, and outbreaks; each
                feature carries a kg_node_id round-trippable to the
                DuckLake graph.
graph/          Cytoscape.js pathogen knowledge graph (16 pathogens with
                their vectors, reservoirs, focus areas, and surveilling
                agencies).
figures/        Structured transcriptions of the EpiHack reference figures
  ├── 01-purpose-one-health-participatory-system.md
  ├── 02-minimum-key-data-parameters.md
  ├── 03-outbreak-timeliness-metrics.md
  ├── 04-designing-launching-participatory-surveillance.md
  ├── 05-design-worksheet-template.md      -- breakout-session worksheet
  └── index.html                            -- combined HTML rendering
wildlife/       Focus group 1 -- Wildlife & Vector-Borne Diseases
  ├── 01-wildlife-tracking.md
  ├── 02-zoonotic-surveillance.md
  ├── 03-surveillance-technologies.md
  ├── 04-participatory-surveillance.md
  ├── resources.md                          -- 30+ AZ resources catalog
  └── index.html
heat/           Focus group 2 -- Heat
  ├── 01-public-awareness-cooling-centers.md
  ├── 02-real-time-resource-sharing.md
  ├── 03-heat-safety-education.md
  ├── 04-vulnerable-populations.md
  ├── resources.md                          -- 30+ AZ heat-resource catalog
  └── index.html
worksheets/     Completed design worksheets from EpiHack breakouts
  ├── 01-animal-health-events.md
  └── 02-desert-wildlife-interface.md
notes/
  └── world-cafe/             -- World Café breakout cards
      ├── README.md
      ├── q4-heat.md
      ├── q4-unhoused.md
      └── q4-information-flow.md
schema/
  ├── knowledge_graph.sql       -- core graph (frameworks)
  ├── system_designs.sql        -- worksheet template, focus areas, designs
  ├── world_cafe.sql            -- World Café Q4 cards + engagement tactics
  ├── wildlife_vectors.sql      -- focus group 1 questions, resources, design
  ├── heat.sql                  -- focus group 2 questions, vulnerable pops, resources
  └── deep/                     -- parallel sub-agent deep-research seeds
      ├── counties.sql          --   all 15 AZ counties
      ├── tribes.sql            --   all 22 federally recognized AZ tribes
      ├── pathogens.sql         --   pathogens with vectors / reservoirs / ICD-10
      ├── outbreaks.sql         --   historical AZ outbreaks + timeline dates
      ├── datasets_apis.sql     --   NEON DPs, WHISPers, NWS, GBIF, iNat, etc.
      └── standards.sql         --   FHIR, OMOP, ICD-10, Darwin Core, GeoSPARQL
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

## Focus groups

EpiHack Arizona 2026 broke participants into focus groups, each chartered
to apply the frameworks above to a concrete domain. This repository covers
two:

1. **[Wildlife &amp; Vector-Borne Diseases](./wildlife/)** &mdash; four
   guiding questions on how Arizona tracks wildlife and vector density;
   how zoonotic infections are monitored in wildlife and vectors; what
   technologies could improve surveillance; and how participatory
   surveillance can better track wildlife disease. Anchored on **NEON**,
   **ADHS**, **AZGFD**, the **Great Arizona Tick Check**, USGS WHISPers,
   USDA APHIS, USFWS, the 22 AZ tribal nations, and 15 county vector
   programs.
2. **[Heat](./heat/)** &mdash; four guiding questions on how the public
   is informed about cooling-center locations; whether centers share
   resources in real time; what severe-heat education is provided; and
   who is most vulnerable to heat in Arizona. Anchored on the
   **ADHS Heat Preparedness Network**, the **MAG Heat Relief Network**
   at hrn.azmag.gov, the **Phoenix Office of Heat Response and Mitigation**,
   the **UA Heat Resilience Initiative** (which umbrellas SW-IFL, NIHHIS,
   CLIMAS, BRACE, and SCORCH), NWS HeatRisk, and **211 Arizona**.

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
.read schema/system_designs.sql
.read schema/world_cafe.sql
.read schema/wildlife_vectors.sql   -- focus group 1
.read schema/heat.sql               -- focus group 2
.read schema/deep/counties.sql      -- deep seeds (any order)
.read schema/deep/tribes.sql
.read schema/deep/pathogens.sql
.read schema/deep/outbreaks.sql
.read schema/deep/datasets_apis.sql
.read schema/deep/standards.sql
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

-- Wide summary of completed system designs
SELECT * FROM kg.v_design_summary;

-- Which focus areas does each design target?
SELECT d.label AS design, f.label AS focus_area
FROM   kg.edge e
JOIN   kg.node d ON d.node_id = e.subject_id
JOIN   kg.node f ON f.node_id = e.object_id
WHERE  e.predicate = 'targetsFocusArea'
ORDER  BY design, focus_area;

-- All World Café Q4 engagement tactics, grouped by card
SELECT * FROM kg.v_engagement_tactics ORDER BY card, tactic;

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
