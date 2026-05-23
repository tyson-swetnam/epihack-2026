---
hide:
  - navigation
---

# AZ One Health Sentinel — archived documentation

!!! abstract "Status"
    **Archived 2026-05.** This site documents the state of the
    [`epihack-2026`](https://github.com/tyson-swetnam/epihack-2026) repository
    as it stood at the close of EpiHack Arizona 2026. No new features are
    planned. Every page here is a snapshot, not a roadmap.

The **AZ One Health Sentinel** is a mobile-first participatory-surveillance
stack covering vector-borne disease and extreme-heat reporting in Arizona.
It was built across roughly two weeks of vibe-coding at EpiHack Arizona
2026, and is intentionally preserved end-to-end so any future revival can
start from a known-good baseline.

<div class="grid cards" markdown>

-   :material-compass-outline:{ .lg .middle } **Start with the journey**

    ---

    Seven short pages walking from the original problem framing through
    the eight-agent FastAPI orchestrator, the eleven MCP servers, the
    DuckLake-on-Postgres knowledge graph, and the Next.js reporting app.

    [:octicons-arrow-right-24: Read the journey](journey/index.md)

-   :material-server-network:{ .lg .middle } **Inspect the architecture**

    ---

    System diagrams, the privacy contract that lives in code (not docs),
    the four worked data flows (A/B/C/D), and the eight-agent topology.

    [:octicons-arrow-right-24: Architecture](architecture/overview.md)

-   :material-tools:{ .lg .middle } **Browse the MCP servers**

    ---

    Eleven FastMCP servers wrapping VectorSurv, NWS HeatRisk, MAG HRN,
    ADHS, 211 AZ, WHISPers, iNaturalist, Great AZ Tick Check, wearables,
    SMS, and the DuckDB knowledge-graph query escape-hatch.

    [:octicons-arrow-right-24: MCP servers](mcps/index.md)

-   :material-cellphone-link:{ .lg .middle } **Try the live app**

    ---

    A working anonymous-first reporting flow with EXIF-stripping, ZIP /
    1 km coarsening, optional profile, and a personal dashboard — running
    on a Jetstream2 VM.

    [:octicons-arrow-right-24: Open the live demo](http://epihack-test.cis240692.projects.jetstream-cloud.org/){ target=_blank }

-   :material-database-outline:{ .lg .middle } **Read the schema**

    ---

    A property-graph (`kg.node` / `kg.edge` / `kg.property`) carrying 572
    nodes, 791 edges, and 1027 properties — all 15 Arizona counties, 22
    tribal nations, 16 pathogens, historical outbreaks, datasets, APIs.

    [:octicons-arrow-right-24: Knowledge graph](kg/schema.md)

-   :material-rocket-launch:{ .lg .middle } **Re-deploy from scratch**

    ---

    The Ansible playbook that targets a fresh Jetstream2 VM — Postgres
    catalog, DuckLake, MongoDB for mobile writes, FastAPI agents, all
    eleven MCP servers, and the Next.js app behind nginx.

    [:octicons-arrow-right-24: Ansible / Jetstream2](deploy/ansible.md)

</div>

---

## What's here

| Section | What it covers |
|---|---|
| [Journey](journey/index.md) | The story of how this thing was vibe-coded into existence. Seven pages, one per phase. |
| [Architecture](architecture/overview.md) | System diagrams, the privacy contract, the eight-agent topology, the four data flows. |
| [MCP servers](mcps/index.md) | One page per FastMCP server with its tool inventory and example calls. |
| [App](app/pages.md) | A page-by-page tour of the Next.js reporting app. |
| [Knowledge graph](kg/schema.md) | Schema reference, seed-load order, and example DuckDB queries. |
| [Deploy](deploy/local.md) | Local dev, Ansible on Jetstream2, and GitHub Pages publishing. |
| [Reference](reference/openapi.md) | The OpenAPI spec, MCP tool inventory, test matrix, glossary. |
| [About](about/governance.md) | Governance, security, contributing, changelog, citation. |

## Citing this work

If you use the schema, the MCP designs, or the reporting-app flows in your
own work, cite this repository per the [citation page](about/citation.md).
A `CITATION.cff` is in the repo root for the GitHub "Cite this repository"
button.
