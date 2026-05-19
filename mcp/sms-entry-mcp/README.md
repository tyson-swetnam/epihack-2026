---
title: SMS-entry MCP server
---

# `sms-entry-mcp` — Model Context Protocol server for SMS-only intake

A [Model Context Protocol](https://modelcontextprotocol.io/) server that
runs the **SMS-only entry point** for users without a smartphone: a user
texts `tick` or `heat` to a Twilio short code and the server walks them
through the same Minimum Dataset intake the mobile app drives.

Built for EpiHack Arizona 2026, **Phase 2** of the OneHealth roadmap
([`plan/05-roadmap.md`](../../plan/05-roadmap.md): *"SMS-only flow for
users with no smartphone (Twilio / agency short code)"*).

> **Mock-by-default.** Twilio webhooks require a real Twilio account, so
> the server defaults to an in-memory transcript that callers can drive
> end-to-end with tool calls. Flip `SMS_MODE=twilio` plus
> `SMS_TWILIO_AUTH_TOKEN` in the gateway HTTP service to wire it up to
> a real short code.

## What it does

| MCP tool | Purpose |
|---|---|
| `sms_inbound(from_number, body, message_sid?, lang?)` | Simulate one inbound SMS. Returns the outbound reply + state + (once finished) a `MinimumDataset` dict. |
| `sms_outbound_log(from_number, limit=20)` | Read the last N outbound messages sent to a phone number. |
| `sms_set_consent(from_number, profile)` | Override the consent profile on a phone's session (defaults: `consent.anonymous_heat` for heat, `consent.tick_mailin` for tick). |
| `sms_state(from_number)` | Inspect a phone number's current conversation state + answers + final dataset. |
| `sms_reset(from_number)` | Clear conversation state. |
| `sms_twilio_webhook_signature_verify(body, signature, url, auth_token?)` | Pure-function Twilio HMAC-SHA1 signature check. |

Plus three MCP **resources**:

- `sms://supported-languages` — the language codes the state machine
  answers in (`en`, `es`).
- `sms://state-machine` — a plain-text rendering of every state + every
  transition, so an LLM can answer *"what happens if a user texts X?"*
  introspectively.
- `sms://prompts/{lang}` — every outbound prompt for a given language
  (for translation review).

## The conversation flow

The state machine is single-purpose: walk a user through the tick or
heat minimum-dataset over SMS, then hand the result to the agents
pipeline. Every outbound message is kept under 160 chars so it ships as
a single SMS segment.

```
greet ─────► vertical_select ──┬─ tick_zip ──► tick_attached_date
                               │                       │
                               │                       ▼
                               │              tick_attached_hours
                               │                       │
                               │                       ▼
                               │              tick_bite_location
                               │                       │
                               │                       ▼
                               │                  tick_photo
                               │                       │
                               │                       ▼
                               │                tick_confirm ──► submit
                               │
                               ├─ heat_zip ──► heat_unsheltered
                               │                       │
                               │                       ▼
                               │                   heat_ac
                               │                       │
                               │                       ▼
                               │               heat_symptoms
                               │                       │
                               │                       ▼
                               │               heat_confirm ──► submit
                               │
                               └─ help_menu
```

Universal: `STOP` / `CANCEL` / `ALTO` resets.

When the conversation reaches `submit`, `sms_inbound` returns a
`minimum_dataset` dict that mirrors `onehealth_agents.MinimumDataset`
exactly: `{general, exposure, human, auxiliary, environmental, channel,
vertical, consent_profile}`. The MCP server does **not** call the
agents pipeline itself; that's the gateway HTTP service's job.

## Spanish

The first inbound message decides the language. Triggers like `hola`,
`ayuda`, `salud`, `garrapata`, `calor`, or `español` flip the session
to Spanish (`lang="es"`); explicit `lang="es"` on `sms_inbound` does
the same. Yes/no parsers accept both English and Spanish forms (`yes /
si / sí`, `no / non`). Symptom keyword extraction recognises both
languages (e.g. `mareo` -> `dizziness`, `dolor de cabeza` -> `headache`).

## Real-Twilio wiring

The MCP server stays stateless w.r.t. Twilio. A thin HTTP gateway is
what actually talks to Twilio:

```text
Twilio webhook (POST /sms)
      │
      ▼
gateway HTTP service
  1. sms_twilio_webhook_signature_verify(body, signature, url)
  2. sms_inbound(from_number=From, body=Body, message_sid=MessageSid)
  3. if result.minimum_dataset is not None:
         observation = await Orchestrator.process(result.minimum_dataset)
         # then translate observation.notifications -> outbound SMS via sms_adapter
      ▼
gateway returns TwiML wrapping result.outbound
      ▼
Twilio sends the reply SMS
```

Env vars consumed by the gateway:

```bash
export SMS_MODE=twilio
export SMS_TWILIO_AUTH_TOKEN=your_twilio_auth_token   # from Twilio Console
export SMS_TWILIO_PHONE_NUMBER=+15555550199           # provisioned short code
```

A `.env.example` template is included; copy to `.env` and source it.

The `agents/src/onehealth_agents/sms_adapter.py` helper handles the
final hop: it takes the `MinimumDataset` dict, runs it through
`Orchestrator.process()`, and returns a single ≤160-char outbound SMS
summarising the triage decision + a follow-up link.

## Install &amp; run

### Standalone

```bash
cd mcp/sms-entry-mcp
uv sync
uv run sms-entry-mcp                            # stdio (default)
MCP_TRANSPORT=streamable-http uv run sms-entry-mcp  # HTTP
```

### As a Claude Desktop MCP server

Drop the snippet in
[`examples/claude_desktop_config.json`](./examples/claude_desktop_config.json)
into your Claude Desktop config; replace the path with the absolute
path to this directory and restart Claude Desktop.

### Tests

```bash
cd mcp/sms-entry-mcp
uv run pytest
```

Tests are offline and exercise the four cases listed in
`plan/05-roadmap.md` Phase 2:

- `tests/test_tick_flow.py` — full happy-path tick mail-in over SMS.
- `tests/test_heat_flow.py` — heat triage hand-off carries
  unsheltered + AC + symptoms.
- `tests/test_signature_verify.py` — Twilio HMAC-SHA1 vectors.
- `tests/test_es_flow.py` — Spanish trigger switches the prompts.

## License

MIT, alongside the rest of `epihack-2026`.
