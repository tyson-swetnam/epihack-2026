---
title: AZ One Health Sentinel — Intake API spec
---

# `api/` — Intake API (OpenAPI 3.1)

The HTTP contract between the reporting app ([`/app/`](../app/)) and
the agent orchestrator ([`/agents/`](../agents/)).

[`openapi.yaml`](./openapi.yaml) is the **source of truth** for
endpoint shapes. Schemas, status codes, and validation rules live
there. PRs that change endpoints must edit the spec first; backend
handlers and frontend client are generated or validated against it.

## What's in the spec

| Endpoint | Purpose |
|---|---|
| `POST /v1/reports` | File an anonymous report (multipart, with optional photo). Returns `observation_id` + one-time `claim_token`. |
| `GET /v1/reports/{id}` | Status of a report; requires `Authorization: Claim …`. |
| `PATCH /v1/reports/{id}/profile` | Attach the optional Minimum-Dataset profile after submit. Same claim-token auth. |
| `GET /v1/context` | Public-health signals for a coarse location (ZIP or 1 km cell). Never asserts a diagnosis. |
| `GET /v1/healthz` | Liveness probe. |
| `GET /v1/openapi.json` | Self-describe (the spec itself). |

## Privacy contract

These are the load-bearing rules from
[`plan/06-mobile-app.md`](../plan/06-mobile-app.html) — the spec
encodes them into the API surface:

1. **No login, no PII by default.** The `ReportPayload` schema has
   no name / contact / demographic fields. Those only land via
   `PATCH /v1/reports/{id}/profile`, and every flag on the profile
   defaults to opt-out.
2. **Coarse location only at the API.** `CoarseLocation` accepts
   `zip` or `grid_id` (a 1 km grid cell); precise lat/lon is *not* a
   valid field on the wire. The client coarsens before sending; the
   server re-coarsens before persisting.
3. **EXIF GPS check.** `POST /v1/reports` returns `422` with
   `error.code = photo_exif_gps_present` if the uploaded photo
   carries GPS tags. Clients strip them via
   `app/legacy/shared/exif-stripper.js` (or its TypeScript port in
   the new app); the server check is defence-in-depth.
4. **IP is ephemeral.** The handler hashes the request IP with the
   rotating daily salt and discards the raw address inside the
   request scope. No IP ever lands in DuckLake.
5. **Triage is routing, never diagnosis.** `TriageOutcome.copy` MUST
   NOT contain assertions of disease state; a regex output-guard on
   the server rejects responses that pattern-match `you have …`,
   `you may have …`, `this is …`, or `diagnos*`.
6. **Claim-token auth.** Reports are read back through the
   one-time `claim_token` only. There's no enumerable index.

## Generating clients

### TypeScript (used by `/app/`)

```bash
# From the repo root:
npx openapi-typescript api/openapi.yaml -o app/src/lib/api-types.ts
```

The Next.js app imports types as:

```ts
import type { paths, components } from "@/lib/api-types";
type ReportPayload = components["schemas"]["ReportPayload"];
```

A typed runtime fetcher (`openapi-fetch`) is wired in
[`app/src/lib/api-client.ts`](../app/src/lib/api-client.ts).

### Python (used by `/agents/`)

```bash
# From the repo root:
uvx datamodel-code-generator \
  --input api/openapi.yaml \
  --output agents/src/onehealth_agents/api_models.py \
  --output-model-type pydantic_v2.BaseModel
```

That gives pydantic v2 models the orchestrator can validate
intake requests against before the agent chain runs.

## Mock backend for the static-pages pilot

GitHub Pages has no server, so the Next.js build at
[`/app/`](../app/) is configured with
`NEXT_PUBLIC_API_BASE=mock`, which makes
[`app/src/lib/api-client.ts`](../app/src/lib/api-client.ts) short-
circuit every endpoint to a bundled fixture under
`app/src/mocks/`. The fixtures mirror real responses one-for-one
so the demo runs without any backend.

## Local dev backend

A reference FastAPI implementation that conforms to this spec is
planned at `agents/src/onehealth_agents/api/` (Phase 06.2 in
[`plan/05-roadmap.md`](../plan/05-roadmap.html)). Until then the
spec is normative and the only implementation is the bundled mock.

## Validating changes

```bash
# Install once:
npm install -g @redocly/cli@latest

# Lint the spec on every change:
redocly lint api/openapi.yaml

# Preview the rendered docs:
redocly preview-docs api/openapi.yaml
```

CI runs `redocly lint` on every PR touching `api/openapi.yaml`.

## Cross-links

- [`plan/06-mobile-app.md`](../plan/06-mobile-app.html) — the
  privacy + UX architecture this spec implements.
- [`plan/03-agentic-architecture.md`](../plan/03-agentic-architecture.html) —
  the agent chain that runs behind `POST /v1/reports`.
- [`/app/`](../app/) — the Next.js reporting app that consumes
  this spec.
- [`/agents/`](../agents/) — the orchestrator + agent
  implementations that serve this spec.
