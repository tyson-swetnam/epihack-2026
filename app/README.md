---
title: AZ One Health Sentinel — prototype app
---

# `app/` — AZ One Health Sentinel prototype

This is the **Phase 0 hackathon-MVP UI** for the
[AZ One Health Sentinel](../plan/README.html). One vertical
(Vector-Borne Disease), one happy path (mail-in tick), wired end-to-end
through a mock backend so the demo runs on GitHub Pages with no server.

See [`plan/05-roadmap.md` Phase 0](../plan/05-roadmap.html#phase-0--hackathon-mvp-week-02)
and [`plan/04-data-flows.md` Scenario A](../plan/04-data-flows.html#scenario-a--hiker-mails-in-a-tick)
for what this UI implements.

## Stack choice

The rest of the site is **static HTML + Jekyll on GitHub Pages**. To stay
consistent with [`map/`](../map/), [`graph/`](../graph/), and the root
[`index.html`](../index.html), this app is a **static, no-build
prototype**: plain HTML, modern vanilla JS (ES modules), one shared CSS
file. No bundler, no framework, no CSS toolkit.

That keeps it `git clone` → `python -m http.server` → done, and it lets
GitHub Pages serve it byte-for-byte.

## Layout

```
app/
  index.html            landing page with two cards (Submit a tick, Heat check-in stub)
  tick/
    index.html          Scenario-A tick mail-in flow (multi-step single page)
    tick.js             ES module that drives the flow
    tick.css            flow-specific styles
  heat/
    index.html          Phase 1 placeholder card
  shared/
    style.css           base styles (palette, header, cards, buttons)
    intake-client.js    POSTs to /api/intake or returns a canned mock response
    geo.js              navigator.geolocation Promise wrapper + ZIP fallback
  mock-responses.json   canned IntakeAgent → … → NotificationAgent results
  README.md             (this file)
```

## Run locally

From the repo root:

```sh
python -m http.server 8000
# then open: http://localhost:8000/app/
```

That's it. No `npm install`, no build step.

## Wire a real backend

The fetch wrapper in
[`shared/intake-client.js`](./shared/intake-client.js) reads
`data-api-base` off `<body>`:

| `data-api-base`                           | Behavior |
|---|---|
| absent, or `"mock"`                       | Returns the canned `mock-responses.json` entry; default for GitHub Pages. |
| an origin, e.g. `https://sentinel.example.org` | `POST {origin}/api/intake` as multipart (`payload` JSON + optional `photo`). |

To point the deployed prototype at a real backend, change one attribute:

```html
<body data-api-base="https://sentinel.example.org">
```

The expected response shape lives in
[`mock-responses.json`](./mock-responses.json) — it mirrors what
the `Intake → Geo-Enrichment → Validation → Triage → Enrichment →
Notification` chain in
[`plan/03-agentic-architecture.md`](../plan/03-agentic-architecture.html)
should produce. Implementing the real backend means matching that shape
(no UI changes needed).

## The tick mail-in flow (in `tick/`)

Six steps on one page, with a progress indicator, sticky Next/Back bar,
44 × 44 px tap targets, and visible focus rings:

1. **Welcome** — what we're about to do, link to the Great Arizona Tick
   Check page. Renders usefully without JS for screen-reader users.
2. **Where + when** — GPS (with ZIP fallback), date attached, hours
   attached, location on body. Covers the General + Exposure slots of
   the [Minimum Dataset](../plan/01-parameter-mapping.html).
3. **Photo** — `<input type="file" accept="image/*" capture="environment">`
   so phones open the back camera directly. Preview + remove.
4. **Optional symptoms** — four checkboxes (fever, headache, rash,
   muscle aches). Skipping is one tap.
5. **Consent** — the `consent.tick_mailin` profile, showing which
   Figure-2 fields are kept vs. suppressed. Explicit accept required.
6. **Submit** — spinner with a per-agent log while the (mock) chain
   runs, then a result card with the species estimate (+ confidence
   caveat), mailing-label download link, 14-day symptom watchlist, and
   "If symptoms appear" link. Cross-links to
   [`graph/`](../graph/) and [`map/`](../map/) so the user can see how
   their report fits the larger picture.

### Stubbed for the real backend to pick up

The hackathon MVP fakes a few things the real pipeline will own. They
are intentionally narrow so they map 1:1 to existing plan items:

- **No backend.** `app/shared/intake-client.js` short-circuits to
  `mock-responses.json`. Replace with the real `IntakeAgent` HTTP entry
  point per the data-api-base contract above.
- **Client-side species ID is faked.** The mock response hard-codes
  *Rhipicephalus sanguineus* at 0.62 confidence. The real flow runs a
  TFLite (or server-side) image model and the Walker Lab supersedes it
  on receipt.
- **Mailing-label URL is a placeholder.** Real flow:
  `great-az-tick-check-mcp.create_submission` returns a signed S3 URL.
- **`vectorsurv-mcp` context is canned.** Real flow:
  `vectorsurv-mcp.get_pools(arthropod="tick", county=…, last 90 days)`
  on submit.
- **No persistent observation.** Real flow writes to DuckLake via
  `knowledge-graph-mcp` and the response carries the new `kg_node_id`.
- **No agent-run audit row.** Real flow appends an `agent_run` row per
  agent in the chain (see Phase 0 in the roadmap), with timestamps the
  Figure 3 milestone joins use.

## Accessibility

- Semantic HTML (`<header>`, `<main>`, `<section>`, `<label>`, headings
  in order).
- `aria-label` on icon-only and ambiguous buttons.
- Visible focus rings via `outline: 3px solid var(--c-focus)`.
- 44 × 44 px minimum tap target on every interactive element.
- `prefers-reduced-motion` respected (transitions / spinner reduced).
- Step 1 (Welcome) renders without JavaScript and links straight to the
  external Tick Check page so a no-JS user is not stranded.

## Palette (matches the rest of the site)

| Token        | Value     | Use |
|---|---|---|
| `--c-navy`   | `#1F3A93` | Primary brand (VBD vertical, links, focus). |
| `--c-red`    | `#C0392B` | Alert / triage urgency. |
| `--c-orange` | `#E84A2B` | Heat vertical. |
| `--c-green`  | `#4CAF50` | Success affirmations. |
