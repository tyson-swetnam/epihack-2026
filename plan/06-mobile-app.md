---
title: "Plan 06 — One Health reporting app: anonymous-first intake"
---

# 06 — One Health reporting app (anonymous-first intake)

A unified reporting surface for community members to submit
**Human**, **Animal**, or **Environmental** events from a phone or
laptop, with **anonymity as the default** and a progressive,
opt-in profile that maps to the Figure&nbsp;2 Minimum Set of Key Data
Parameters once the user is ready.

This extends the Phase&nbsp;0 [`app/`](../app/index.html) prototype (tick
mail-in + heat self-report) into the general intake surface the
[plan/03 agentic architecture](./03-agentic-architecture.html) was
designed for. The pilot is a **mobile-friendly web app on GitHub
Pages**; the full prototype targets the Apple App Store and Google
Play.

## Hard rules

These are load-bearing — every decision below derives from them.

1. **Anonymity is the default for Animal and Environmental reports.**
   Workplace whistleblower scenarios (broken sewage pipes, illegal
   burns, dead livestock) must be submittable with **zero identifying
   information** — no IP capture beyond what's needed to coarsen a
   location, no device fingerprint, no account.
2. **Human reports are anonymous by default** with an explicit
   opt-in path to share contact information with a clinician or
   211 dispatcher. The intake form must work end-to-end without
   that opt-in.
3. **The app NEVER renders a diagnosis** from user-supplied symptoms
   or demographics. It MAY surface read-only public-health context
   (e.g. "WNV is active in your county this week" from
   [`vectorsurv-mcp`](../mcp/vectorsurv-mcp/), or "CDC reports
   elevated influenza activity in HHS Region&nbsp;9" from a future
   CDC MCP) **alongside** a report, but it must never connect the
   user's specific symptoms to a specific disease classification.
   Triage Agent's output is a routing decision (self-care &middot;
   clinician &middot; 211 &middot; agency notifier), not a diagnosis.
4. **Public-share resolution is coarse by construction.** Any
   aggregated map, public dashboard, or third-party export uses
   **ZIP code (≈ 5 km²)** or **1&nbsp;km grid cell**, whichever is
   coarser. Precise lat/lon is only retained in the encrypted
   row-level store and only released to a verified agency on an
   explicit per-report consent token (cf.
   [`schema/deep/application.sql`](../schema/deep/application.sql)
   `consent_profile`).
5. **Photographs are stripped of EXIF GPS** before any photo leaves
   the device for a health provider, agency, or public surface,
   **unless** the user has explicitly opted into location sharing
   on their profile. The strip happens client-side; the server
   never receives the original.

## The three report types

| Type | Default anonymity | Required fields | Optional fields | Vertical |
|---|---|---|---|---|
| **Human** event (illness, heat distress, exposure) | Anonymous | event class (icons) &middot; date &middot; coarse location | symptoms (Figure&nbsp;2 Human class) &middot; contact &middot; demographics | VBD &middot; Heat |
| **Animal** event (sick / dead / unusual wildlife or livestock) | **Fully anonymous** | event class (icons) &middot; date &middot; coarse location &middot; species (or "unknown") | photo &middot; count &middot; behavior notes | VBD |
| **Environmental** event (sewage, burn, standing water, smoke, water-quality) | **Fully anonymous** | event class (icons) &middot; date &middot; coarse location | photo &middot; severity (icon scale) &middot; source notes | Both |

The intake screen is **three large tap-targets** — one per type,
each iconographic and language-independent. No required text input
to file a report.

## UI principles

- **Low / no text.** Icons + photo + tap-targets. Text input is
  optional; voice transcription is on the roadmap. The bar to
  file a report must be lower than the bar to post on social
  media.
- **Photo-first.** Camera capture is one tap from the home
  screen. The dead-animal / sewage-pipe / burned-material use
  cases all start with a photo.
