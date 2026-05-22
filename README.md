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
| **GitHub** | Source of truth + review surface | Every change &mdash; new content, schema, MCP code, visualizations &mdash; lands as a pull request; humans review and merge. Versioned snapshots of upstream specs (e.g. `mcp/vectorsurv-mcp/openapi/`) make API drift a `git diff` away. The site itself is served via GitHub Pages with Jekyll. |
| **[DuckLake](https://ducklake.select/) (Postgres + [DuckDB](https://duckdb.org/))** | Queryable knowledge graph | A property-graph (`kg.node`, `kg.edge`, `kg.property`) seeded from version-controlled SQL; Postgres holds the DuckLake catalog (time-travel, branches, ACID), DuckDB is the query engine. Joins Parquet + Postgres + CSV in a single SQL statement; works on a laptop and at hack-day scale. |

What makes it *living* rather than a static snapshot:

- **New AZ data sources land via PR.** A sub-agent does the research,
  drafts a `schema/deep/*.sql` seed, and opens a PR. Reviewers (humans
  or other agents) merge. The next `.read` rebuilds the graph.
- **Upstream API drift is detected, not silently swallowed.** The
  `mcp/vectorsurv-mcp/openapi/` directory holds versioned snapshots; a
  `git diff` between two snapshots is the changelog the MCP client
  reacts to.
- **MCP servers stream live agency data into the same graph.**
  The included [`vectorsurv-mcp`](./mcp/vectorsurv-mcp/) exposes the
  national mosquito- and tick-surveillance API as MCP tools (sites,
  collections, pools, vector-index calculations, human / equine
  arbovirus case counts). An LLM client can query VectorSurv and
  drop the results into the same DuckLake graph.
- **The visualizations are knowledge-graph-aware.** Every pin on the
  [map](./map/) and every node in the
  [pathogen graph](./graph/) carries a `kg_node_id` that round-trips
  to the SQL graph. Click a feature, get the canonical node back.

## System architecture

Alongside the knowledge graph, the repo ships a working
participatory-surveillance application. Four loosely-coupled components
share one origin:

| Component | Stack | Role |
|---|---|---|
| [`app/`](./app/) | Next.js 16 + React 19 + TypeScript + Tailwind | Mobile-first anonymous reporting app (tick / heat / cool-off), typed against `api/openapi.yaml`. Static-exported to `/epihack-2026/app/`. |
| [`agents/`](./agents/) | Python 3.11 + FastAPI + Pydantic v2 + `anthropic` + `mcp` | The HTTP backend + eight-agent orchestrator (Intake → Geo → Validation → Triage → Enrichment → Notification + Cluster + KnowledgeUpdate). Serves `api/openapi.yaml`. |
| [`mcp/`](./mcp/) | FastMCP + httpx + Pydantic v2 | **Eleven** MCP servers wrapping live (and, where no upstream API exists, mock) agency data sources. |
| [`dashboard/`](./dashboard/), [`today/`](./today/), [`map/`](./map/), [`graph/`](./graph/) | Vanilla HTML + ES modules | Agency analyst workspace, public citizen view, and the two knowledge-graph viewers. |

### Two stores, one privacy contract

As of [`plan/09`](./plan/09-mobile-datastore.md) the write path is
**dual-sink**: the **mobile app persists to MongoDB**, while the **web
build and all analytics stay on DuckLake**. Both channels POST to the
same `/v1/reports` endpoint and run the *same* privacy enforcement
(coarsen location, strip/reject EXIF GPS, never-diagnose triage guard,
SHA-256 audit digests) **before** the sink is chosen by an
`X-Client-Channel` header — so the contract lives in one place
(`agents/.../api/routes/reports.py`). Mobile documents are then replayed
into DuckLake by a watermarked, idempotent `mongo_to_ducklake` sync, so
the agents, MCP servers, and cluster detection all see one unified
dataset.

```
  web build  ─┐                            ┌─► DuckLake  (kg_writer) ──────────────┐
              ├─ POST /v1/reports · FastAPI ┤                                       ├─► knowledge graph
  mobile app ─┘   + X-Client-Channel        └─► MongoDB (mongo_writer) ─ sync ──────┘   (agents · MCP ·
                                                                                         cluster scan)
   privacy enforcement (validate · coarsen · EXIF check · triage-guard · SHA-256 digests)
   runs inside FastAPI BEFORE the sink is chosen — one contract for both channels
```

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
- [AZ One Health Sentinel — plan](./plan/) &mdash; the multi-document plan (`01`–`09` plus cluster-calibration, evaluation, and federation notes) for a mobile-first participatory-surveillance app spanning Vector-Borne Disease and Heat. Covers Figure 2 parameter mapping by vertical, the MCP integration topology, the eight-agent architecture, four worked end-to-end data flows, the [auth model](./plan/07-auth.md), the [mobile UX revamp](./plan/08-mobile-ux-revamp.md), the [dual MongoDB/DuckLake datastore](./plan/09-mobile-datastore.md), and a phased roadmap tied to the [Figure 3 timeliness milestones](./figures/03-outbreak-timeliness-metrics.md).

### MCP servers (live data ingestion for LLMs)
Eleven servers ship today; see [`mcp/README.md`](./mcp/README.md) for the
full index (tool tables, auth posture, test counts).
- [`vectorsurv-mcp`](./mcp/vectorsurv-mcp/) &mdash; VectorSurv national mosquito + tick surveillance API (spec v1.0.44). 13 tools.
- [`knowledge-graph-mcp`](./mcp/knowledge-graph-mcp/) &mdash; Read-only DuckDB query MCP over the kg (572 nodes / 791 edges / 1027 properties). 12 tools + SELECT-only SQL escape-hatch.
- [`great-az-tick-check-mcp`](./mcp/great-az-tick-check-mcp/) &mdash; Mock submission tracking for the UA Cooperative Extension tick program. 5 tools.
- [`nws-heatrisk-mcp`](./mcp/nws-heatrisk-mcp/) &mdash; NWS HeatRisk + alerts + heat-index. 7 tools.
- [`mag-hrn-mcp`](./mcp/mag-hrn-mcp/) &mdash; MAG Heat Relief Network cooling-center search. 5 tools.
- [`adhs-mcp`](./mcp/adhs-mcp/) &mdash; ADHS public surveillance summaries (heat mortality, arbovirus, reportable conditions). 6 tools.
- [`211-az-mcp`](./mcp/211-az-mcp/) &mdash; 211 Arizona referrals + transport dispatch. 6 tools.
- [`whispers-mcp`](./mcp/whispers-mcp/) &mdash; USGS WHISPers wildlife mortality events. 6 tools.
- [`inaturalist-mcp`](./mcp/inaturalist-mcp/) &mdash; iNaturalist citizen-science observations. 6 tools.
- [`sms-entry-mcp`](./mcp/sms-entry-mcp/) &mdash; SMS-only intake adapter; Twilio HMAC-SHA1 signature check, normalisation, intent parsing. 6 tools.
- [`wearable-mcp`](./mcp/wearable-mcp/) &mdash; HealthKit / Health Connect readings (skin temp, HRV, sweat rate, heart rate); on-device-only posture, mock-by-default. 4 tools.

### Reporting app + backend
- [`app/`](./app/) &mdash; Mobile-first reporting app: **Next.js 16 + React 19 + TypeScript + Tailwind**, typed against `api/openapi.yaml`. Anonymous Human / Animal / Environmental flows (tick mail-in, heat check-in, anonymous heat self-report, "where can I cool off?"), client-side EXIF strip + ZIP / 1&nbsp;km coarsening, a localStorage offline retry queue, and an `X-Client-Channel` header that routes the write to MongoDB (mobile) or DuckLake (web). An optional account adds **profile enrichment** (household size, pets, outdoor work — all opt-in, off by default) so advisories stay relevant, plus a **personal dashboard** (`/dashboard`): local weather, active alerts near you, a link into the live map + county resources, a community leaderboard, engagement rewards, and a weekly-email opt-in (leaderboard, rewards, and the weather strip are demo stubs pending a live feed). The original vanilla-HTML flows live on as a read-only archive at [`app/legacy/`](./app/legacy/).
  - **Live demo:** <http://epihack-test.cis240692.projects.jetstream-cloud.org/> (running on a Jetstream2 VM).
- [`agents/`](./agents/) &mdash; The FastAPI backend + 8-agent pipeline (Intake → Geo-Enrichment → Validation → Triage → Enrichment → Notification → Cluster Detection → Knowledge Update). Two write sinks (`kg_writer` → DuckLake, `mongo_writer` → MongoDB) behind one privacy-enforcing endpoint, plus the `mongo_to_ducklake` sync. Offline test suite; Scenarios A and C run end-to-end against shipped MCP-tool names.
- See [`plan/EXECUTION-STATUS.md`](./plan/EXECUTION-STATUS.md), [`plan/EXECUTION-STATUS-PHASE-1-2.md`](./plan/EXECUTION-STATUS-PHASE-1-2.md), and [`plan/EXECUTION-STATUS-PHASE-4.md`](./plan/EXECUTION-STATUS-PHASE-4.md) for the verification matrix.

### Public dashboard (Phase 3)
- [`today/`](./today/) &mdash; *AZ One Health Today*: a citizen-facing aggregated view (today's HeatRisk, WNV pool positivity, recent wildlife signals, and a five-number statewide snapshot). Auto-detects county, no login, no PII — renders only pre-aggregated kg fields.

### Agency dashboard (Phase 3)
- [`dashboard/`](./dashboard/) &mdash; Read-only analyst workspace for ADHS Vector-Borne &amp; Zoonotic Diseases, Maricopa County DPH Heat Surveillance, AZ Game &amp; Fish Wildlife Health Program, and Coconino HHS. Four-audience landing pages, status cards, Cluster Detection Agent feed, lazy-loaded MapLibre embed, sparkline case-count tables, and a SQL preview that round-trips to `knowledge-graph-mcp`. Implements Scenario D from [`plan/04-data-flows.md`](./plan/04-data-flows.md).

### Knowledge-graph SQL
- [`schema/`](./schema/) &mdash; core graph (frameworks) plus worksheet template, focus areas, designs, World Café cards, and the two focus-group seeds.
- [`schema/deep/`](./schema/deep/) &mdash; sub-agent deep-research seeds: all 15 AZ counties, all 22 federally recognized AZ tribes, pathogens (with vectors / reservoirs / ICD-10), historical AZ outbreaks (with Figure 3 milestone dates), datasets &amp; APIs (NEON DPs, WHISPers, NWS, GBIF, iNat), interop standards (FHIR, OMOP, ICD-10, Darwin Core), MCP servers.

### Breakout artifacts
- [Worksheets](./worksheets/) &mdash; completed design worksheets from EpiHack breakouts.
- [World Café notes](./notes/world-cafe/) &mdash; Q4 cards transcribed from Heat, Unhoused, and Information Flow breakouts.

## Contents

```
README.md       Project overview (this file)
index.html      Top-level site landing page (linked from GitHub Pages)
CLAUDE.md       Repo guide for Claude Code / contributors
api/
  └── openapi.yaml   Source of truth for the app ⇄ backend HTTP contract

app/            Next.js 16 + React 19 + TypeScript + Tailwind reporting app
  ├── src/app/         -- routes: home, report/[type], account, profile, sign-in, auth
  ├── src/lib/         -- api-client, coarse-geo, exif-stripper, offline-queue,
  │                       api-types.ts (generated from openapi.yaml — do not hand-edit)
  ├── src/components/  -- ReportFlow, AppShell, OfflineFlusher, ProfileForm
  └── legacy/          -- original vanilla-HTML flows (read-only archive)

agents/         FastAPI backend + 8-agent orchestrator (Python 3.11)
  └── src/onehealth_agents/
      ├── api/             -- FastAPI app + routes (reports, profile, auth, context)
      ├── orchestrator.py  -- runs the 8 agents below
      ├── intake.py geo.py validation.py triage.py enrichment.py
      │                       notification.py cluster.py update.py   -- the 8 agents
      ├── kg_writer.py     -- DuckLake sink (web channel)
      ├── mongo_writer.py  -- MongoDB sink (mobile channel)
      ├── sync/            -- mongo_to_ducklake watermarked, idempotent ETL
      └── mcp_client.py audit.py contracts.py ...

mcp/            Eleven MCP servers, one uv workspace each -- see mcp/README.md
  ├── vectorsurv-mcp/ knowledge-graph-mcp/ great-az-tick-check-mcp/
  ├── nws-heatrisk-mcp/ mag-hrn-mcp/ adhs-mcp/ 211-az-mcp/
  └── whispers-mcp/ inaturalist-mcp/ sms-entry-mcp/ wearable-mcp/

map/            MapLibre GL map of AZ (counties, tribes, NEON sites, agency
                HQs, federal lands, outbreaks); each pin carries a kg_node_id.
graph/          Cytoscape.js pathogen knowledge graph (16 pathogens).
dashboard/      Phase-3 agency-side read-only analyst workspace
                (ADHS / MCDPH / AZGFD / Coconino).
today/          Phase-3 public citizen-facing aggregated view (no login, no PII).
figures/        Structured transcriptions of the five EpiHack reference figures.
wildlife/ heat/ Focus-group materials (4 questions + 30+ resource catalogs each).
worksheets/     Completed design worksheets from EpiHack breakouts.
notes/world-cafe/  World Café Q4 breakout cards (heat, unhoused, info-flow).
evaluation/     Cluster-detector evaluation harness + 2024 baseline.

schema/         Knowledge-graph SQL (property graph: kg.node / edge / property)
  ├── knowledge_graph.sql  -- core graph (frameworks)
  ├── system_designs.sql world_cafe.sql wildlife_vectors.sql heat.sql
  └── deep/                -- parallel sub-agent deep-research seeds
      ├── standards.sql        -- FHIR/OMOP/ICD-10/Darwin Core (load FIRST)
      ├── pathogens.sql        -- vectors / reservoirs / ICD-10 (load SECOND)
      ├── counties.sql tribes.sql outbreaks.sql datasets_apis.sql
      ├── application.sql followups.sql audit.sql
      └── cluster_followups.sql outbreaks_near_me.sql mcp_servers.sql

ansible/        One-command VM deploy (Postgres + DuckLake, self-hosted
                MongoDB + sync timer, MCP servers, FastAPI, app, nginx).
deploy/         VM sizing, DNS, and the operations runbook.
plan/           01–09 plan docs + cluster-calibration / evaluation / status.
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

DuckLake is the **web + analytics store**; the mobile app writes to
**MongoDB**, which is synced back into DuckLake so the agents, MCP
servers, and cluster detection see one dataset (see
[System architecture](#system-architecture)). The bootstrap below builds
the DuckLake side.

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
.read schema/deep/standards.sql     -- must load first  (SNOMED / ICD-10 FKs)
.read schema/deep/pathogens.sql     -- must load second (pathogen FKs)
.read schema/deep/counties.sql
.read schema/deep/tribes.sql
.read schema/deep/outbreaks.sql
.read schema/deep/datasets_apis.sql
.read schema/deep/application.sql
.read schema/deep/followups.sql
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

## Self-hosting on a VM

Spinning up your own instance? [`deploy/README.md`](./deploy/README.md)
walks through VM sizing, DNS, and the operations runbook;
[`ansible/`](./ansible/) is a one-command Ansible playbook that takes
a fresh Ubuntu 24.04 VM from `apt update` to a running deployment of
Claude Code, every MCP server in [`mcp/`](./mcp/), the FastAPI backend,
the Next.js reporting app, Postgres for the DuckLake catalog,
self-hosted MongoDB for the mobile write-path (bound to `127.0.0.1`,
auth enabled) with its `mongo_to_ducklake` sync timer, and nginx with
optional Let's Encrypt TLS.

```bash
cd ansible
cp inventory.example.yml inventory.yml          # edit ansible_host
cp group_vars/all.vault.example.yml group_vars/all.vault.yml
ansible-vault encrypt group_vars/all.vault.yml  # fill in secrets first
ansible-galaxy install -r requirements.yml
ansible-playbook -i inventory.yml playbook.yml --ask-vault-pass
```

## Contributing + governance

The repository is now stewarded by a standing review board (ADHS,
AZGFD, ITCA-TEC, Maricopa Vector Control) per the cross-cutting
governance track in [`plan/05-roadmap.md`](./plan/05-roadmap.md).
Contributions are welcome through pull requests; the six documents
below describe the conventions, the review structure, the security
posture, and the version history.

- [`CONTRIBUTING.md`](./CONTRIBUTING.md) &mdash; local environment
  setup, PR workflow, MCP-server and schema-seed templates, coding
  style, and the privacy + data-sovereignty checklist every PR
  touching observation data must pass.
- [`GOVERNANCE.md`](./GOVERNANCE.md) &mdash; standing review board
  membership, proposal-then-merge cadence, tribal-partner veto,
  opt-in posture for tribal data, conflict-of-interest disclosure,
  and sunset clauses for MCP servers that proxy tribal data.
- [`SECURITY.md`](./SECURITY.md) &mdash; private-disclosure channel,
  the five-class threat model
  (re-identification / credential leakage / token reuse /
  prompt-injection / cluster-detection false positives), mitigations
  in place, and an itemised list of known security gaps.
- [`CHANGELOG.md`](./CHANGELOG.md) &mdash; per-phase rollup of what
  landed and when (PRs #1 through #8), plus the "Next" backlog from
  [`plan/EXECUTION-STATUS-PHASE-1-2.md`](./plan/EXECUTION-STATUS-PHASE-1-2.md)
  and [`plan/CLUSTER-CALIBRATION.md`](./plan/CLUSTER-CALIBRATION.md).
- [`mcp/README.md`](./mcp/README.md) &mdash; index of all 11 MCP
  servers with tool counts, auth posture, and test counts, plus the
  recipe for adding a new MCP server.
- [`NOTICE`](./NOTICE) &mdash; third-party attribution for runtime
  dependencies (MapLibre, Cytoscape, FastMCP / `mcp` SDK, pydantic,
  httpx, DuckDB / DuckLake), data sources surfaced via MCP, and
  upstream-spec snapshots.

## License

See [LICENSE](./LICENSE).
