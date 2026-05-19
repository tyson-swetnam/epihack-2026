---
title: 211 Arizona MCP server
---

# `211-az-mcp` — Model Context Protocol server for 211 Arizona

A [Model Context Protocol](https://modelcontextprotocol.io/) server that
exposes [211 Arizona](https://211arizona.org/) — operated by
[Solari Crisis & Human Services](https://solariinc.org/) — as a set of
tools an LLM (Claude Desktop, Claude Code, Claude API agents, or any
other MCP client) can call.

Built for the EpiHack Arizona 2026 [Heat focus
group](../../heat/index.html). Powers the Heat-vertical
[Scenario C](../../plan/04-data-flows.html) (unsheltered heat check-in
on a Magenta-HeatRisk day) in cooperation with `nws-heatrisk-mcp` and
`mag-hrn-mcp`.

> **Mock-by-default.** 211 Arizona / Solari Crisis & Human Services
> does **not** publish a public REST API at the time of writing. This
> server ships a canned in-memory backend so the end-to-end agent
> flows in [`plan/04-data-flows.md`](../../plan/04-data-flows.html)
> run offline. When a real API arrives, point `AZ211_BACKEND_URL` at
> it and the client will swap transparently (see
> [Swapping to a real backend](#swapping-to-a-real-backend) below).
>
> Reference for the canned content:
> <https://211arizona.org/crisis/heat-relief/>.

## What it does

| MCP tool | What it returns |
|---|---|
| `az211_transport_to_cooling_center` | Mock ride-dispatch confirmation with a stable `dispatch_id`, ETA, provider, and a callback phone number. Tagged `source: "mock"`. |
| `az211_get_dispatch` | Look up a previously-created dispatch by ID (chained call). |
| `az211_utility_assistance_nearby` | Community-action / LIHEAP providers near the caller, filterable by `kind` (electric / gas / water / weatherization / emergency_ac_repair). 7 canned providers across Maricopa, Pima, Coconino, Yuma, and Navajo / Apache counties. |
| `az211_crisis_referrals` | Phone / hours / languages by topic (`heat`, `housing`, `food`, `behavioral_health`, or `all`). |
| `az211_cooling_center_referral_nearby` | Nearby cooling centers (canned). In production this cross-calls `mag-hrn-mcp.search_centers` for the authoritative Maricopa County registry. |
| `az211_lines` | Structured phone-line directory: main 2-1-1 / 1-877-211-8661, 988 Suicide & Crisis Lifeline, Solari Crisis Response Network, Veterans Crisis Line, ASL video relay. |

Plus two MCP **resources**:

| MCP resource | Payload |
|---|---|
| `az211://hours` | Full operator hours by season (year-round + heat-season expansion May 1 – Sept 30). |
| `az211://languages` | Languages supported, including indigenous-language pathways (Navajo / Diné bizaad, O'odham, Apache, Hopi) routed through partner organisations (ITCA-TEC, Navajo Epidemiology Center, IHS). |

## Why this matters for EpiHack

211 Arizona is the **statewide non-clinical heat-relief on-ramp**:
live operators in English and Spanish, expanded hours during the
May 1 – September 30 heat season, with connect points to cooling
centers, transportation to centers, utility-bill assistance,
weatherization, and emergency AC-repair referrals. It is also the
voice channel most likely to be reachable for callers with no
internet or no smartphone — the same population most exposed to
heat mortality (see
[Heat Q4](../../heat/04-vulnerable-populations.html) and the
"anonymity matters" insight on the Unhoused card in
[World Café Q4 — Heat](../../notes/world-cafe/q4-heat.html)).

Exposing it as an MCP server lets an agent:

- Convert a CHW field observation (Scenario C in
  [plan 04](../../plan/04-data-flows.html)) into an actual dispatch
  in one tool call, with a stable `dispatch_id` the rest of the
  agent run can chain off.
- Look up utility-assistance providers near a caller without leaving
  the conversation.
- Render a "what languages can we help you in?" panel from a single
  MCP resource fetch — including indigenous-language access via
  the right tribal partner, not via the LLM guessing.

## Mock backend

The mock backend lives in
[`src/az211_mcp/mock_data.py`](./src/az211_mcp/mock_data.py) and
[`src/az211_mcp/client.py`](./src/az211_mcp/client.py).

- **Dispatches** are held in a process-local `dict` keyed by
  `dispatch_id`. Two tool calls inside one LLM session share the
  same client instance, so a `transport_to_cooling_center` call
  followed by a `get_dispatch` lookup returns consistent state.
- **Dispatch IDs** use `secrets.token_hex(6)` — 12 hex chars, no
  extra dependency, collision-free for any realistic session.
- **Postal-code → county routing** is a coarse prefix table
  covering the counties named in the canned dataset; unknown ZIPs
  fall back to Maricopa so demos never empty.
- **Every record is tagged `source: "mock"`** so an audit log or
  the knowledge-graph receipt can tell which calls came from real
  vs. canned data.

## Swapping to a real backend

When 211 Arizona ships an API, set `AZ211_BACKEND_URL` (and optionally
`AZ211_API_KEY`) in env. The client will pick the `HttpBackend`
instead of the mock; today that backend raises
`NotImplementedError` on every method so a misconfiguration is loud.
Update
[`src/az211_mcp/client.py::HttpBackend`](./src/az211_mcp/client.py)
to match the live wire format — none of the FastMCP tools or
resources need to change.

## Operating partner & data-sovereignty notes

- **Operator:** [Solari Crisis & Human Services](https://solariinc.org/),
  the statewide crisis line behind both 988 and 211 in Arizona.
- **Tribal access:** indigenous-language calls are warm-transferred to
  [ITCA-TEC](https://itcaonline.com/),
  [Navajo Epidemiology Center](https://nec.navajo-nsn.gov/), and IHS
  Area facilities. Tribal data lives behind tribal sovereignty and
  does not flow back through this MCP server.
- **No PII leaves the MCP boundary.** The MCP server returns dispatch
  metadata (provider, ETA, callback phone) and resource directories
  only — it does not echo back caller PII to the LLM (see
  [`plan/02-mcp-integration.md`](../../plan/02-mcp-integration.html)
  auth + data-sovereignty notes).

## Install & run

### As a Claude Desktop MCP server

1. Install [`uv`](https://docs.astral.sh/uv/) if you don't have it.
2. Drop the snippet in
   [`examples/claude_desktop_config.json`](./examples/claude_desktop_config.json)
   into your Claude Desktop config
   (`~/Library/Application Support/Claude/claude_desktop_config.json`
   on macOS,
   `%APPDATA%\Claude\claude_desktop_config.json` on Windows).
3. Replace the path with the absolute path to this directory.
4. Restart Claude Desktop. The server starts in mock mode with no
   credentials required.

### Standalone

```bash
cd mcp/211-az-mcp
uv sync
uv run az211-mcp                          # stdio (default)
MCP_TRANSPORT=streamable-http uv run az211-mcp  # HTTP
```

### Tests

```bash
cd mcp/211-az-mcp
uv run pytest
```

All tests are offline — no `AZ211_BACKEND_URL` required.

- `tests/test_dispatch_chain.py` — verifies the mock-dispatch
  `dispatch_id` is stable and retrievable in a chained call, and
  that records carry `source: "mock"`.
- `tests/test_referrals.py` — postal-code → county routing, `kind`
  filter on utility assistance, `topic` filter on crisis referrals,
  `urgency` → radius on cooling-center lookup.
- `tests/test_languages.py` — direct English + Spanish operator
  coverage, interpreter-service entry, and the indigenous-language
  partner pathways (Navajo / Diné, O'odham, Apache, Hopi).

## Cross-references

- [`plan/02-mcp-integration.md`](../../plan/02-mcp-integration.html)
  — server inventory and the multi-MCP cooling-center join.
- [`plan/04-data-flows.md`](../../plan/04-data-flows.html), Scenario
  C — the unsheltered heat check-in this server is designed to
  power, end-to-end.
- [`heat/resources.md`](../../heat/resources.md) — 211 Arizona's
  heat-relief services in context.
- [`heat/04-vulnerable-populations.md`](../../heat/04-vulnerable-populations.html)
  — why a voice / no-smartphone channel matters for the highest-
  burden cohort.
- [`notes/world-cafe/q4-heat.md`](../../notes/world-cafe/q4-heat.html)
  — the "anonymity matters" insight from the Unhoused card that
  informs the dispatch flow's PII-minimisation.

## License

MIT, alongside the rest of `epihack-2026`.
