---
title: How we vibe-coded the Sentinel
nav_order: 7
---

# How we vibe-coded the Sentinel

## What this is

This page is a retrospective on how the AZ One Health Sentinel stack
(eleven MCP servers, an eight-agent FastAPI backend, a Next.js mobile
app, a DuckLake-on-Postgres knowledge graph, a two-store write path,
two Phase-3 dashboards, and a one-command Ansible deploy) was built
with [Claude Code](https://claude.com/product/claude-code) over a
**four-day burst, May 19 – May 23 2026**. Across that window we
shipped **9 Claude Code sessions, 5,907 transcript lines, ~1,250 user
turns**, and roughly **80 commits** ending at `15f750f`. The single
longest session (`173972db…`, 3,200 lines) covers the mobile-UX
revamp, the MongoDB-side datastore split, and the first end-to-end
deploy to a Jetstream2 VM.

"Vibe-coding" here means a tight loop:

1. The user (`tswetnam@arizona.edu`) writes an intent — usually one
   to three English sentences, occasionally a multi-paragraph plan,
   never a code snippet.
2. Claude produces the plan (`plan/NN-*.md`), drafts the code, runs
   the tests, and opens the PR.
3. The user reviews behaviour against the running app at
   `epihack-test.cis240692.projects.jetstream-cloud.org`, sends a
   one-line correction, and the loop repeats.

No `git apply`-style snippets land from the user side. The
artifact-to-prompt ratio is roughly **one shippable feature per
2-to-5 English prompts**, which is the calibration we want future
readers to keep in mind.

## Session-by-session timeline

| Session id (short) | Dates (UTC) | Lines | One-line theme |
|---|---|---:|---|
| `173972db…` | 2026-05-19 → 2026-05-22 | 3,200 | Ansible bring-up · Next 16/React 19 mobile-UX revamp · MongoDB sink + Phase A/B/C/D · 422-on-submit fix |
| `849197ca…` | 2026-05-20 → 2026-05-23 | 946 | Repo housekeeping (README/SECURITY/index) · synthetic dataset · signal-monitor dashboard · "make it real" |
| `924a2aed…` | 2026-05-22 | 546 | EpiHack pitch reconciliation ("Sentinel" not "EyeDetect") · VectorSurv-MCP as a Claude.ai custom connector · nginx + TLS |
| `ff2c20eb…` | 2026-05-20 → 2026-05-22 | 402 | DuckDB-WASM in-browser query console + pinned-CDN viewer page |
| `367a72c1…` | 2026-05-22 | 259 | MCP READMEs → headless-browser walkthrough · connector instructions for Claude.ai / Desktop / Cursor / Codex |
| `2442be0b…` | 2026-05-21 → 2026-05-22 | 224 | Personal dashboard · Leaflet "your reports" map · ZIP-level community view · login on landing page |
| `0d7738c5…` | 2026-05-21 | 217 | `/loop` + sub-agents to verify every MCP against its real upstream API |
| `02a81450…` | 2026-05-22 | 66  | Wiring the analytics dashboard link into the published site · top-level docs/source links |
| `9b4b90bf…` | 2026-05-23 | 47  | Archive prep: this page, the Zensical/MkDocs Material plan, the headless-browser pass over the published site |

Total: **5,907 lines** of Claude Code transcript, plus three
`memory/*.md` notes the agent wrote to itself during the burst
(`pitch-vs-repo-reconciliation`, `datastore-split-mobile-mongo`,
`synthetic-data-and-signal-monitor`).

## Top 10 most-impactful prompts

These are the prompts whose downstream diff was largest, ordered
roughly by architectural reach.

### 1. The mobile-UX pivot

> "here is a much more polished version of a phone app — this is the
> preferred UX and design flow — create a plan to integrate this
> into the UI of our app here, keeping the DuckDB and DuckLake
> backend and other features, including the MCP servers"
>
> ([`173972db…`](#session-by-session-timeline), 2026-05-20 13:49)

Produced `plan/08-mobile-ux-revamp.md`, then the full Next.js 16 +
React 19 + Tailwind port at `app/src/app/`, `app/src/components/`,
and `app/src/lib/`. The original vanilla-HTML flows were archived
under `app/legacy/`. Commit `7402b1a`.

### 2. The datastore split

> "Phase B — do self-hosted MongoDB on the VM with a new ansible
> role for deploying mongo, then Phase C and Phase D"
>
> (`173972db…`, 2026-05-20 19:12)

Created the dual-sink write path: `agents/src/onehealth_agents/
mongo_writer.py`, the watermarked `sync/mongo_to_ducklake.py`, and
the `ansible/roles/mongo/` role bound to `127.0.0.1` with auth on.
The `X-Client-Channel` header — set in
`app/src/lib/api-client.ts` and read in `agents/.../api/routes/
reports.py` — decides the sink **after** privacy enforcement, so
the contract lives in one place. Documented in
`plan/09-mobile-datastore.md`. Commits `86331cc`, `f235bf7`.

### 3. The real-MCP wire-up

> "use your `/loop` and sub-agent capabilities to evaluate the
> functionality and test all of the mcp/ servers: check that they
> are ready to connect to the knowledge graph and to the reporting
> structures (its okay to use synthetic data for these) — but then
> you must wire up every server to its actual real API or service
> and confirm that its works in production. Update the respective
> README.md with the results."
>
> (`0d7738c5…`, 2026-05-21 13:16, set via `/goal`)

Drove a parallel pass over every `mcp/<server>/README.md` and the
upstream-API snapshots in `mcp/vectorsurv-mcp/openapi/`. Each
server's README ended with a real-upstream verification stanza;
where no public API existed (e.g. `great-az-tick-check-mcp`,
`mag-hrn-mcp`) the README is explicit about the mock posture and
the sunset clause.

### 4. The personal-dashboard scope

> "after a user has created a profile, they should be able to see
> the public analysis dashboard with current data from the MCP
> servers — there should also be a login button somewhere on the
> landing page of the One Health Sentinel so they can log in. The
> personal dashboard should show their location of reports they've
> submitted on a leaflet map with a pop-up of their report when
> they click on their dot, they should not be able to see other
> people's report locations, but at a zip code level they should
> be able to see details about local and regional reports. They
> should also have a dashboard where they can see their reports,
> or withdraw their reports, view their photos or remove their
> photos."
>
> (`2442be0b…`, 2026-05-21 20:34)

A single prompt that defined the entire `app/src/app/dashboard/`
route, the privacy posture for "your dots, not theirs," and the
withdrawal/photo-delete affordances. Landed across
`app/src/components/DashboardView.tsx` and
`agents/.../api/routes/profile.py`. Commit `9039423`.

### 5. The event-class taxonomy expansion

> "in the App, the environmental factors should include food-based
> illness (spoiled food, food cart/truck), in wildlife it should
> include pets and specifically animal health or malnourishment,
> and in persons it should include animal bites or scratches"
>
> (`173972db…`, 2026-05-20 21:08)

Edits cascaded through `api/openapi.yaml`, `app/src/lib/api-types.ts`
(regenerated, not hand-edited), the report-flow components, and
the corresponding `schema/deep/*` slugs. Commit `6db9cda`.

### 6. The synthetic dataset + signal monitor

> "Let's make it real. Create the missing data directories. Create
> a synthetic dataset with several thousand report submissions from
> across the state — in the synthetic dataset, include a higher
> prevalence of [redacted: dengue-like, GI-cluster, animal die-off]
> signals in three named AZ communities. Importantly, these are
> just reports — they are not diagnoses, and the app should never
> make a suggestion of such."
>
> (`849197ca…`, 2026-05-22, set via `/goal`)

Produced 4,395 synthetic observations tagged
`source_fig='synthetic-load'`, the `scripts/export_signals.py`
exporter, and the `dashboard/signals/` static page. The "never
diagnose" constraint was honoured *by construction*: the generator
seeded report-category counts, no disease/diagnosis property key
exists in the kg, and free-text notes are stored as SHA-256
digests only. The synthetic data itself is gitignored
(`15f750f`); the exporter, dashboard, and the privacy-safe ZCTA
aggregations are committed (`82e0297`). The synthetic prompt is
also the source of the AZ-community signal-shape choices, which is
why we've redacted the three towns here — the cluster fixtures
read better in a generator than on an archive page.

### 7. The bring-up

> "check out the ansible deployment, run it and start the app
> services"
>
> (`173972db…`, 2026-05-19 22:41 — *first prompt of the project*)

The single sentence that produced the first end-to-end deploy on a
Jetstream2 VM. The Ansible playbook was already drafted; this
prompt forced it through the *actual* Ubuntu 24.04 install loop
and produced `ansible/`, `deploy/README.md`, and the per-MCP
systemd units committed in `bfd3d56` and `ff6a9b8`.

### 8. The pitch reconciliation

> "We built a participatory surveillance tool — and before that
> phrase scares anyone off, let us tell you what it actually is."
> (full pitch script pasted, ~3 KB)
>
> "make sure that our app, dashboard, and github.io website have
> all of these aspects documented and characterized"
>
> (`924a2aed…`, 2026-05-22 14:25)

The EpiHack organisers' pitch named the project "EyeDetect" and
described AWS/DynamoDB/kiosks. The user explicitly chose: keep
**"AZ One Health Sentinel"** as the name, document only what's
*built* (DuckLake-on-Postgres + MongoDB + FastAPI + 11 MCPs +
GitHub Pages), and stub the unbuilt pitched features as labelled
demo stubs (leaderboard, rewards, weekly-email opt-in,
weather-strip). The reconciliation is recorded verbatim in
`~/.claude/projects/.../memory/pitch-vs-repo-reconciliation.md`.

### 9. The DuckDB-WASM page

> "add in a new page to the project, a DuckDB-WASM viewer with
> SQL query window, and a set of pre-written queries for common
> requests"
>
> (`ff2c20eb…`, 2026-05-20 21:09)

Produced the in-browser query console at `app/src/app/duckdb/`
(and a parallel static viewer linked from the Jekyll site), with
DuckDB-WASM pulled from a pinned unpkg URL — same rule as the
MapLibre/Cytoscape pinning used in `map/` and `graph/`. Commit
`fa3e04c`.

### 10. The MCP connector docs

> "on the website, the MCP servers have README.html, e.g.,
> https://tyson-swetnam.github.io/epihack-2026/mcp/vectorsurv-mcp/
> README.html — use sub-agents and headless browser to read these,
> and then follow their directions to set up MCP servers running
> locally on this VM, also create instructions for users to
> connect to the server running here on the test instance in
> platforms like Claude.ai, Claude Desktop, Cursor, Codex, etc."
>
> (`367a72c1…`, 2026-05-22 13:59)

This is the prompt that flipped the MCPs from "self-contained
servers" to "addressable connectors". Sub-agents read each
README via a headless browser, captured the gaps, and patched
them; commit `e4c6a64` lands the `vectorsurv-mcp` Claude.ai
custom-connector recipe; `199bcfc` ships the `FASTMCP_*` env
fixes the connector-style deploy exposed.

## Pivots

Five places where the project's direction changed mid-stream:

1. **2026-05-20 13:49 — Vanilla-HTML → Next.js mobile UX.** The
   "much more polished version of a phone app" prompt (#1 above)
   killed the bundler-less vanilla-HTML flow we'd shipped through
   Phase 2 and brought in Next 16 / React 19 / Tailwind. The
   archived vanilla flow lives on at `app/legacy/`.
2. **2026-05-20 19:12 — One store → two stores.** Until this prompt,
   every write path (web *and* planned mobile) targeted DuckLake
   via `POST /v1/reports`. The "self-hosted MongoDB on the VM"
   prompt (#2 above) introduced the dual-sink architecture
   documented in `plan/09-mobile-datastore.md`, with the
   `mongo_to_ducklake` sync timer doing the reconciliation. Recorded
   in `memory/datastore-split-mobile-mongo.md`.
3. **2026-05-22 14:25 — "EyeDetect" → "Sentinel".** The pitch-vs-repo
   reconciliation (#8 above). The pitch slide named the project
   *EyeDetect*; the user chose to keep **AZ One Health Sentinel**
   in code and docs, leaving "EyeDetect" as a presentation-only
   label that does not appear anywhere in the repo. Documented
   verbatim in `memory/pitch-vs-repo-reconciliation.md`.
4. **2026-05-22 14:25 — Pitch infra ↔ real infra.** The same prompt
   forced a second reconciliation: the pitch described AWS Gateway
   + DynamoDB + kiosks; the repo documents DuckLake-on-Postgres +
   MongoDB + 11 MCPs + GitHub Pages. The pitched-but-unbuilt
   features were either implemented as minimal stubs (profile
   enrichment, personal dashboard, weekly-email opt-in) or labelled
   demo-only in UI copy (leaderboard, rewards, weather strip).
5. **2026-05-20 23:21 — Photo blob → string payload.** The first
   real submit produced a 422 (`Input should be a valid string`,
   `body.payload`), which exposed a contract drift between the
   browser sending a `Blob` and the FastAPI route expecting a text
   field. The fix (`4dd88b1` then `506e6e8`) makes the route
   tolerant of either shape — and tightened the OpenAPI spec.

## Patterns that worked

Six prompting patterns that produced shippable code on first try
(or close to it):

1. **Spec first, code second.** "evaluate the current structure of
   the repository, update the README.md, SECURITY.md…" (#849197ca)
   reliably produced consistent doc + code diffs because the docs
   were edited *before* the code. We extended this to OpenAPI:
   edit `api/openapi.yaml`, then run `npm run gen:api`, then write
   the route. The generated `app/src/lib/api-types.ts` is never
   hand-edited.
2. **Phase-numbered todos.** "continue plan/08 phase 1 — make sure
   to use the design of `Elbaraaa/OneHealth`" (#173972db) and
   "Phase B — do self-hosted MongoDB on the VM with a new ansible
   role" (#173972db) pinned each work-unit to a numbered phase in
   the plan doc. "proceed to Phase 2" / "continue from where you
   stopped" then carried the context across context-compactions.
3. **Cite the failing URL, not the bug.** "I'm trying in my browser,
   `http://epihack-test.cis240692.projects.jetstream-cloud.org/
   report/` but it gets 404 for the different selections" (#173972db)
   gave Claude enough information to diagnose the static-export
   route mismatch without a stack trace.
4. **Paste the exact error.** "the app is getting an error when I
   try to submit my report ```API 422: {"detail":[…]}```" (#173972db)
   bypassed any guessing and produced commit `4dd88b1` directly.
5. **Sub-agents + headless browser for cross-doc passes.** The two
   "use sub-agents and headless browser to read these" prompts
   (#0d7738c5 and #367a72c1) farmed out per-MCP README walks in
   parallel and consolidated the deltas into a single PR. Same
   trick used for the published-site card audit in `367a72c1` and
   the archive pass in `9b4b90bf`.
6. **Goal-with-`/goal`-then-`begin`.** The `/goal` slash-command
   pinned the long-running condition (e.g. "Finalize and confirm
   the Ansible deployment works end to end, ensure that all MCP
   Servers are operating and 100% functional…"), and a single
   `begin` kicked off the autonomous loop. The Stop hook then
   only released the session when the goal condition was met,
   which is why `173972db` ran for three days without
   re-prompting the high-level intent.

## Patterns that didn't

Three places where Claude needed correction:

1. **Optimistic completion claims.** Multiple times the user pinged
   "are we stuck?" / "how is it going? just making sure things are
   moving along" / "I think you're stuck on this step. give me an
   update on where you are at in the plan" (all #173972db,
   2026-05-20 afternoon). The fix was a more explicit phase-gate
   plan in `plan/08` and the use of background tasks
   (`run_in_background`) instead of inline long-runs, so progress
   was visible in `task-notification` events.
2. **Pitch-vs-repo drift.** The pitch script (#924a2aed) named the
   project "EyeDetect" and described AWS Gateway / DynamoDB /
   kiosks; an unprompted Claude would have happily updated the
   README to match. The user's explicit "keep Sentinel, document
   only what's built" correction is now memorialised in
   `memory/pitch-vs-repo-reconciliation.md` so the next session
   inherits the decision.
3. **Synthetic data being too realistic.** The first pass of the
   synthetic-dataset generator wrote disease names ("dengue",
   "food poisoning") into observation properties. The user's
   guard rail — "these are just reports — they are not diagnoses,
   and the app should never make a suggestion of such" — forced
   the second pass to keep the disease framing *in the generator
   only* and persist only report-category counts plus SHA-256
   digests of free text. The `dashboard/signals/` viewer then
   surfaces *above-baseline categories*, never a labelled cause.

## Reproducibility

The transcripts (`*.jsonl` under
`~/.claude/projects/-home-exouser-epihack-2026/`) are **not
committed** — they live in the local Claude Code state directory
and contain enough timing and tool-call detail that they're best
treated as a working journal rather than a public artifact. What
*is* committed is everything they produced:

- `api/openapi.yaml` (the contract)
- `agents/` (the orchestrator)
- `app/` and `app/legacy/` (the two UIs)
- `mcp/<server>/` × 11 (the MCP servers + their pinned upstream
  spec snapshots)
- `schema/` and `schema/deep/` (the kg seeds)
- `ansible/` + `deploy/` (the one-command bring-up)
- `plan/01-09` + `plan/10-archival-and-docs.md` (the plan docs,
  in load order)
- `memory/` notes inside the project's Claude state directory —
  three load-bearing decisions surfaced in this page

Future readers can re-run any of the patterns above against this
repo without seeing the transcripts: every named prompt landed in
either a plan doc, a commit message, or a `memory/` note, and the
six worked patterns ("spec first," "phase-numbered todos," etc.)
are the operational summary. A second team picking this up should
expect roughly the same calibration: **one shippable feature per
2-to-5 English prompts, given the spec and the plan doc are in
place first**.
