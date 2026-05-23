# The journey

Seven short pages on how the **AZ One Health Sentinel** was built across
EpiHack Arizona 2026 — from a one-paragraph problem statement to a
production-ish multi-tier stack on a Jetstream2 VM. Each page follows the
same structure:

1. **What we wanted** (one paragraph)
2. **What we built** (file paths, tool counts, links into Reference)
3. **What it looks like** (screenshots)
4. **Decisions & trade-offs**
5. **Where to go next**

| # | Page | One-liner |
|---|---|---|
| 01 | [Frame the problem](01-frame.md) | The ten-prompt design worksheet, two focus groups, and the figures that anchor every later decision. |
| 02 | [Map the data sources](02-map.md) | 30+ anchor resources, the parameter-mapping table, and the choice of which APIs to wrap. |
| 03 | [Build the MCPs](03-mcps.md) | Eleven FastMCP servers, scaffolded from a single template, all tested offline. |
| 04 | [Stand up the store](04-store.md) | DuckLake-on-Postgres + MongoDB for mobile, with a property-graph schema and the kg.* seed-load order. |
| 05 | [Orchestrate the agents](05-orchestrate.md) | Eight Pydantic agents behind a FastAPI surface, gated by the privacy contract in `validation.py`. |
| 06 | [Ship the app](06-app.md) | Next.js 16, anonymous-first, EXIF-stripped, with profile enrichment and a personal dashboard. |
| 07 | [Vibe-coding history](07-vibe-coding.md) | How we vibe-coded the whole thing with Claude Code — prompts, pivots, what worked, what didn't. |

!!! tip "Reading order"
    The journey is sequenced for a *first* read. If you already know the
    stack, jump straight to the [Architecture overview](../architecture/overview.md)
    or to the [MCP server pages](../mcps/index.md).
