---
title: iNaturalist MCP server
---

# `inaturalist-mcp` — Model Context Protocol server for iNaturalist

A [Model Context Protocol](https://modelcontextprotocol.io/) server
that wraps the [iNaturalist](https://www.inaturalist.org/) public API
as a set of tools an LLM (Claude Desktop, Claude Code, Claude API
agents, or any other MCP client) can call.

Built for the EpiHack Arizona 2026 [Wildlife & Vector-Borne Diseases
focus group](../../wildlife/index.html).

> **Why iNaturalist?** iNaturalist is the world's largest open
> biodiversity-observations dataset — every record is a photo with a
> timestamp, GPS, and a community-verified species ID, released under
> permissive CC licenses. For One Health surveillance in Arizona it
> gives us a real-time citizen-science feed of tick, mosquito, flea,
> and wildlife-reservoir sightings that complements the
> structured-submission programs (the Walker lab's
> [`great-az-tick-check-mcp`](../great-az-tick-check-mcp/), AZGFD
> wildlife mortality, VectorSurv trap data). When a hiker photographs
> a tick on their dog in Cochise County, the photo shows up in
> iNaturalist days before the physical specimen reaches the lab.

## What it does

| MCP tool | What it does |
|---|---|
| `inat_observations_bbox` | Public observations inside a `(min_lon, min_lat, max_lon, max_lat)` box, filtered by taxon + days + quality grade. |
| `inat_observations_near` | Convenience wrapper for `(lat, lon, radius_km)` — bbox + haversine sort by distance. |
| `inat_observations_by_taxon` | Observations of a specific `taxon_id` in a `place_id` (default: AZ, place_id=53). |
| `inat_taxon_lookup` | Resolve a name (`"deer mouse"`) or numeric ID to a taxon record. |
| `inat_species_summary_az` | Counts by month and by AZ county-equivalent place for a taxon. |
| `inat_tick_observations_az` | Convenience: research-grade tick observations in AZ — the citizen-science cross-check for `great-az-tick-check-mcp`. |

Plus two MCP **resources**:

- `inat://tick-genera-az` — AZ-relevant tick genera + species with
  iNaturalist taxon IDs (quick reference; skip the lookup
  round-trip).
- `inat://rate-limits` — documented iNaturalist API rate-limit
  policy and how this server honours it.

## Why this matters for EpiHack

| Scenario | What this MCP adds |
|---|---|
| Hiker mails in a tick (`plan/04-data-flows.md` Scenario A) | The Walker lab gets the specimen; iNaturalist gives a *near-real-time photo stream* of other ticks observed in the same area in the same week. The Triage Agent can show *"4 other brown-dog-tick photos within 25 km in the last 30 days"* on the submission confirmation screen. |
| AZGFD wildlife mortality (Scenario B) | When an agency reports a die-off of prairie dogs in Apache County, this MCP gives the historical iNaturalist baseline of *Cynomys gunnisoni* sightings in the same place. |
| Knowledge-graph backfill | Every observation row carries an `observation_id` + `url`; the Knowledge Update Agent can dereference both back to the canonical iNaturalist record. |

## User-Agent requirement

The iNaturalist API **requires every client to identify itself with
a meaningful User-Agent header**
([API recommended practices](https://www.inaturalist.org/pages/api+recommended+practices)).
Anonymous traffic gets throttled or blocked, which would poison the
shared rate-limit budget for the whole EpiHack stack.

So this server:

1. **Refuses to start** if `INAT_USER_AGENT` is unset (the
   `__main__` entry point exits with code 2 and a clear error).
2. **Sets the header on every outbound request** from the
   `INaturalistClient`.

Pick a UA that includes a project name, a version, and a contact:

```
INAT_USER_AGENT='epihack-az-2026/0.1 (contact: ops@example.org)'
```

## Rate limits

Sourced from
[`api.inaturalist.org/v1/docs/`](https://api.inaturalist.org/v1/docs/)
and the
[iNaturalist API recommended practices](https://www.inaturalist.org/pages/api+recommended+practices)
page:

- **~100 requests per minute** per IP (iNat asks clients to stay
  well below this).
- **~10,000 requests per day** per IP.
- Maximum **per-page = 200** observations; deeper paging beyond
  10,000 results requires id-based cursors (`id_above` +
  `order_by=id`).
- 429 responses include a **`Retry-After`** header — the client
  sleeps for that many seconds (capped at 60s) and retries once.

For the full server-side policy text, query the
`inat://rate-limits` resource.

## Place + taxon IDs

iNaturalist uses stable numeric IDs for both places and taxa. The
defaults shipped here:

| Key | Default ID | Source |
|---|---|---|
| Arizona (US state) | **53** | confirm at <https://api.inaturalist.org/v1/places/53> |
| Ticks (order Ixodida) | 47119 | confirm at <https://www.inaturalist.org/taxa/47119> |
| Mosquitoes (family Culicidae) | 84738 | confirm at <https://www.inaturalist.org/taxa/84738> |
| Fleas (order Siphonaptera) | 84377 | confirm at <https://www.inaturalist.org/taxa/84377> |
| Rodents (order Rodentia) | 43698 | confirm at <https://www.inaturalist.org/taxa/43698> |
| *Rhipicephalus sanguineus* (brown dog tick) | 84219 | |
| *Dermacentor andersoni* (Rocky Mountain wood tick) | 126099 | |
| *Dermacentor variabilis* (American dog tick) | 84223 | |
| *Ixodes pacificus* (Western black-legged tick) | 62366 | |
| *Peromyscus maniculatus* (deer mouse — hantavirus) | 46559 | |
| *Cynomys gunnisoni* (Gunnison's prairie dog — plague) | 46211 | |
| *Otospermophilus variegatus* (rock squirrel — plague) | 73704 | |
| *Sylvilagus audubonii* (desert cottontail — tularemia) | 43130 | |

**Every ID is env-overridable** (`INAT_AZ_PLACE_ID`, `INAT_TAXON_*`).
A contributor who finds a drifted ID can patch the env without a
code change. The `inat_taxon_lookup` tool is the authoritative
runtime check.

## Mock-by-default fallback

This server is **mock-by-default** in the same sense as
[`great-az-tick-check-mcp`](../great-az-tick-check-mcp/): the build
sandbox runs all tests without network access, against a canned
dataset of ~20 synthetic AZ observations covering ticks,
mosquitoes, fleas, deer mice, prairie dogs, rock squirrels, and
cottontails (see
[`src/inaturalist_mcp/canned_data.py`](./src/inaturalist_mcp/canned_data.py)).

Behaviour:

- Set `INAT_OFFLINE=1` to force the canned-data path (no HTTP
  requests will be made).
- On any `httpx.ConnectError` / `ReadError`, the client
  **transparently falls back to the canned dataset** and tags the
  response with `source: "canned"` so the calling LLM knows which
  it got. Live responses carry `source: "live"`.

## Cross-reference

This server is the citizen-science complement to the structured
[`great-az-tick-check-mcp`](../great-az-tick-check-mcp/):

- **`great-az-tick-check-mcp`** = mail in a physical tick to the
  Walker lab; deterministic species ID + PCR pathogen screen.
- **`inaturalist-mcp`** = scrape the public photo stream for the
  same taxa in the same place + time window.

The two together let the Triage Agent answer *"is this tick the
species I think it is?"* with both a definitive lab path (mail it
in) and a citizen-science prior (here are 4 other people's photos
of the same species in the same county in the last month).

## iNaturalist open-data ethos

iNaturalist observations are released under
[Creative Commons licenses](https://www.inaturalist.org/pages/help#cc)
(the most permissive default is `CC BY-NC`; observers can pick more
or less permissive). The platform is a joint initiative of the
California Academy of Sciences and the National Geographic Society.

Visit <https://www.inaturalist.org/> for the full project, the
[GBIF data portal](https://www.gbif.org/dataset/50c9509d-22c7-4a22-a47d-8c48425ef4a7)
for the research-grade research-grade exports, and
<https://www.inaturalist.org/pages/api+recommended+practices> for
the API rules-of-the-road.

If you're publishing analysis built on iNaturalist data, credit
individual observers (the `user_login` field on each row) per the
license attached to the photo.

## Install & run

### As a Claude Desktop MCP server

1. Install [`uv`](https://docs.astral.sh/uv/) if you don't have it.
2. Drop the snippet in [`examples/claude_desktop_config.json`](./examples/claude_desktop_config.json)
   into your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`
   on macOS, `%APPDATA%\Claude\claude_desktop_config.json` on Windows).
3. Replace the path with the absolute path to this directory.
4. Fill in `INAT_USER_AGENT` — the server refuses to start without it.
5. Restart Claude Desktop.

### Standalone

```bash
cd mcp/inaturalist-mcp
uv sync
INAT_USER_AGENT='epihack-az-2026/0.1 (contact: ops@example.org)' \
  uv run inaturalist-mcp                                          # stdio (default)
MCP_TRANSPORT=streamable-http \
INAT_USER_AGENT='epihack-az-2026/0.1 (contact: ops@example.org)' \
  uv run inaturalist-mcp                                          # HTTP
```

### Tests

```bash
cd mcp/inaturalist-mcp
uv run pytest
```

All tests are offline; no live API access required.

## License

MIT, alongside the rest of `epihack-2026`.
