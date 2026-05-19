---
title: EpiHack Arizona 2026
---

# epihack-2026

EpiHack AZ 2026 &mdash; a working repository for the
[EpiHack Arizona](https://endingpandemicsacademy.arizona.edu/trainings-events/epihack-arizona)
event hosted by the Ending Pandemics Academy and the University of Arizona
Global Health Institute.

## A living database for ending pandemics

This repository is an experiment in building a **living knowledge graph
for One Health surveillance**. Three pieces of infrastructure do the
heavy lifting:

| Layer | Role | What it lets us do |
|---|---|---|
| **[Claude Code](https://claude.com/product/claude-code)** | Agentic authoring | Drafts the schema, runs parallel sub-agents to research AZ counties / tribes / pathogens / outbreaks / datasets / standards, keeps the prose docs in sync with the SQL seeds, and opens pull requests against this repo. Every commit message in `git log` describes a Claude-led change. |
| **GitHub** | Source of truth + review surface | Every change &mdash; new content, schema, MCP code, visualizations &mdash; lands as a pull request; humans review and merge. Versioned snapshots of upstream specs (e.g. `mcp/vectorsurv/openapi/`) make API drift a `git diff` away. The site itself is served via GitHub Pages with Jekyll. |
| **[DuckLake](https://ducklake.select/) (Postgres + [DuckDB](https://duckdb.org/))** | Queryable knowledge graph | A property-graph (`kg.node`, `kg.edge`, `kg.property`) seeded from version-controlled SQL; Postgres holds the DuckLake catalog (time-travel, branches, ACID), DuckDB is the query engine. Joins Parquet + Postgres + CSV in a single SQL statement; works on a laptop and at hack-day scale. |

What makes it *living* rather than a static snapshot:

- **New AZ data sources land via PR.** A sub-agent does the research,
  drafts a `schema/deep/*.sql` seed, and opens a PR. Reviewers (humans
  or other agents) merge. The next `.read` rebuilds the graph.
- **Upstream API drift is detected, not silently swallowed.** The
  `mcp/vectorsurv/openapi/` directory holds versioned snapshots; a
  `git diff` between two snapshots is the changelog the MCP client
  reacts to.
- **MCP servers stream live agency data into the same graph.**
  The included [`vectorsurv-mcp`](./mcp/vectorsurv/) exposes the
  national mosquito- and tick-surveillance API as MCP tools (sites,
  collections, pools, vector-index calculations, human / equine
  arbovirus case counts). An LLM client can query VectorSurv and
  drop the results into the same DuckLake graph.
- **The visualizations are knowledge-graph-aware.** Every pin on the
  [map](./map/) and every node in the
  [pathogen graph](./graph/) carries a `kg_node_id` that round-trips
  to the SQL graph. Click a feature, get the canonical node back.

## Site roadmap

Everything in this repository is also a page on the published site at
<https://tyson-swetnam.github.io/epihack-2026/>.

### Reference frameworks
- [Top-level landing page](./index.html) &mdash; entry point with cards to every section.
- [Figures](./figures/) &mdash; the four EpiHack reference posters plus the breakout-session worksheet, transcribed into structured Markdown with explicit RDF-style triples.

### Focus groups
- [Wildlife &amp; Vector-Borne Diseases](./wildlife/) &mdash; four guiding questions, a 30+ resource catalog spanning state / county / tribal / federal / academic / citizen-science, plus a draft participatory-surveillance system design.
- [Heat](./heat/) &mdash; four guiding questions, vulnerable populations, and a 30+ heat-resource catalog (ADHS, MAG HRN, Phoenix OHRM, UA Heat Resilience Initiative, NWS HeatRisk, 211 Arizona).

### Interactive viewers
- [Map](./map/) &mdash; MapLibre GL map of Arizona surfacing the geospatial slice of the knowledge graph: 15 counties, 22 tribal nations, NEON Domain 14 sites, agency HQs by jurisdiction, federal-land units, and historical outbreak locations. Mobile-responsive with a collapsible panel.
- [Pathogen knowledge graph](./graph/) &mdash; Cytoscape.js node-edge viewer for the 16 pathogens with their vectors, reservoirs, focus areas, and surveilling agencies. Color- and shape-coded; filter by pathogen class; switch layouts.

### Application plan
- [AZ One Health Sentinel — plan](./plan/) &mdash; five-document plan for a mobile-first participatory-surveillance app spanning Vector-Borne Disease and Heat. Covers Figure 2 parameter mapping by vertical, the MCP integration topology, the eight-agent architecture, four worked end-to-end data flows, and a phased roadmap tied to the [Figure 3 timeliness milestones](./figures/03-outbreak-timeliness-metrics.md).

### MCP servers (live data ingestion for LLMs)
- [`vectorsurv-mcp`](./mcp/vectorsurv/) &mdash; Wraps the [VectorSurv](https://vectorsurv.org/) API ([spec v1.0.44](./mcp/vectorsurv/openapi/)). 13 tools including `vectorsurv_agency_region_intersect` (the fastest way to enumerate AZ agencies), `vectorsurv_get_pools`, `vectorsurv_pools_are_positive`, `vectorsurv_get_case_counts`, and client-side abundance / infection-rate / vector-index calculators.
- [`knowledge-graph-mcp`](./mcp/knowledge-graph-mcp/) &mdash; Read-only DuckDB query MCP over the EpiHack knowledge graph (572 nodes / 791 edges / 1027 properties at last load). 12 tools (`kg_node_lookup`, `kg_neighborhood`, `kg_path`, `kg_pathogens_by_vector`, `kg_outbreak_check`, …) plus a SELECT-only SQL escape-hatch.
- [`great-az-tick-check-mcp`](./mcp/great-az-tick-check-mcp/) &mdash; Mock submission tracking for the Great Arizona Tick Check (UA Cooperative Extension / Walker lab) until the real API arrives. 5 tools incl. mailing-label generation.
- [`nws-heatrisk-mcp`](./mcp/nws-heatrisk-mcp/) &mdash; NWS HeatRisk + active heat alerts + Rothfusz heat-index calculator (no auth, just a `User-Agent` header). 7 tools.

### Application (Phase 0)
- [`app/`](./app/) &mdash; Vanilla HTML+JS+CSS prototype of the AZ One Health Sentinel app. Hosts the Scenario-A tick mail-in flow end-to-end (GPS, photo capture, symptoms, consent, mailing label) against a mock backend.
- [`agents/`](./agents/) &mdash; Python package implementing the 8-agent pipeline (Intake → Geo-Enrichment → Validation → Triage → Enrichment → Notification → Cluster Detection → Knowledge Update) with typed pydantic contracts. Scenarios A and C from the plan run end-to-end through the stub agents.
- See [`plan/EXECUTION-STATUS.md`](./plan/EXECUTION-STATUS.md) for the verification matrix and the small list of doc / schema follow-ups.

### Knowledge-graph SQL
- [`schema/`](./schema/) &mdash; core graph (frameworks) plus worksheet template, focus areas, designs, World Café cards, and the two focus-group seeds.
- [`schema/deep/`](./schema/deep/) &mdash; sub-agent deep-research seeds: all 15 AZ counties, all 22 federally recognized AZ tribes, pathogens (with vectors / reservoirs / ICD-10), historical AZ outbreaks (with Figure 3 milestone dates), datasets &amp; APIs (NEON DPs, WHISPers, NWS, GBIF, iNat), interop standards (FHIR, OMOP, ICD-10, Darwin Core), MCP servers.

### Breakout artifacts
- [Worksheets](./worksheets/) &mdash; completed design worksheets from EpiHack breakouts.
- [World Café notes](./notes/world-cafe/) &mdash; Q4 cards transcribed from Heat, Unhoused, and Information Flow breakouts.

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
mcp/
  └── vectorsurv/   Model Context Protocol server wrapping the VectorSurv
                    vector-borne disease surveillance API (sites,
                    collections, pools, abundance, infection rate,
                    vector index).
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
      ├── standards.sql         --   FHIR, OMOP, ICD-10, Darwin Core, GeoSPARQL
      └── mcp_servers.sql       --   MCP servers (vectorsurv-mcp + tools)
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