- **Mobile-first viewport.** Designed at 360 × 640. Must work
  one-handed. Must work with the screen reader. Must work in
  bright Arizona sun (high-contrast palette).
- **Multilingual.** EN + ES at pilot. Diné Bizaad and Tohono
  O'odham per [plan/05 Phase 2](./05-roadmap.html#phase-2--tribal-partnerships--offline-month-36).
  All UI strings live in [`app/shared/i18n.js`](../app/shared/i18n.js).
- **Offline-capable.** Reports queue in IndexedDB and sync on
  reconnect — already implemented in
  [`app/shared/sync.js`](../app/shared/sync.js); the new flows
  use the same primitive.
- **No login required to submit.** A profile is created lazily
  after the first submission, and only if the user wants one.

## Privacy architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Client (browser / mobile app)                              │
│                                                              │
│   • Photo capture → EXIF strip (client-side)                │
│   • Browser geolocation OR IP → coarsen to ZIP/km           │
│   • Report payload (no PII unless profile.share = true)     │
└──────────────────────────────┬───────────────────────────────┘
                               │  POST /api/intake
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  Intake Agent (plan/03)                                      │
│                                                              │
│   1. Validate consent_profile (anon | contact | full)        │
│   2. Re-coarsen location server-side (defense in depth)      │
│   3. Verify photo has no GPS tags (reject if present)        │
│   4. Hash IP → coarse_geo_token (one-way, salted, rotated)   │
│   5. Drop IP from the in-flight record                       │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  DuckLake — two zones                                        │
│                                                              │
│   precise.observation     (line-level, agency-only,          │
│                            encrypted at rest, consent-gated) │
│   public.observation      (coarsened to ZIP / km grid,       │
│                            no PII, time-bucketed)            │
└──────────────────────────────────────────────────────────────┘
```

### IP-based location

The browser will share precise GPS only with explicit user
permission. If the user declines, the server may use the request
IP to estimate a region — **but the IP itself is never stored**.
The Intake Agent immediately hashes the IP with a rotating salt
to produce a `coarse_geo_token` (the same IP under the same salt
produces the same token, enabling repeat-reporter de-duplication
without ever retaining a re-identifiable address). The token is
discarded after the salt rotates (daily).

### EXIF stripping

The photo upload widget runs the strip locally before the file
leaves the device:

- iOS / Android picker: a small JS utility (`exif-stripper.js`)
  re-encodes the JPEG without the EXIF block before upload.
- Server-side check: the Intake Agent rejects any photo that
  still carries GPS tags. (Defense in depth — clients can be
  buggy or hostile.)
- Audit trail: every photo has a `media_asset` row in the kg with
  `exif_stripped_at` and `original_had_gps` boolean. The boolean
  is preserved so the validation pipeline can spot pattern
  failures, but the original GPS is never written.

### Profile creation

After the first report submits, a non-blocking interstitial
offers profile creation. The profile follows the Figure&nbsp;2
Minimum Dataset and exposes per-field toggles:

```
[ ] Share my home ZIP code with verified agencies
[ ] Share my home address with verified agencies
[ ] Let agencies contact me about reports I file
[ ] Let agencies contact me about events near me
[ ] Use my photo's GPS metadata when I file animal/environmental reports
[ ] Use my photo's GPS metadata for human-event reports
```

Every toggle defaults to **off**. Each toggle is a
`consent_profile` row scoped to a parameter class (cf.
[`schema/deep/application.sql`](../schema/deep/application.sql)).

## Risk assessment: never diagnose

The Triage Agent's contract is unchanged from
[plan/03](./03-agentic-architecture.html#triage-agent), but the
intake app's UI must respect a stricter copy rule:

| Allowed copy | Forbidden copy |
|---|---|
| "WNV is active in Maricopa County this week — see ADHS surveillance." | "You may have West Nile virus." |
| "Heat advisory in effect through Friday — see NWS HeatRisk." | "Your symptoms suggest heat exhaustion." |
| "Veterinary lab nearby: AZ Veterinary Diagnostic Laboratory." | "This appears to be rabies / hantavirus / plague." |
| "Cooling centers near you (211 Arizona)." | "You are at high risk for heat stroke." |

The Notification Agent reuses
[`mcp/vectorsurv-mcp/`](../mcp/vectorsurv-mcp/),
[`mcp/whispers-mcp/`](../mcp/whispers-mcp/),
[`mcp/nws-heatrisk-mcp/`](../mcp/nws-heatrisk-mcp/),
[`mcp/adhs-mcp/`](../mcp/adhs-mcp/), and a future
`cdc-mcp` to pull contextual public-health signals. The
**enrichment text always names the public source and never asserts a
diagnosis**. A regex-based output guard in the Notification Agent
blocks any LLM-generated phrase that pattern-matches a clinical
assertion ("you have …", "you may have …", "this is …").

## Incentives (open)

The bidirectional team identified user-incentive mechanisms as a
core question for adoption — but the specifics from that session
aren't yet captured in the repo. **This is the largest open
question in this plan.** Candidate mechanisms worth pricing /
testing once we have the workshop list:

- Real-time public-health context returned in-app (already in
  scope — fastest payoff).
- Verified-volunteer badges (with no PII exposed externally).
- ITCA-TEC / county-program partnerships that mail submission
  kits (e.g. [Great&nbsp;AZ Tick Check](https://extension.arizona.edu/programs/great-arizona-tick-check)
  already runs this loop for ticks).
- Civic gamification — county leaderboards by ZIP for
  observation count, lab-confirmation rate, follow-up rate.
- "Heard you — here's what happened" reply-back when a report
  contributes to a verified Detect event.

**Action item.** Capture the workshop incentive list verbatim
(notes, photos of whiteboards, etc.) and price each candidate
against (a) privacy risk, (b) gameability, (c) implementation
cost, and (d) equity impact across the
[`heat/04-vulnerable-populations`](../heat/04-vulnerable-populations.html)
cohorts.

## Admin analytics dashboard

Extends [`dashboard/`](../dashboard/). The dashboard is web-based,
laptop / desktop primary, but every view must remain usable at a
mobile viewport (matching the responsive work already shipped on
[`map/`](../map/index.html) and [`graph/`](../graph/index.html)).

Required panels:

| Panel | Source | Audience |
|---|---|---|
| Reports / day by type (Human / Animal / Environmental) | DuckLake `public.observation` time-bucketed | All |
| Cluster alerts (live, with Tier-A through Tier-E flags) | `agents.cluster` outputs + `schema/deep/cluster_followups.sql` | Agency epi |
| Report → Notify median interval (Figure&nbsp;3) | `schema/deep/audit.sql` timeliness view | Agency leadership |
| Demographic-disparity dashboard (where consented) | `consent_profile`-filtered cohorts | Governance board |
| Photo gallery (EXIF-stripped, agency-only) | `media_asset` rows with `consent_profile.share_photo = true` | Agency epi |
| Repeat-reporter rate (without de-anonymising) | `coarse_geo_token` aggregates | Governance board |
| Source-of-truth audit trail per report | `schema/deep/audit.sql` agent-run log | Privacy auditor |

All panels respect tribal-data row-level suppression
(cf. [plan/02 § Auth + data-sovereignty](./02-mcp-integration.html#auth--data-sovereignty-notes)).

## DuckLake + GitHub LFS

The pilot keeps DuckLake's Postgres catalog + Parquet storage as
the system of record, with three new operational guarantees:

1. **Time travel.** Every cluster alert and every "Detect"
   timeline event references a DuckLake snapshot ID, so
   re-evaluation against the historical state is one query:

   ```sql
   USE epihack AT (SNAPSHOT '2026-05-19T08:00:00Z');
   ```

2. **Snapshot cadence.** Hourly snapshots during heat season and
   WNV season; daily otherwise. Snapshot metadata (Postgres
   catalog rows describing each snapshot's manifest list) is
   committed to the repo so the **lakehouse history is
   reproducible from a clone**.

3. **GitHub LFS for the catalog backup + manifest snapshots.**
   The Parquet data files themselves stay in object storage (S3
   / R2 / local); but the DuckLake catalog dump (`pg_dump`) and
   the per-snapshot manifest JSON are versioned under
   `schema/snapshots/*.json.lfs` so a fresh clone can
   `git lfs pull && ./scripts/restore-ducklake.sh` to bring a
   laptop up to the latest committed snapshot. Adds a hard upper
   bound on catalog size in the repo (LFS handles the binary
   weight), and gives us a free off-site backup via GitHub.

   - `.gitattributes` entry: `schema/snapshots/* filter=lfs diff=lfs merge=lfs -text`
   - Restore script lives at `scripts/restore-ducklake.sh`
     (Phase&nbsp;1 deliverable).

## Stack

Locked-in decisions:

| Layer | Choice | Why |
|---|---|---|
| Frontend | **Next.js 14 + React 18 + TypeScript**, App Router, `output: 'export'` | One React codebase for the web pilot; Capacitor wraps the same static export for native; TS gives us strict types generated from the OpenAPI spec. SSR is unused (GitHub Pages has no server) but the file-routing + RSC story are still net wins. |
| API contract | **OpenAPI 3.1** at [`api/openapi.yaml`](../api/openapi.yaml) | Source of truth for endpoint shapes. TS types generated via `openapi-typescript`; pydantic v2 models generated via `datamodel-code-generator` for the Python orchestrator at `agents/`. |
| Backend | FastAPI/uvicorn handlers in `agents/src/onehealth_agents/api/` (Phase 06.2) | Conforms to the OpenAPI spec; the agent chain from plan/03 runs behind `POST /v1/reports`. |
| Hosting (pilot) | GitHub Pages, static export via `.github/workflows/deploy-app.yml` | No server needed; same workflow that already publishes the Jekyll docs. |
| Hosting (native) | Capacitor → TestFlight + Play Internal Track | Reuses 100% of the Next.js build; native plugins gate HealthKit / Health Connect / push. |

## Delivery sequence

| Phase | Surface | Status |
|---|---|---|
| **Pilot** | Next.js static export on GitHub Pages ([`app/`](../app/)) | scaffolded — this commit |
| **Prototype** | Capacitor wrapper around the Next.js export → TestFlight + Play Internal Track | new |
| **v1** | Native iOS (Swift / SwiftUI) + Android (Kotlin / Jetpack Compose) builds sharing a thin shared-logic core, OR Capacitor production build if no native-only feature is required | new — gated on the prototype's UX findings |

The Capacitor middle step lets us reuse 100% of the pilot's Next.js
output while gating the native-only features (HealthKit /
Health Connect from [plan/05 Phase 4](./05-roadmap.html#phase-4--statewide--evaluation-month-912), camera APIs, push notifications) behind native plugins.

The Phase-0/1 vanilla flows (tick mail-in, three heat flows) are
preserved unchanged under [`app/legacy/`](../app/legacy/) until each
is ported into the React app. Migration table lives in
[`app/README.md`](../app/README.html).

## Mapping to Figure 2 Minimum Dataset

| Class | Anonymous report supplies | Profile-opt-in supplies |
|---|---|---|
| General | coarse geo (ZIP/km), date, report type | precise geo (if opted), household ID |
| Human | symptom-icon picks (if Human), event class | full Figure 2 Human class, demographics, contact |
| Severity | self-rated icon scale (😊 → 😖) | clinician-confirmed severity score |
| Exposure | exposure-icon picks (water, smoke, animal contact) | full Figure 2 Exposure class, duration, location-of-exposure |
| Auxiliary | photo (EXIF-stripped) | wearable readings (opt-in) |
| Environmental | (always live from MCPs) | — |
| Livestock | species icon, count, photo (Animal reports) | husbandry context (opt-in) |
| Wildlife | species icon, count, photo (Animal reports) | iNat / WHISPers cross-reference (opt-in) |

## Mapping to existing agents

| Agent | New responsibility |
|---|---|
| [Intake](./03-agentic-architecture.html#intake-agent) | Three intake forms, EXIF strip enforcement, IP hashing, consent-profile gating |
| [Geo-Enrichment](./03-agentic-architecture.html#geo-enrichment-agent) | Coarsen GPS / IP → ZIP / km cell at write time |
| [Validation](./03-agentic-architecture.html#validation-agent) | Reject photos with surviving EXIF GPS; tribal-row suppression |
| [Triage](./03-agentic-architecture.html#triage-agent) | Output is **routing only, never diagnosis**; regex output-guard enforces this |
| [Enrichment](./03-agentic-architecture.html#enrichment-agent) | Pull contextual public-health signals from MCPs; surface alongside report |
| [Notification](./03-agentic-architecture.html#notification-agent) | Public-source-cited copy; reply-back when report contributes to Detect |
| [Cluster Detection](./03-agentic-architecture.html#cluster-detection-agent) | New report types feed the spatio-temporal detector |
| [Knowledge Update](./03-agentic-architecture.html#knowledge-update-agent) | Write coarsened `public.observation`, encrypted `precise.observation` |

## New schema

Lands as `schema/deep/report_intake.sql` (Phase 06.1) with:

- `report_intake` node type (one row per submission, anonymous-by-default)
- `media_asset` node type (one row per photo, with `exif_stripped_at`)
- `coarse_geo_token` table (rotating-salt IP → token map; not in `kg.node`)
- `kg.v_public_observations` view that joins `report_intake` to its
  coarsened location for the public dashboard
- `kg.v_precise_observations` view (agency-only, consent-gated)

Edge IDs reserved in the 70000–70999 block (next free after the
60000–60999 used by `outbreaks_near_me.sql`).

## Open questions

1. **Incentives.** Capture the workshop list (above).
2. **Native-app framework.** Capacitor everywhere, or
   Capacitor-for-pilot + native rewrite for v1? Driven by whether
   HealthKit / Health Connect / silent push needs justify the
   native-rewrite cost.
3. **Photo storage.** Object store (S3 / R2) vs. inline in
   DuckLake. Leaning S3-equivalent with the row in DuckLake
   carrying the URL + content hash, for cost and CDN reasons.
4. **CDC MCP.** Is there an existing CDC-data MCP we can adopt, or
   do we need to ship `cdc-mcp` to surface FluView / RSV-NET /
   COVID-NET context? (Phase 06.2 if we ship it.)
5. **Bidirectional confirmation.** When a report contributes to a
   Detect milestone, what's the consented channel for the
   reply-back? In-app push only, or also SMS / email if the user
   shared contact?

## Acceptance criteria

The Phase 06 ship is done when:

- A new user can file an **Animal** report from a fresh phone in
  **under 60 seconds**, with zero text input, and the report
  lands in `public.observation` with ZIP-coarsened location.
- A new user can file the same report **offline**, and it
  syncs cleanly on reconnect.
- An uploaded photo with embedded GPS is **rejected by the
  server** (defense-in-depth check).
- The profile UI defaults every consent toggle to **off** and
  the toggles are reflected in the `consent_profile` row.
- Triage Agent output never contains the strings "you have", "you
  may have", "this is", or "diagnosis" (regex output guard +
  test).
- DuckLake `AT (SNAPSHOT …)` queries reproduce the historical
  state of `public.observation` for any past snapshot.
- The admin dashboard renders cleanly at 360&nbsp;px and at
  1440&nbsp;px.
- A pen-tester cannot recover a reporter's precise location or
  IP from the public dataset.
