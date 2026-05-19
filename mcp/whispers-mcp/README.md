---
title: WHISPers MCP server
---

# `whispers-mcp` — Model Context Protocol server for USGS WHISPers

A [Model Context Protocol](https://modelcontextprotocol.io/) server
that exposes the U.S. Geological Survey National Wildlife Health
Center's [WHISPers](https://whispers.usgs.gov/) — the **Wildlife
Health Information Sharing Partnership event reporting system** — as
a set of tools an LLM (Claude Desktop, Claude Code, Claude API
agents, or any other MCP client) can call.

Built for the EpiHack Arizona 2026 [Wildlife & Vector-Borne Diseases
focus group](../../wildlife/index.html).

## What WHISPers is

WHISPers is the federal source-of-truth for wildlife
mortality/morbidity events. It is a web-based repository of basic
information on current and historic wildlife mortality (death) and/or
morbidity (illness) events — bird die-offs, prairie-dog plague,
hantavirus rodent surveillance, HPAI in wild waterfowl — reported by
federal, state, tribal, and academic partners and curated by the USGS
NWHC. Partners use it to alert each other to emerging wildlife
disease activity; the public-portal subset of events is the layer
this MCP wraps.

* Public portal: <https://whispers.usgs.gov/>
* Backing service codebase:
  [USGS-WiM/whispersservices](https://github.com/USGS-WiM/whispersservices)
  (archived 2023-06-30; active mirror at
  [code.usgs.gov/WiM/whispersservices](https://code.usgs.gov/WiM/whispersservices)).
* Production API root: `https://whispers.usgs.gov/api/` (confirmed
  against the Angular frontend's
  `src/environments/environment.prod.ts`).

## What it does

Every tool name starts with `whispers_`.

| MCP tool | Backed by | Auth |
|---|---|---|
| `whispers_events_recent` | `GET /api/eventsummaries/` (with `public=true` + date filter) | none |
| `whispers_event_detail` | `GET /api/eventdetails/{id}/` | none |
| `whispers_events_bbox` | `GET /api/eventsummaries/` + client-side bbox filter | none |
| `whispers_events_by_species` | `GET /api/eventsummaries/` (species substring) | none |
| `whispers_events_by_diagnosis` | `GET /api/eventsummaries/` (diagnosis substring) | none |
| `whispers_az_recent_summary` | `GET /api/eventsummaries/?administrative_level_one_name=AZ` + local aggregation | none |

Plus two MCP **resources**:

- `whispers://event-types` — the WHISPers event-type enumeration
  (`Mortality/Morbidity`, `Surveillance`).
- `whispers://diagnosis-vocabulary` — a representative slice of the
  WHISPers diagnosis controlled vocabulary
  (`Avian influenza, HPAI`, `Yersinia pestis`, `Hantavirus`,
  `West Nile virus`, …). Refresh from
  `/api/diagnoses/?no_page=true` for the authoritative full list.

### Auth boundary

All read tools above are **guaranteed-no-auth**: the upstream
`EventViewSet.get_queryset()` filters anonymous callers to rows where
`public=True`, so the public subset of WHISPers is freely callable.
A future write-oriented tool (creating events, adding diagnoses) or
one calling non-public/admin-only viewsets — `userchangerequests`,
`servicerequests`, drafts, restricted contacts — would need a
WHISPers Gateway account. The MCP server keeps the auth boundary at
the server process, never sending credentials through the LLM.

## Why this matters for EpiHack

WHISPers is exactly the kind of agency dataset the
[`EnrichmentAgent`](../../agents/src/onehealth_agents/enrichment.py)
needs to attach to community VBD reports: "did anyone find dead
prairie dogs near this Coconino check-in last week?" One bbox call
answers that. Scenario D in
[`plan/04-data-flows.md`](../../plan/04-data-flows.md) walks through
the exact ADHS dashboard query against the resulting graph nodes.

## Mock-by-default fallback

The build sandbox the MCP was authored in cannot reach
`whispers.usgs.gov`, and many EpiHack venues will have similarly
restrictive networks. To keep tests hermetic and demos resilient,
`whispers-mcp` ships with a small canned AZ-centric dataset in
[`src/whispers_mcp/canned.py`](./src/whispers_mcp/canned.py). The
10-row dataset is modelled on real history:

- 1993 Four Corners hantavirus outbreak (deer mouse, Sin Nombre).
- 2022–2023 HPAI H5N1 wild-waterfowl detections in Maricopa and Yuma.
- 2024–2025 plague (Yersinia pestis) in Gunnison's prairie dogs on
  the Colorado Plateau (Coconino + a cross-border NM control row).
- 2024 WNV-positive American crows in Pima County.
- 2025 EHDV in mule deer near Patagonia (matches Scenario A).
- An out-of-state Salton Sea HPAI row so the bbox/state filters have
  a negative example.

Fallback behaviour:

| `WHISPERS_USE_MOCK` | live host reachable | result |
|---|---|---|
| unset (default) | yes | live API |
| unset (default) | no | canned dataset (silent fallback) |
| `1` | — | canned dataset always |

Set `WHISPERS_DISABLE_FALLBACK=1` to surface upstream errors
instead of silently degrading — useful in production where you'd
rather get paged than serve stale-looking data.

Event IDs in the canned dataset are intentionally in the 9 000 000+
range so they don't collide with real WHISPers rows; the
`public_url` fields will 404 against the live UI on purpose.

## Install & run

### As a Claude Desktop MCP server

1. Install [`uv`](https://docs.astral.sh/uv/) if you don't have it.
2. Drop the snippet in
   [`examples/claude_desktop_config.json`](./examples/claude_desktop_config.json)
   into your Claude Desktop config.
3. Replace the path with the absolute path to this directory.
4. Restart Claude Desktop.

No credentials are required for the default tool set.

### Standalone

```bash
cd mcp/whispers-mcp
uv sync
uv run whispers-mcp                                # stdio (default)
MCP_TRANSPORT=streamable-http uv run whispers-mcp  # HTTP
WHISPERS_USE_MOCK=1 uv run whispers-mcp            # force canned data
```

### Tests

```bash
cd mcp/whispers-mcp
uv run pytest
```

All tests are offline; they exercise the canned dataset directly via
the `WhispersClient(use_mock=True)` code path.

## Endpoint overrides

Every path is overridable via env — `WHISPERS_PATH_EVENTS`,
`_EVENT_SUMMARIES`, `_EVENT_DETAILS`, `_EVENT_TYPES`,
`_EVENT_LOCATIONS`, `_SPECIES`, `_DIAGNOSES`, `_ADMIN_L1`,
`_ADMIN_L2`. Set `WHISPERS_BASE_URL` to point at a staging deploy.

See [`.env.example`](./.env.example) for the full list.

## License

MIT, alongside the rest of `epihack-2026`.
