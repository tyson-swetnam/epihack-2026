---
title: "Plan 08 — Mobile UX revamp (port the Elbaraaa/OneHealth design)"
---

# 08 — Mobile UX revamp

Adopt the polished mobile UX from the reference app
[`Elbaraaa/OneHealth`](https://github.com/Elbaraaa/OneHealth) as the new
look-and-feel + screen flow for `app/`, **without changing the backend**:
the DuckDB/DuckLake knowledge graph, the eight-agent orchestrator, the
eleven MCP servers, the `api/openapi.yaml` contract, the privacy contract,
and Supabase auth all stay exactly as they are. Only the Next.js front end
changes.

## Decisions (locked)

| Fork | Decision |
|---|---|
| Visual design | **Adopt Tailwind** 3.4 + the reference's teal design tokens, `AppShell`, and utility classes. |
| Framework baseline | **Upgrade `app/` to Next.js 16 / React 19** (matches the reference). Static export + `basePath` must be preserved — this is a gated step (Phase 0). |
| Result screen | **Reuse the polished result-card layout, but bind it to the server's `TriageOutcome.next_action`** routing. No client-side risk scoring (the reference's `riskScoring.ts` is rejected — see Guardrails). |

## Guardrails — what must NOT change

1. **`api/openapi.yaml` stays the source of truth.** Any new field the
   polished forms collect (e.g. `symptomStartDate`, `recentTravel`,
   `ongoingConcern`) is added to the spec first, then `npm run gen:api`
   regenerates `api-types.ts`, then `agents/.../api/models.py` is
   re-validated. Never hand-edit `api-types.ts`.
2. **The submit path stays `POST /v1/reports` → FastAPI → DuckLake.** The
   UI keeps calling `createReport()` (`app/src/lib/api-client.ts`). The
   intake write-path (`agents/.../kg_writer.py`) and MCP-backed agents are
   untouched.
3. **Privacy contract is load-bearing** (CONTRIBUTING.md checklist):
   - Location stays coarse — keep `coarse-geo.ts` (1 km grid / ZIP). Do
     **not** adopt the reference's raw-ZIP-only handling without the
     coarsen step; keep our GPS→1 km path too.
   - Keep `exif-stripper.ts` on photo upload (the reference only sets a
     `photoAttached` flag and never strips/uploads).
   - **Triage is routing, not diagnosis.** The reference computes a 0–100
     "risk score" + "High/Elevated" group client-side — that is a verdict
     and is forbidden. The result screen renders only `next_action`
     (+ optional `copy` / cited `sources`) returned by the server. The
     server's regex output-guard already rejects `you have…`/`diagnos*`.
   - Cluster/dashboard views use ZCTA-week aggregations from `/v1/context`,
     never individual observations.
4. **Static export + `basePath: '/epihack-2026/app'`** must keep working
   (gh-pages `deploy-app.yml`, the VM nginx vhost, and the Ansible `app`
   role all build `out/`). This is the upgrade's main risk.
5. **Anonymous-first.** Auth stays optional (`isAuthConfigured()`); the
   whole report flow works signed-out.

## Reference inventory → adopt / adapt / reject

| Reference asset | Disposition |
|---|---|
| `tailwind.config.ts` tokens (ink, public-teal, public-blue, soft-mint/sky, `soft` shadow) | **Adopt** — becomes our design system. |
| `app/globals.css` utilities (`.app-button`, `.choice-row`, `.phone-page/.phone-screen`, `.progress-track`, `.focus-ring`) | **Adopt** (merge into our `globals.css`). |
| `components/AppShell.tsx` + `AppTopBar` (390 px phone frame, back/title/user) | **Adopt** — replaces our ad-hoc `header`/`main` shell. Add our `AuthBadge` into the top bar. |
| `components/DomainSelection.tsx` (feeling good/sick + domain toggles) | **Adapt** — map to our `report_type` (human/animal/environmental); keep our anonymity defaults. |
| `components/ReportForm.tsx` (per-domain fields, progress bar, photo) | **Adapt heavily** — keep the layout/progress UX, swap field sets to our `event_class` taxonomy + `coarse-geo`/`exif` steps; submit via `createReport()` not localStorage. |
| `components/ProfileForm.tsx` | **Adapt** — keep UI, wire to `attachProfile()` PATCH `/v1/reports/{id}/profile`. |
| `components/RiskResultCard.tsx` + `MitigationDetails.tsx` (gauge + advice) | **Adapt** — reuse layout; bind gauge to `next_action`/`urgency`, render `copy` + `sources`. **Drop the score.** |
| `components/DashboardSummary.tsx`, `RecentReportsTable.tsx` | **Adapt (Phase 6, optional)** — feed from `/v1/context` ZCTA aggregations, not raw reports. |
| `components/QuestionRenderer.tsx` (generic input mapper) | **Adopt** — useful to drive forms from an event-class schema. |
| `lib/riskScoring.ts`, `lib/mockData.ts` localStorage scoring | **Reject** — replaced by server triage + our mock fixtures. |
| `lib/types.ts` report shapes | **Reject as-is** — our `ReportPayload`/`api-types.ts` is the contract; map onto it. |

## Data-model mapping (reference → our contract)

