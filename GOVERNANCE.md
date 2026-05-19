---
title: "EpiHack Arizona 2026 — Governance"
---

# Governance

This document defines how the EpiHack Arizona 2026 stack is governed
post-event. It encodes the cross-cutting governance track from
[`plan/05-roadmap.md`](./plan/05-roadmap.md) and is binding on
maintainers, agency-affiliated committers, and contributing
agents (human or LLM).

The intent is not bureaucracy. It is a small, durable structure that
keeps the four founding agencies in the loop on anything that could
change how surveillance data is collected, suppressed, or routed —
and that gives tribal partners a hard veto on anything touching
tribal data.

## Standing review board

The standing review board has four seats. Membership is by
organization, not by individual, so transitions inside an agency do
not require a repo change.

| Seat | Organization | Scope of authority |
|---|---|---|
| **ADHS** | Arizona Department of Health Services — Vector-Borne & Zoonotic Diseases program and the Heat Preparedness Network | Statewide arbovirus + heat-mortality surveillance; reportable-condition definitions; triage-class thresholds |
| **AZGFD** | Arizona Game and Fish Department — Wildlife Health Program | Wildlife observation flows; WHISPers + iNaturalist enrichment behaviour; species-attribution rules |
| **ITCA-TEC** | Inter Tribal Council of Arizona — Tribal Epidemiology Center | All decisions touching tribal data; veto authority below |
| **Maricopa Vector Control** | Maricopa County Environmental Services Department, Vector Control Division | Mosquito / tick pool data flows; cluster-detection threshold calibration for VBD; Phoenix-metro cooling-center integrations |

The board operates by lazy consensus on the GitHub PR thread (any
member can request changes; absence is consent after a 5-business-day
window). Two domains escape lazy consensus and require explicit signoff:

* **Tribal-data changes** require ITCA-TEC explicit approval (see
  [Tribal-partner veto](#tribal-partner-veto) below).
* **Cluster-detection threshold changes** require explicit approval
  from at least one of ADHS or Maricopa Vector Control, depending on
  vertical.

## Proposal-then-merge cadence

Changes fall into three buckets with different review depths.

### Schema changes — *proposal first*

Anything in [`schema/`](./schema/) — node types, edge predicates,
property keys, slug renames, view definitions.

* Open an **issue first** describing the proposed change, the
  affected seeds, and the downstream consumers (`mcp/knowledge-graph-mcp/`,
  `dashboard/`, `today/`, `agents/`).
* Wait at least **5 business days** for review-board comment.
* Then open the PR implementing the change, linking the issue.
* Slug renames must include a deprecation note in the PR description;
  the old slug stays valid (as an alias edge) for one full release
  cycle.

### Runtime / orchestrator changes — *PR first, fast review*

Changes in [`agents/`](./agents/), [`app/`](./app/),
[`dashboard/`](./dashboard/), [`today/`](./today/).

* Open the PR. The board reviews on the standard lazy-consensus
  cadence.
* Cluster-detection threshold edits (`agents/src/onehealth_agents/cluster.py`,
  `plan/CLUSTER-CALIBRATION.md`) trigger the explicit-approval rule
  above.
* Consent-enforcement edits (`agents/src/onehealth_agents/validation.py`)
  trigger ITCA-TEC explicit approval if the change weakens any
  tribal-data check, removes any cell-suppression rule, or expands
  what enters `agent_run` digests.

### MCP server changes — *PR first, prefix-scoped review*

Changes in [`mcp/<server>/`](./mcp/).

* New MCP server: follow the recipe in [`mcp/README.md`](./mcp/README.md)
  and [`CONTRIBUTING.md`](./CONTRIBUTING.md).
* Existing MCP server: the seat whose agency owns the upstream data
  source is the de-facto reviewer (ADHS for `adhs-mcp`, AZGFD for
  `whispers-mcp` + `inaturalist-mcp` wildlife-context use, Maricopa
  Vector Control for `mag-hrn-mcp` and `vectorsurv` pool tools, etc.).
* `knowledge-graph-mcp` SQL-escape-hatch edits require approval from
  any two seats (the escape hatch is the highest-blast-radius surface
  in the repo).

## Tribal-partner veto

ITCA-TEC and any participating tribal nation hold an unconditional
veto on every change that touches tribal data, including but not
limited to:

* New MCP servers that proxy tribal data sources (e.g. the optional
  `navajo-ec-mcp` proxy described in
  [`plan/05-roadmap.md`](./plan/05-roadmap.md) Phase 2).
* Changes to the Validation Agent's tribal-data suppression rules.
* New dashboard views, public or private, that aggregate at a
  geography below the county level if any constituent ZCTA
  intersects tribal land.
* New triage classes, cluster-detection thresholds, or notification
  routes that change how tribal observations are handled.
* Changes to `consent_profile` semantics in
  [`schema/deep/application.sql`](./schema/deep/application.sql).
* Changes to what tribal-jurisdiction observations contribute to
  `agent_run` digests or to any public-facing artifact.

A veto is recorded on the PR. There is no override mechanism.

## Tribal-partner opt-in posture

The default for every new tribal partner is **no data flows in
either direction** until an MOU is signed *and* a corresponding
`consent_profile` row is added with `default = opt_in`. There is no
opt-out posture and no default that shares tribal data; tribes opt in
explicitly per data source.

Concretely:

* New `tribe.*` nodes are added to
  [`schema/deep/tribes.sql`](./schema/deep/tribes.sql) for reference
  but ship with `consent_profile.default = suppress` until an MOU
  attaches an opt-in.
* MCP servers that proxy tribal data sources do not deploy until the
  MOU is recorded in the repo and the sunset clause below is
  encoded in the server's `pyproject.toml` `description` and README.
* Public dashboards apply tribal-suppression *before* aggregation,
  not after, so cell-count thresholds cannot be reverse-engineered
  from neighbouring cells.

## Conflict-of-interest disclosure

Committers affiliated with one of the standing-board agencies (ADHS,
AZGFD, ITCA-TEC, Maricopa Vector Control) or any state, county, or
tribal health authority must disclose that affiliation:

* In their **GitHub profile** (the `Company` field is sufficient), or
* In the **PR description** of any PR they author or review when the
  PR materially affects their agency's data flow or threshold
  decisions, or
* In a comment on this file if a structural conflict exists (e.g.
  serving simultaneously as a committer and a vendor whose product
  this repo integrates with).

A disclosed conflict does not disqualify the contributor; it informs
reviewers, who may ask for an independent second review. An
**undisclosed** conflict that is later discovered is grounds for
revoking commit access pending board review.

## Sunset clauses

Any MCP server that acts as a proxy for a tribal data source operates
**only as long as the underlying MOU is live**. Specifically:

* The MOU expiry date is captured in the server's `pyproject.toml`
  `description` field and in the first line of the server's
  `README.md`.
* On MOU expiry, the server's `__main__.py` entry point refuses to
  start unless `MOU_RENEWED_THROUGH=<ISO-date>` is set in the
  environment to a date later than today. This is a hard runtime
  gate, not just a comment.
* Renewal is recorded as a PR updating both files plus a corresponding
  `consent_profile` row in the kg.
* The board reviews proxy-server status quarterly; any proxy whose
  MOU has lapsed for more than 90 days is removed from the repo
  (not just disabled) at the next maintenance cycle.

The same posture applies, less formally, to MCP servers proxying
non-tribal partner data (ADHS, MAG, 211 Arizona, USGS WHISPers,
iNaturalist): if the data-sharing agreement lapses, the server is
disabled in deployment configs and the README header is updated.

## Amending this document

This file is amended via PR, with the same lazy-consensus rules as
runtime changes, *plus*: amendments to the [Standing review
board](#standing-review-board) section, the [Tribal-partner
veto](#tribal-partner-veto) section, or the [Sunset
clauses](#sunset-clauses) section require explicit approval from all
four seats. Other sections may be amended by lazy consensus.
