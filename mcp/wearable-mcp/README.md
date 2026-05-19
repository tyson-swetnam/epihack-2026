---
title: Wearable MCP server
---

# `wearable-mcp` — Model Context Protocol server for wearable readings

A [Model Context Protocol](https://modelcontextprotocol.io/) server that
exposes user-consented wearable readings (heart rate, skin temperature,
HRV SDNN, 24-hour step count, body temperature) to LLM clients (Claude
Desktop, Claude Code, the Sentinel Triage Agent, etc.).

Built for the EpiHack Arizona 2026 **Heat focus group** as part of
Phase 4 of the [roadmap](../../plan/05-roadmap.html#phase-4--statewide--evaluation-month-912).

## Privacy stance (read this first)

This MCP server **never** talks to Apple HealthKit or Android Health
Connect directly. Those data sources require on-device user consent
and stay on the user's device. Instead, the server is a *consumer* of
the on-device store that [`app/shared/wearable.js`](../../app/shared/wearable.js)
populates after the user grants permission through the
`webkit.messageHandlers.health` bridge (iOS) or
`navigator.healthConnect` (Android). The MCP-side picture is therefore
read-only and downstream of consent.

Until that on-device store exists (it's a Phase-4 ship), the server
runs **mock-by-default**: every tool returns canned readings drawn
from `wearable_mcp.mock_data` so the demo + tests work without a real
device. Set `WEARABLE_BACKEND_URL` to point at a real consented-store
proxy when one is available.

## What it does

| MCP tool | Returns |
|---|---|
| `wearable_recent_readings` | List of normalised readings for one LOINC code since a given ISO timestamp. |
| `wearable_summary_24h`     | min / max / mean / count for the last 24 h. |
| `wearable_alert_check`     | Which of a small rules-spec fire on the current data (tachycardia, etc.). |
| `wearable_supported_metrics` | The LOINC codes this build supports, plus human-readable name + unit. |

Plus two MCP **resources**:

* `wearable://loinc-codes` — text reference matching the LOINC entries
  in `schema/deep/followups.sql`.
* `wearable://privacy-stance` — the explicit text version of the
  paragraph above.

## Supported metrics (LOINC)

| LOINC | Name | Unit |
|---|---|---|
| `8867-4`  | Heart rate                 | bpm   |
| `8310-5`  | Body temperature           | degC  |
| `8328-7`  | Skin temperature           | degC  |
| `80404-7` | Heart rate variability SDNN | ms    |
| `41950-7` | Steps in 24h               | steps |

## Why this matters for EpiHack

When the Triage Agent is reasoning about a heat self-report it can
ask, in plain language, "is this user currently meeting a tachycardia
threshold?" and get a structured deterministic answer from
`wearable_alert_check`, without ever touching the user's raw stream
or leaving the consent boundary the wearable shim already established.

## Run

```bash
uv run --from . wearable-mcp
```
