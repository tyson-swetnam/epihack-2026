---
title: AZ One Health Sentinel — reporting app (Next.js)
---

# `app/` — AZ One Health Sentinel reporting app

The mobile-first reporting app from
[`plan/06-mobile-app.md`](../plan/06-mobile-app.html). Next.js +
TypeScript + React. Static-exported for the GitHub Pages pilot;
the same build wraps with Capacitor for iOS / Android (plan/06
Delivery sequence).

> **The Phase-0 vanilla prototype** (tick mail-in, heat check-in,
> heat self-report, cooling-center lookup) is preserved unchanged
> under [`legacy/`](./legacy/) until each flow is ported into
> the React app. Existing URLs continue to work via the static
> archive.

## What's here

```
app/
  package.json              Next.js 14 + React 18 + TypeScript + openapi-typescript
  next.config.mjs           output: 'export'; basePath = /epihack-2026/app
  tsconfig.json             strict + noUncheckedIndexedAccess
  src/
    app/
      layout.tsx            Root layout (palette, viewport, theme-color)
      page.tsx              Landing — three-button picker (Person / Animal / Environment)
      report/
        [type]/page.tsx     The multi-step report flow (one route per report type)
      profile/
        page.tsx            Optional post-submit profile interstitial
      globals.css           Base styles
    lib/
      api-client.ts         Typed fetch wrapper around /v1/reports etc.
      api-types.ts          GENERATED — run `npm run gen:api` to refresh
      exif-stripper.ts      Client-side EXIF GPS strip (port of legacy/shared/exif-stripper.js)
      coarse-geo.ts         GPS → 1 km grid / ZIP coarsening (port of legacy/shared/coarse-geo.js)
    mocks/
      reports.create.json   Canned response for POST /v1/reports
      context.zip.json      Canned response for GET /v1/context?zip=…
  legacy/                  Vanilla-HTML Phase-0/1 prototype (read-only archive)
```

## Quick start

```bash
cd app
cp .env.example .env.local      # fill in Supabase URL + anon key if you want auth
npm install
npm run gen:api                 # generate TS types from ../api/openapi.yaml
npm run dev                     # localhost:3000
```

The dev server defaults to `NEXT_PUBLIC_API_BASE=mock`, which makes
the API client short-circuit to `src/mocks/*.json` so the app runs
without a backend. Point at a real Intake Agent with:

```bash
NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run dev
```

And to run the FastAPI backend locally:

```bash
cd agents
uv sync
ONEHEALTH_AUTH_MOCK=1 uv run uvicorn onehealth_agents.api:app --reload --port 8000
```

Sign-in is gated by `NEXT_PUBLIC_SUPABASE_URL` and
`NEXT_PUBLIC_SUPABASE_ANON_KEY`. When unset, the auth UI renders in
"configure-me" mode and anonymous reporting still works end-to-end.
See [`plan/07-auth.md`](../plan/07-auth.html) for the architecture.

## Production build

```bash
npm run build            # writes out/ as static HTML/JS/CSS
```

The `out/` directory is what GitHub Pages serves at
`https://tyson-swetnam.github.io/epihack-2026/app/`. The build is
wired into `.github/workflows/deploy-app.yml` (Phase 06.1 deliverable).

## Stack rationale

- **Next.js + React + TypeScript.** React for component reuse with
  the future native shell (Capacitor → React Native if needed);
  Next.js for routing, file conventions, and static export; TS
  for the strict types we get from the OpenAPI spec.
- **`output: 'export'`.** GitHub Pages has no server runtime; static
  export sidesteps that. We lose Next.js features that need a server
  (API routes, ISR, middleware) but we don't need any of them — the
  backend lives in [`/agents/`](../agents/) and is reached via the
  OpenAPI spec at [`/api/openapi.yaml`](../api/openapi.yaml).
- **`openapi-typescript` + `openapi-fetch`.** The spec is the source
  of truth. `npm run gen:api` regenerates `src/lib/api-types.ts`
  from the YAML; the fetcher is typed against those types, so every
  endpoint call is checked at compile time.

## Privacy contract (load-bearing)

These are the rules from
[`plan/06-mobile-app.md`](../plan/06-mobile-app.html) that the
client must enforce. See `src/lib/exif-stripper.ts` and
`src/lib/coarse-geo.ts` for the implementations:

1. Photo EXIF GPS is stripped **before** any photo leaves the device.
2. Precise lat/lon is coarsened to a 1 km grid cell (or ZIP) before
   the body is built.
3. Every consent toggle on the profile page defaults to **off**.
4. The Triage Agent's `next_action` enum is the only authority on
   what action UI the app renders. Server-side LLM copy is read-
   only context; the app must not render a diagnosis even if one
   slips through the server's output guard.

## Migration plan (Phase 0/1 → React)

Each legacy flow gets ported in its own commit:

| Legacy URL | New React route | Status |
|---|---|---|
| `app/legacy/tick/` | `app/src/app/tick/page.tsx` | TODO |
| `app/legacy/heat/check-in/` | `app/src/app/heat/check-in/page.tsx` | TODO |
| `app/legacy/heat/self-report/` | `app/src/app/heat/self-report/page.tsx` | TODO |
| `app/legacy/heat/cool-off/` | `app/src/app/heat/cool-off/page.tsx` | TODO |

Until each port lands, the legacy HTML stays addressable at
`/epihack-2026/app/legacy/<flow>/` and the new landing page in
`src/app/page.tsx` links to it.
