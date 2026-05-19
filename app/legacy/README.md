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
  index.html               landing page with the four flow cards + install button + sync pill
  manifest.webmanifest     Web App Manifest (PWA name, icons, shortcuts)
  sw.js                    Service worker (scope /app/, three caching strategies)
  icons/
    icon.svg               icon source (gradient + white "S" + heat-vertical accent)
    icon-192.png           manifest icon
    icon-512.png           manifest icon (also serves as maskable)
  tick/
    index.html             Scenario-A tick mail-in flow
    tick.js                ES module — wires geo, photo, IDB enqueue on offline
    tick.css               flow-specific styles
  heat/
    index.html             Heat-vertical landing
    heat.css               heat-themed components
    heat-shared.js         vulnerability score + center-list helpers
    mock-responses.json    canned heat-vertical agent-chain responses
    check-in/index.html    CHW heat check-in flow (Scenario C)
    check-in/check-in.js
    self-report/index.html anonymous heat self-report
    self-report/self-report.js
    cool-off/index.html    "where can I cool off?" lookup
    cool-off/cool-off.js
  shared/
    style.css              base styles (palette, header, cards, buttons, offline pill)
    intake-client.js       POSTs to /api/intake, handles SW 202 queued response
    sync.js                IndexedDB queue: enqueueReport / replayAll / subscribe
    install-prompt.js      beforeinstallprompt → Install button helper
    sw-register.js         registers /app/sw.js + mounts the sync-status pill
    geo.js                 navigator.geolocation Promise wrapper + ZIP fallback
    i18n.js                EN / ES bundle + <html lang> + switcher
  mock-responses.json      canned IntakeAgent → … → NotificationAgent results (VBD)
  README.md                (this file)
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

## Offline + sync-on-reconnect (Phase 2)

The app is an installable PWA. The four primary flows
(tick mail-in, heat CHW check-in, heat self-report, cooling-center
lookup) keep working with no network.

### Files involved

```
app/
  manifest.webmanifest      Web App Manifest (name, icons, shortcuts)
  sw.js                     Service worker, scoped to /app/ only
  icons/
    icon.svg                Source icon (gradient + white "S" + heat dot)
    icon-192.png            Manifest icon (192x192)
    icon-512.png            Manifest icon (512x512, also used as maskable)
  shared/
    sync.js                 IndexedDB queue: enqueueReport, pendingReports,
                            replayAll, subscribe
    install-prompt.js       beforeinstallprompt handler + Install button
    sw-register.js          Registers the SW, mounts the sync-status pill
                            ("synced" / "N pending" / "offline") and the
                            "report synced" toast
```

### Caching strategies (service worker)

1. **App shell (HTML / CSS / JS / icons under `/app/`):** cache-first
   with a stale-while-revalidate background refresh. Pre-cached on
   `install`. The shell opens instantly offline; the next online
   navigation refreshes it transparently for the visit after.
2. **Mock-response fixtures + canned cooling-center data**
   (`*/mock-responses.json`): stale-while-revalidate. Pre-populated on
   `install` so the cooling-center lookup works on first launch even
   without a network handshake.
3. **`POST /api/intake`:** network-first. If the request errors or the
   browser is offline, the SW returns a synthetic `202 Accepted` with
   `{ "queued": true }`. The page picks that up and routes the report
   through `shared/sync.js` (IndexedDB), then shows the "Saved offline"
   card. The same path is taken when the page detects
   `navigator.onLine === false` before the fetch even runs.

The scope is `/app/` (not site-wide) so the SW cannot touch the rest of
the static Jekyll site (`map/`, `graph/`, `plan/`, `wildlife/`, the root
`index.html`). That matches the "static-site content shouldn't be
cached aggressively" guardrail in `plan/05-roadmap.md`.

### IndexedDB schema

Database `az-onehealth-sentinel`, object store `pending_reports`:

| field         | type      | notes                                        |
|---|---|---|
| `id`          | UUIDv4    | primary key, generated by `crypto.randomUUID` |
| `enqueued_at` | ISO-8601  | FIFO replay order; indexed                   |
| `flow`        | string    | `tick_mailin`, `heat_chw_checkin`, `heat_self_report` |
| `vertical`    | string    | `vbd` or `heat`                              |
| `mock_key`    | string?   | optional mock-response selector              |
| `api_base`    | string?   | captured at enqueue time; `null` => mock mode |
| `payload`     | object    | Minimum-Dataset shaped JSON                  |
| `retries`     | integer   | bumped on each failed replay, capped at 5    |
| `last_error`  | string?   | last failure reason, for debugging           |

### Background Sync — and the iOS fallback

On Chromium-based browsers (Chrome, Edge, Brave, Samsung Internet),
the page calls `ServiceWorkerRegistration.sync.register('az-sentinel-intake-replay')`
when it enqueues a report. The browser fires that sync the next time
connectivity returns — even with no tab open — and the service worker
replays everything from IndexedDB by itself (see `swDirectReplay()`
in `app/sw.js`).

**iOS Safari does not implement the Background Sync API** (still true
as of 2026). On Safari and Firefox the offline path degrades like this:

* The IDB enqueue still happens — no data loss.
* The sync-status pill shows `N pending` and becomes clickable.
* Replay runs when:
  1. The page is open and the `online` event fires
     (`window.addEventListener('online', replayAll)`), or
  2. The user taps the pending pill to retry manually, or
  3. The user reopens the app — the `load` handler kicks off
     `replayAll()` if `navigator.onLine` is true.

In other words: on iOS, the user has to open the app at least once
after coming back online for queued reports to upload, but they will
still upload reliably. The "report synced" toast and the
`sentinel:synced` event fire in either path.

A future improvement (tracked informally) is a Periodic Background
Sync fallback where supported, and/or a Web Push trigger that wakes
the SW. Both require backend cooperation and so are out of scope for
the prototype.

### Verification

```sh
python -m http.server 8000
# open http://localhost:8000/app/ in Chrome
# DevTools → Application → Service Workers (confirm registered)
# DevTools → Network → Offline
# navigate to /app/tick/, fill the form, submit
#   → "Saved offline" card appears
#   → header pill flips to "1 pending"
# DevTools → Network → Online
#   → pill flips to "syncing…" then "synced"
#   → "tick mailin synced" toast appears
```

