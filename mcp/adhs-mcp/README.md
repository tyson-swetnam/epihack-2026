---
title: ADHS MCP server
---

# `adhs-mcp` — Model Context Protocol server for Arizona Department of Health Services public data

A [Model Context Protocol](https://modelcontextprotocol.io/) server
that wraps [Arizona Department of Health Services](https://www.azdhs.gov/)
public surveillance data — the **weekly arbovirus surveillance
summary**, the **annual heat-mortality report series** (published at
[pub.azdhs.gov/health-stats/report/heat/](https://pub.azdhs.gov/health-stats/report/heat/)),
zoonotic case counts (hantavirus, plague, rabies, RMSF, tularemia),
the ADHS Vector-Borne & Zoonotic Diseases program, and the Heat
Preparedness Network ArcGIS map — as a set of tools an LLM (Claude
Desktop, Claude Code, Claude API agents, or any other MCP client) can
call.

Built for the EpiHack Arizona 2026
[Heat](../../heat/index.html) and
[Wildlife & Vector-Borne Diseases](../../wildlife/index.html) focus
groups, and threaded into the multi-MCP joins in
[`plan/02-mcp-integration.md`](../../plan/02-mcp-integration.html).

> **Mock-by-default.** ADHS does **not** publish a clean REST API
> today. Surveillance reports are distributed as **PDFs**
> (heat-mortality series, weekly vector-borne summaries) and the Heat
> Preparedness Network lives on an
> [ArcGIS Experience dashboard](https://experience.arcgis.com/experience/c5bdf9ab90894e1baa5860c450dedb3b).
> This server ships with **canned data** sourced from those reports
> and from the EpiHack knowledge graph (`schema/heat.sql`,
> `schema/deep/standards.sql`, `heat/04-vulnerable-populations.md`,
> `wildlife/resources.md`). The canned constants live in a single
> file — [`src/adhs_mcp/canned_data.py`](./src/adhs_mcp/canned_data.py)
> — so a contributor updating the numbers from a new ADHS report only
> has to touch that file. Set `ADHS_BACKEND_URL` in the environment
> to swap in a real HTTP backend once one ships.

## What it does

| MCP tool | What it returns |
|---|---|
| `adhs_recent_cases` | Weekly case counts (`week_of`, `county`, `confirmed`, `probable`, `source_report_url`) for one of WNV, SLEV, DENV, ZIKV, HANTAVIRUS, PLAGUE, RABIES, RMSF, TULAREMIA. |
| `adhs_heat_mortality_summary` | Annual heat-mortality counts (statewide + per-county) for 2013–2024. |
| `adhs_arbovirus_surveillance_summary` | Weekly arbovirus rows: positive mosquito pools, sentinel-chicken seroconversion (where active), human + equine cases, county trap-network size. |
| `adhs_vector_borne_zoonotic_program` | Structured description of the ADHS VBZD program — pathogens monitored, labs, reporting cadence. |
| `adhs_heat_preparedness_network` | Pointer to the ADHS Heat Preparedness Network ArcGIS map + season window. |
| `adhs_reportable_conditions` | ICD-10-CM / SNOMED CT / CDC NNDSS coded list of AZ-reportable conditions. |

Plus two MCP **resources**:

- `adhs://pathogen-acronyms` — same shape as
  `vectorsurv://disease-acronyms` but pinned to ADHS terminology
  (covers the zoonotic + tick-borne pathogens VectorSurv itself
  doesn't carry).
- `adhs://heat-mortality-summary-text` — human-readable summary text
  from [`heat/04-vulnerable-populations.md`](../../heat/04-vulnerable-populations.md)
  with links back to the ADHS report portal.

## Where the canned numbers came from

| Datum | Value | Source |
|---|---|---|
| AZ heat deaths 2013–2024 (cumulative) | >4,320 | `heat/04-vulnerable-populations.md`, also encoded as `group.heat / az_heat_deaths_2013_2024` in `schema/heat.sql`. |
| AZ heat deaths 2023 | 990 | Same, plus `group.heat / az_heat_deaths_2023`. |
| AZ heat deaths 2024 | 602 | Provided in the task brief; preliminary ADHS figure. |
| AZ heat ER visits / year | ~4,298 | `heat/04-vulnerable-populations.md` + `group.heat / az_heat_er_visits_per_year` in `schema/heat.sql`. |
| MCDPH surveillance start year | 2006 | `heat/04-vulnerable-populations.md` (2006); `schema/heat.sql` (2005). |
| Maricopa Vector Control trap count | 800+ | `wildlife/resources.md` ("Over 800 vector traps county-wide"). |
| MAG HRN sites | 200+ | `schema/heat.sql / group.heat / mag_hrn_sites`. |
| ADHS Heat Preparedness Network map URL | `experience.arcgis.com/experience/c5bdf9ab90894e1baa5860c450dedb3b` | `schema/heat.sql / tool.adhs_heat_map`. |
| ADHS heat-mortality portal | `pub.azdhs.gov/health-stats/report/heat/` | `schema/heat.sql / tool.adhs_heat_mortality_dash`. |
| ICD-10 / SNOMED / NNDSS codes | various | `schema/deep/standards.sql`. |

Per-year statewide deaths for **2013–2022** are interpolated to bend
between the 2014–2018 baseline and the 2020-onward escalation
documented in MCDPH + ADHS reports. **2023 (990)** and **2024 (602)**
are taken directly from the headline figures. **Per-county splits**
(Maricopa / Pima / Yuma / other) are illustrative — Maricopa carries
~85–90% of the statewide burden each year, consistent with the MCDPH
surveillance footprint. Update these as new ADHS reports drop.

## Why this matters for EpiHack

ADHS sits at the intersection of every multi-MCP join in
[`plan/02-mcp-integration.md`](../../plan/02-mcp-integration.html):

- **VBD triage (Wildlife-Q4)** — when a community VBD report comes
  in, the Triage Agent calls `adhs_recent_cases` for the matching
  pathogen + county to decide whether there is an active outbreak
  context.
- **Cooling-center awareness (Heat-Q1)** — `adhs_heat_preparedness_network`
  is the statewide entry point; `mag-hrn-mcp` carries the detailed
  Phoenix-metro records, `211-az-mcp` carries the utility-assistance
  layer, and `knowledge-graph-mcp` ranks by vulnerable-population
  priority.
- **Vulnerable populations (Heat-Q4)** — `adhs://heat-mortality-summary-text`
  is the static context an LLM pulls before answering "who is most at
  risk?"; `adhs_heat_mortality_summary` is the structured timeseries
  for trend questions.
- **Reportable conditions** — `adhs_reportable_conditions` is the
  ICD-10 / SNOMED / NNDSS bridge between participatory observations
  and the formal NEDSS / NNDSS reporting stack.

## Pointing at a real backend

By default the server runs against the canned constants — all
in-memory, no network. To swap in a real HTTP backend (an ADHS open-
data API, a partner-operated proxy, etc.):

```bash
export ADHS_BACKEND_URL=https://adhs.example/api
export ADHS_API_TOKEN=...    # optional, if the real backend needs auth
```

The HTTP path in
[`client.py`](./src/adhs_mcp/client.py) is a thin stub that raises
`NotImplementedError` until the request bodies + response parsing
for the real API are filled in. That way a misconfigured deployment
(typo'd URL, wrong env) fails loudly rather than silently
masquerading as a working canned-data server.

A `.env.example` template is included; copy to `.env` and source it.

## Updating the numbers

When a new ADHS heat-mortality report drops (typically Q1 of the
following year), or a new weekly arbovirus summary publishes:

1. Open [`src/adhs_mcp/canned_data.py`](./src/adhs_mcp/canned_data.py).
2. Update the relevant constant — `HEAT_MORTALITY_SUMMARY`,
   `RECENT_CASES`, `ARBOVIRUS_SURVEILLANCE`, etc.
3. Re-run `pytest`. The `tests/test_canned_data.py` suite enforces
   the documented totals; any drift fails CI loudly.

## Install &amp; run

### As a Claude Desktop MCP server

1. Install [`uv`](https://docs.astral.sh/uv/) if you don't have it.
2. Drop the snippet in [`examples/claude_desktop_config.json`](./examples/claude_desktop_config.json)
   into your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`
   on macOS, `%APPDATA%\Claude\claude_desktop_config.json` on Windows).
3. Replace the path with the absolute path to this directory.
4. Leave `ADHS_BACKEND_URL` empty to run with the canned data, or
   fill it in for a real backend.
5. Restart Claude Desktop.

### Standalone

```bash
cd mcp/adhs-mcp
uv sync
uv run adhs-mcp                                # stdio (default)
MCP_TRANSPORT=streamable-http uv run adhs-mcp  # HTTP
```

### Tests

```bash
cd mcp/adhs-mcp
uv run pytest
```

All tests are **offline** — no network, no credentials, no scraping.
`tests/test_canned_data.py` pins the headline numbers from
`heat/04-vulnerable-populations.md`; `tests/test_tools.py` exercises
the client + pydantic round-trips for every tool; and
`tests/test_reportable_conditions.py` enforces that every reportable
condition carries either an ICD-10 or a SNOMED CT code (or both).

## Useful links

- ADHS home: <https://www.azdhs.gov/>
- ADHS Heat Mortality Report portal: <https://pub.azdhs.gov/health-stats/report/heat/>
- ADHS Vector-Borne & Zoonotic Diseases program:
  <https://www.azdhs.gov/preparedness/epidemiology-disease-control/vector-borne-zoonotic-diseases/>
- ADHS Heat Preparedness Network (ArcGIS):
  <https://experience.arcgis.com/experience/c5bdf9ab90894e1baa5860c450dedb3b>
- 2012–2023 heat-related mortality PDF:
  <https://www.azdhs.gov/documents/preparedness/epidemiology-disease-control/extreme-weather/pubs/heat-related-mortality-year-2012-2023.pdf>

## License

MIT, alongside the rest of `epihack-2026`.
