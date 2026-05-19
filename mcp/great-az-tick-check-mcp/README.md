---
title: Great Arizona Tick Check MCP server
---

# `great-az-tick-check-mcp` — Model Context Protocol server for the UA Great Arizona Tick Check

A [Model Context Protocol](https://modelcontextprotocol.io/) server
that wraps the [University of Arizona Cooperative Extension's
**Great Arizona Tick Check**](https://extension.arizona.edu/programs/great-arizona-tick-check)
program — Dr. **Kathleen Walker**'s lab in Forbes 410, Department of
Entomology, UA Tucson — as a set of tools an LLM (Claude Desktop,
Claude Code, Claude API agents, or any other MCP client) can call.

Built for the EpiHack Arizona 2026 [Wildlife & Vector-Borne Diseases
focus group](../../wildlife/index.html) and threaded into
[Scenario A](../../plan/04-data-flows.html) ("Hiker mails in a tick")
of the [end-to-end data flows](../../plan/04-data-flows.html).

> **Mock-by-default.** The Great Arizona Tick Check is a **mail-in**
> program — there is **no public REST API today**. This server ships
> with an in-memory mock backend so the rest of the EpiHack stack can
> develop against it. The mock is good enough to demo the full
> create → status → species + pathogen-results flow in a single LLM
> session, and bad enough that you would never confuse it for the
> real lab. When a real backend ships, set `GATTC_BACKEND_URL` in the
> environment and the client routes to it instead (see
> [Pointing at a real backend](#pointing-at-a-real-backend)).

## What it does

| MCP tool | What it returns |
|---|---|
| `gattc_create_submission` | A new submission ID, the lab's static mailing address, a placeholder mailing-label URL, a status URL, and the estimated turnaround in days. |
| `gattc_submission_status` | Current status (`received` → `identifying` → `testing` → `complete`); once `complete` it also returns `species` and `pathogens_tested`. |
| `gattc_species_identification_from_photo` | A *low-confidence* best-guess species + alternatives from a short list of AZ-relevant ticks. Always carries `verify_with_lab: true`. |
| `gattc_pathogens_screened` | Reference list of pathogens the Walker lab screens for, each with its ICD-10 code. |
| `gattc_mailing_label` | Placeholder mailing-label URL (PDF or PNG) plus the lab's mailing address. |

Plus two MCP **resources**: `gattc://mailing-address` and
`gattc://az-tick-species` so an LLM can pull them as context without
having to call a tool.

## Why this matters for EpiHack

The Great Arizona Tick Check is the
[closest thing Arizona has](../../wildlife/resources.html#university-of-arizona-cooperative-extension-—-great-arizona-tick-check)
to a statewide participatory tick-surveillance program — exactly the
pattern EpiHack is trying to scale across heat and vector-borne
disease. Wrapping it as an MCP server lets an LLM:

- Hand a hiker a printable mailing label and the lab's address in one
  call (Scenario A, step 9).
- Poll for the lab's species identification and PCR results as soon
  as they land, then write them back into the
  [DuckLake knowledge graph](../../schema/).
- Give the Triage Agent an "if you see a tick like this, here's what
  the Walker lab screens for" reference table without bespoke glue
  code.

## Pathogens screened

The reference list returned by `gattc_pathogens_screened`. ICD-10
codes for *Rickettsia rickettsii* come from
[`schema/deep/standards.sql`](../../schema/deep/standards.sql); the
others come from
[`schema/deep/pathogens.sql`](../../schema/deep/pathogens.sql) and
standard CDC tick-borne disease references.

| Pathogen | Disease | ICD-10 |
|---|---|---|
| *Rickettsia rickettsii* | Rocky Mountain spotted fever | A77.0 |
| *Rickettsia parkeri* | R. parkeri rickettsiosis | A77.8 |
| *Borrelia burgdorferi* | Lyme disease | A69.20 |
| *Anaplasma phagocytophilum* | Anaplasmosis | A77.49 |
| *Babesia microti* | Babesiosis | B60.0 |
| *Ehrlichia chaffeensis* | Ehrlichiosis | A77.40 |

## AZ-relevant tick species

The short list `gattc_species_identification_from_photo` chooses
from:

- **Brown dog tick** (*Rhipicephalus sanguineus*) — dominant
  statewide; principal RMSF vector, especially in tribal-community
  clusters.
- **Western black-legged tick** (*Ixodes pacificus*) — Lyme +
  anaplasmosis; documented in Mohave County.
- **Gulf Coast tick** (*Amblyomma maculatum*) — *R. parkeri* vector;
  range-expanding into Cochise and Santa Cruz counties.
- **Rocky Mountain wood tick** (*Dermacentor andersoni*) — Colorado
  tick fever, RMSF, tularemia at higher elevations.
- **American dog tick** (*Dermacentor variabilis*) — secondary RMSF
  vector, also tularemia.

## Pointing at a real backend

By default the server runs in **mock mode** — submissions live in a
dict for the lifetime of the process. To swap in a real HTTP backend
once the Walker lab (or a partner) ships one:

```bash
export GATTC_BACKEND_URL=https://great-arizona-tick-check.example/api
export GATTC_API_TOKEN=...    # optional, if the real backend needs auth
```

The HTTP path in [`client.py`](./src/great_az_tick_check_mcp/client.py)
is intentionally a thin stub that raises `NotImplementedError` until
the request bodies + response parsing for the real API are filled in.
That way a misconfigured deployment (typo'd URL, wrong env) fails
loudly rather than silently masquerading as a working mock.

A `.env.example` template is included; copy to `.env` and source it.

## Submitting ticks the real way

This server doesn't replace the real program — it shadows it. The
real mailing address (printed verbatim by `gattc_create_submission`
and the `gattc://mailing-address` resource) is:

> Dr. Kathleen Walker
> Forbes 410, Department of Entomology
> P.O. Box 210036
> University of Arizona
> Tucson, AZ 85721

See the
[Great Arizona Tick Check homepage](https://extension.arizona.edu/programs/great-arizona-tick-check)
and
[Help Us page](https://extension.arizona.edu/programs/great-arizona-tick-check/help-us)
for current submission instructions (a tick in a sealed bag, ideally
frozen 1–2 days, with date + city/town + ZIP).

## Install &amp; run

### As a Claude Desktop MCP server

1. Install [`uv`](https://docs.astral.sh/uv/) if you don't have it.
2. Drop the snippet in [`examples/claude_desktop_config.json`](./examples/claude_desktop_config.json)
   into your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`
   on macOS, `%APPDATA%\Claude\claude_desktop_config.json` on Windows).
3. Replace the path with the absolute path to this directory.
4. Leave `GATTC_BACKEND_URL` empty to run in mock mode, or fill it in
   for a real backend.
5. Restart Claude Desktop.

### Standalone

```bash
cd mcp/great-az-tick-check-mcp
uv sync
uv run great-az-tick-check-mcp                 # stdio (default)
MCP_TRANSPORT=streamable-http uv run great-az-tick-check-mcp  # HTTP
```

### Tests

```bash
cd mcp/great-az-tick-check-mcp
uv run pytest
```

Synthetic-data tests exercise the full create → status → complete
flow, the species-guess response shape, the deterministic Walker-lab
mailing address text, mailing-label URL generation, and the
pathogens-screened reference list. No live credentials and no
network calls.

## What a real Walker-lab integration must override

These are the deliberate stubs in this server. A future PR plugging
the real backend in should at minimum:

- Fill in `client._HttpBackend.create()` and `.get()` to POST/GET
  against the real submission endpoint. The `Submission` dataclass
  is the contract — whatever shape the real API returns has to map
  into it.
- Replace the deterministic status progression in
  `client._MockBackend.get()` with whatever the real backend reports.
- Replace `client._label_url` / `client._status_url` with whatever
  signed-URL or routing scheme the real backend uses (override the
  `GATTC_LABEL_BASE` and `GATTC_STATUS_BASE` env vars if just the
  base changes).
- Plug a real image-classifier into `client.species_guess()` (the
  current implementation is deterministic and ignores the photo;
  the `verify_with_lab: true` flag is the safety net).

## License

MIT, alongside the rest of `epihack-2026`.