| Reference field | Our `ReportPayload` / handling |
|---|---|
| `domain` human/animal/environment | `report_type` human/animal/**environmental** |
| human `symptoms[]` | `symptoms: SymptomCategory[]` + choose `event_class` (e.g. `human.fever_chills`) |
| `symptomStartDate` | `event_date` (or new spec field — add to openapi first) |
| animal `animalType`, `symptomsBehavior[]` | `event_class` (`animal.*`) + `species` + `symptoms`/`notes` |
| `animalCount` / `multipleAnimalsAffected` | `count` |
| environment `concernTypes[]` | `event_class` (`env.*`) |
| `ongoingConcern`, `recentTravel`, `recentAnimalContact` | **new optional spec fields** (add to openapi, regen, validate) or fold into `notes` for v1 |
| `zipCode` (raw) | `coarse_location.zip` via `normaliseZip()`; keep GPS→`grid_id` path |
| `photoAttached` (flag only) | real photo → `stripExif()` → multipart `photo` blob |
| client `riskScore`/`group` | **server** `TriageOutcome.next_action` (+ `urgency`, `copy`, `sources`) |

## Phased work plan

### Phase 0 — Framework upgrade + Tailwind (gated)
- Bump `app/package.json`: `next@^16`, `react@^19`, `react-dom@^19`,
  `eslint-config-next@^16` (and re-pin `eslint` to whatever 16 needs).
  Add `tailwindcss@^3.4`, `postcss`, `autoprefixer`, `lucide-react`,
  Inter via `next/font`.
- Add `tailwind.config.ts` (port tokens) + `postcss.config.mjs`; add the
  Tailwind directives to `globals.css` while keeping existing CSS vars
  during migration.
- **Verify static export survives** before touching screens:
  `NEXT_PUBLIC_API_BASE=mock npm run build` must still emit `out/` with
  `basePath` intact; `npm run typecheck` clean. Confirm `next.config`
  `output:'export'`, `trailingSlash`, `images.unoptimized` still honored
  on 16. **Gate: do not proceed until `out/` builds.**
- Update `app/src/lib/supabase` + `openapi-fetch`/`openapi-typescript`
  versions for React 19 compatibility; smoke `npm run gen:api`.

### Phase 1 — Design system
- Land `tailwind.config.ts` tokens, merge reference `globals.css`
  utilities, wire Inter font, add lucide icons.
- Port `AppShell` + `AppTopBar` as our new `layout.tsx` shell; mount
  `AuthProvider` + `AuthBadge` inside the top bar. Respect `basePath` via
  `next/link` (no hardcoded `/`).

### Phase 2 — Screen flow
- Rebuild routes to the reference's flow, keeping our route names where
  the API/auth depend on them:
  `/` welcome → `/report` domain-select → `/report/[type]` form →
  `/profile` (optional) → `/result` (was inline "done") → `/dashboard`
  (optional). Keep `/sign-in`, `/account`, `/auth/callback` as-is.
- Port `DomainSelection` and the `ReportForm` progress-wizard, but render
  **our** steps: Photo (EXIF) → Class (event_class grid) → Where
  (coarse-geo) → Consent → Submitting → Result.

### Phase 3 — Backend wiring (keep DuckLake + MCP)
- Submission calls `createReport(payload, photo)` → `POST /v1/reports`
  (already flows to DuckLake via `kg_writer.py`). Keep mock mode.
- **Channel split (see `plan/09-mobile-datastore.md`):** the mobile build sends
  `X-Client-Channel: mobile` and FastAPI persists it to MongoDB (then syncs to
  DuckLake); the web build stays DuckLake-direct. Privacy enforcement is shared
  and runs before either sink.
- Result screen: poll `getReportStatus(id, claim_token)` →
  render `next_action` gauge + `copy` + `sources`. No score.
- Profile: `attachProfile()` PATCH with `claim_token`.
- Dashboard (optional): `getContext()` ZCTA aggregations only.

### Phase 4 — Privacy re-integration & governance
- Re-wire `coarse-geo.ts` + `exif-stripper.ts` into the new form steps;
  keep the consent checklist gate before submit.
- Walk the CONTRIBUTING.md privacy checklist; confirm no raw lat/lon, no
  diagnosis copy, EXIF stripped, claim-token status reads.

### Phase 5 — Deploy reconciliation + verify
- Confirm the Ansible `app` role still builds Next 16 (`npm install` +
  `gen:api` + `next build` → `out/`); it already handles missing
  lockfiles and `--legacy-peer-deps` fallbacks.
- Confirm `deploy-app.yml` (gh-pages) and the nginx vhost serve the new
  `out/`. Run the full localhost playbook and re-check `http://<host>/`.

### Phase 6 — Optional polish
- Local dashboard from `/v1/context`; offline submit queue keyed by
  `claim_token`; QuestionRenderer-driven event-class schema.

## Risks & mitigations

- **Next 16 breaks static export / basePath** → Phase 0 gate; if it
  regresses, fall back to Next 14 + port design only (design is
  framework-agnostic). Keep the upgrade on a branch.
- **React 19 peer-dep churn** (Supabase SSR, openapi-fetch) → bump
  together; `--legacy-peer-deps` already tolerated by the `app` role.
- **Governance regression** (score creeps back in) → result screen reads
  only `next_action`; add a test asserting no `diagnos*`/score copy.
- **New form fields outrun the spec** → spec-first rule; fold extras into
  `notes` until added to `openapi.yaml`.

## Acceptance checklist

- [ ] `npm run build` emits `out/` with `basePath` on Next 16; `typecheck` clean.
- [ ] New UX matches the reference (AppShell frame, teal system, wizard, gauge).
- [ ] A report POSTs to `/v1/reports`, lands in DuckLake (new snapshot), and the result screen shows server `next_action` only.
- [ ] EXIF stripped + location coarse; consent gate present; anonymous path works.
- [ ] Supabase sign-in still optional and functional.
- [ ] gh-pages + nginx + Ansible `app` role all serve the new build.
- [ ] CONTRIBUTING.md privacy checklist walked in the PR.
