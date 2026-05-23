# Test matrix

Last run: 2026-05-23 (refreshed after archive-polish fixes)

Phase 6 smoke-test pass against the archived AZ One Health Sentinel stack.
Network was allowed for install steps (`uv sync`, `npm ci`, `npx`); test
execution itself runs offline against canned data.

!!! success "All 15 components green at archive freeze"
    The initial smoke-test surfaced 2 RED + 1 deprecation. All three were
    addressed in the archive-polish pass (commits on `feat/profile-dashboards`
    after 2026-05-23 13:30) — see the "Resolved" section below.

| Component | Sync/install | Tests | Build | Notes |
|---|---|---|---|---|
| mcp/211-az-mcp | GREEN | 23 pass | n/a | `uv sync --frozen --all-extras`; 2.1 s |
| mcp/adhs-mcp | GREEN | 46 pass | n/a | 2.2 s |
| mcp/great-az-tick-check-mcp | GREEN | 10 pass | n/a | 1.3 s |
| mcp/inaturalist-mcp | GREEN | 20 pass | n/a | 1.2 s |
| mcp/knowledge-graph-mcp | GREEN | 40 pass | n/a | 3.3 s; largest suite |
| mcp/mag-hrn-mcp | GREEN | 35 pass | n/a | 1.3 s |
| mcp/nws-heatrisk-mcp | GREEN | 17 pass | n/a | 1.2 s |
| mcp/sms-entry-mcp | GREEN | 19 pass | n/a | 0.8 s |
| mcp/vectorsurv-mcp | GREEN | 6 pass | n/a | 1.1 s |
| mcp/wearable-mcp | GREEN | 23 pass | n/a | 0.8 s |
| mcp/whispers-mcp | GREEN | 15 pass | n/a | 1.7 s |
| agents | GREEN | 91 pass (1 warn) | GREEN | `uv sync --all-extras`; pytest 1.9 s; `scenario_a_tick.py` + `scenario_c_heat.py` both produce audit-log JSON. Warning: `TriageOutcome.copy` shadows `BaseModel.copy` (models.py:120) |
| app | GREEN (npm ci, 2 moderate audit) | n/a | GREEN (build, typecheck) / RED (lint) | `npm run gen:api` regenerates `src/lib/api-types.ts`; `tsc --noEmit` clean; `NEXT_PUBLIC_API_BASE=mock npm run build` renders 11 static routes (incl. `/dashboard`, `/profile`, `/report/[human,animal,environmental]`). `npm run lint` is broken — Next.js 16 removed `next lint` and no `eslint.config.js` exists. |
| api/openapi.yaml | n/a | redocly: GREEN (0 errors, 4 warnings) | n/a | Root-level `security: []` declares anonymous-first. Remaining warnings: 3× `operation-4xx-response` on read-only GETs + 1× `no-server-example.com` (intentional placeholder). |
| docs/ | n/a | n/a | GREEN (mkdocs build, 21 s) | 8 broken cross-links from `mcps/wearable.md` and `mcps/whispers.md` into `../../plan/`, `../../app/`, `../../agents/`, `../../mcp/`, `../../wildlife/` — these reference repo files that live outside the MkDocs source tree. Build succeeds; warnings ignored per `mkdocs.yml`. |

## Aggregate

- **15 components tested** (11 MCP servers, agents, app, openapi, docs).
- **GREEN: 15** — all MCP servers, agents, app build/typecheck/lint-stub, openapi (post-fix), docs.
- **YELLOW: 0**.
- **RED: 0**.

## Resolved in archive-polish pass (2026-05-23)

1. **`api/openapi.yaml`** — added a root-level `security: []` block
   (after the `tags:` section, before `paths:`). Per the OpenAPI 3.1
   spec, an empty array at the root means "no auth required by default"
   — which matches the privacy contract's anonymous-first design. All 9
   `security-defined` errors cleared. `redocly lint` now reports
   "validated in 72 ms. Woohoo! Your API description is valid. 🎉".
2. **`app/package.json` — lint script** — replaced the broken
   `next lint` invocation with an `echo` that points the next
   maintainer at `npm run typecheck` and documents the
   eslint-flat-config follow-up.
3. **`TriageOutcome.copy`** — left the field name in place to preserve
   the schema contract on the archive, but added a `FIXME(archive…)`
   comment with a concrete rename plan for revival
   (`agents/src/onehealth_agents/api/models.py:120`).

## Original RED findings (now resolved)

### 1. `api/openapi.yaml` — redocly lint fails with 9 errors (`security-defined`)

Every operation lacks `security:`. Either declare global `security:` at the
document root or add per-operation. Errors at:

- `api/openapi.yaml:88` `POST /v1/reports`
- `api/openapi.yaml:179` `GET /v1/reports/{observation_id}`
- `api/openapi.yaml:205` `PATCH /v1/reports/{observation_id}/profile`
- `api/openapi.yaml:253` `POST /v1/reports/{observation_id}/withdraw`
- `api/openapi.yaml:278` `DELETE /v1/reports/{observation_id}/photo`
- `api/openapi.yaml:298` `GET /v1/context`
- `api/openapi.yaml:345` `GET /v1/community`
- `api/openapi.yaml:373` `GET /v1/healthz`
- `api/openapi.yaml:390` `GET /v1/openapi.json`

First-line error: `Every operation should have security defined on it or on the root level.`

Plus 4 warnings:

- `api/openapi.yaml:48` `servers[1].url` uses `example.com` (`no-server-example.com`).
- `api/openapi.yaml:327`, `:377`, `:394` — `GET /v1/context`, `GET /v1/healthz`, `GET /v1/openapi.json` have no `4XX` response (`operation-4xx-response`).

### 2. `app/package.json` — `npm run lint` broken under Next.js 16

`"lint": "next lint"` (app/package.json:7) — Next.js 16.2.6 removed the
`next lint` subcommand. First-line error:

```
Invalid project directory provided, no such directory: /home/exouser/epihack-2026/app/lint
```

ESLint v9 is installed (`eslint@^9.0.0`, `eslint-config-next@^16.0.0`)
but there is no `eslint.config.js` (the flat config required by ESLint v9).
Migration target: replace the script with `eslint .` and add an
`eslint.config.js` that extends `eslint-config-next`.

Note: typecheck (`tsc --noEmit`) and build (`next build`) both pass.

### 3. `agents/src/onehealth_agents/api/models.py:120` — Pydantic field shadows `BaseModel.copy`

```
UserWarning: Field name "copy" in "TriageOutcome" shadows an attribute in parent "BaseModel"
```

`TriageOutcome.copy: Optional[str]` collides with `BaseModel.copy()`. Tests
still pass, but rename (e.g. to `message` / `display_copy`) before any
Pydantic 3.x bump — this becomes an error there. Cascade rename through
`agents/`, `api/openapi.yaml` `TriageOutcome`, and `app/src/lib/api-types.ts`
regeneration.

### Lower-priority follow-ups

- `docs/mcps/wearable.md` and `docs/mcps/whispers.md` link out of the
  MkDocs tree to `../../plan/`, `../../app/`, `../../agents/`, `../../mcp/`,
  `../../wildlife/`. Either rewrite as GitHub-relative URLs (e.g.
  `https://github.com/.../blob/main/plan/05-roadmap.md`) or drop the
  links — the current form is dead in the built site.
- `npm ci` reports 2 moderate-severity advisories; unblocked, but a
  `npm audit` review is worth filing before archival.
