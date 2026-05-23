# Plan 10 — Archival & docs site (post-EpiHack)

**Status:** Draft, 2026-05-23
**Owner:** Tyson Swetnam
**Scope:** Prepare this repo for archival (or pause-and-resume) with a UI/UX-journey landing page, a full MkDocs Material docs site, and a refreshed Ansible deploy.

---

## 1 — Goal

EpiHack Arizona 2026 has concluded. The repo currently presents itself as a flat directory of working components (app, agents, 11 MCPs, dashboards, schemas, plans). For an archival hand-off we need to:

1. **Tell the story** — why we built each piece, in what order, and how they fit together.
2. **Preserve the path** — anyone reviving this in 2027+ should be able to bootstrap from scratch.
3. **Document the *how* of vibe-coding** — the Claude Code prompting history is itself an artifact worth keeping.
4. **Lock in working state** — every MCP, every app page, every playbook role tested and screenshotted.

Out of scope: new features, new MCPs, new agent capabilities. This plan is about *capturing* what exists, not extending it.

---

## 2 — Two-surface publishing model

`gh-pages` already serves two surfaces from one branch via `keep_files: true`:

- `/` — Jekyll site (cards landing) — **redesigned as a narrative journey**
- `/app/` — Next.js static export — **unchanged**

We add a third:

- `/docs/` — **new** MkDocs Material site (full reference)

The redesigned `index.html` becomes a *trailhead*: it hooks the visitor, then routes them either into the live app (try it), the docs site (understand it), or the source (build on it).

```
                 ┌─────────────────────────────────────────────────────┐
                 │  /  (Jekyll: hero + journey ribbon + 6 entry cards) │
                 └──────────────┬────────────────────────┬─────────────┘
                                │                        │
              ┌─────────────────▼───────┐    ┌───────────▼──────────┐
              │ /app/  (live React app) │    │ /docs/  (MkDocs Mat.) │
              │   Jetstream2 demo link  │    │   journey + reference │
              └─────────────────────────┘    └──────────────────────┘
```

Three GitHub Actions workflows publish to `gh-pages` with `keep_files: true`:

| Workflow | Triggers on | Lands at |
|---|---|---|
| `deploy-jekyll.yml` | root non-`app/`, non-`api/`, non-`docs/` paths | `gh-pages:/` |
| `deploy-app.yml` (existing) | `app/**`, `api/openapi.yaml` | `gh-pages:/app/` |
| `deploy-docs.yml` (**new**) | `docs/**`, `mkdocs.yml` | `gh-pages:/docs/` |

`_config.yml` excludes get a new entry: `- docs` and `- mkdocs.yml` so Jekyll doesn't try to render Markdown that MkDocs owns.

---

## 3 — Phase-by-phase plan

### Phase 0 — Reconnaissance (this plan) ✅
Inventory completed. 11 MCPs, 9 app pages, 17 plan docs, 14 Ansible roles, 12 schema seeds, 9 Claude Code transcripts (~5907 lines).

### Phase 1 — Redesign `index.html`

**Goal:** Replace the flat card grid with a top-to-bottom journey.

**New section order:**

1. **Hero** — keep current gradient, add a "Project archived 2026-05" badge and a "Read the Journey" CTA → `/docs/journey/`.
2. **Journey ribbon** (new) — 6 numbered steps as a horizontal strip:
   `Frame → Map → Tool → Store → Orchestrate → Surface`
   Each step links into the matching MkDocs page.
3. **System diagram** (new) — one inline SVG showing: phone → API → 8 agents → 11 MCPs → DuckLake/Mongo. Replaces three paragraphs of prose.
4. **Try it** — current live-demo card, slimmed.
5. **Read it** — three cards: Journey, Architecture, Reference (all → `/docs/`).
6. **Source** — repo + license + citation.
7. **Browse-everything** (collapsed) — the *current* card grid, demoted into a `<details>` so nothing breaks, but it's no longer the front-and-center experience.

Visual: keep the Wildcat-blue / Sedona-red palette. Add an inline footer crediting EpiHack participants + Anthropic Claude Code as a tool.

### Phase 2 — Stand up `docs/` (MkDocs Material)

**Tech:**

- `mkdocs-material` (Material theme, the closest OSS analogue to "Zensical")
- `mkdocs-mermaid2-plugin` (architecture diagrams)
- `mkdocs-glightbox` (clickable screenshots)
- `pymdown-extensions` (admonitions, tabs, code annotations)
- `mike` (versioning — pin "1.0-archive" once frozen)

**Top-level nav (proposed):**

```
Home                   docs/index.md
Journey ─┬─ 01 Frame the problem        journey/01-frame.md
         ├─ 02 Map the data sources     journey/02-map.md
         ├─ 03 Build the MCPs           journey/03-mcps.md
         ├─ 04 Stand up the store       journey/04-store.md
         ├─ 05 Orchestrate the agents   journey/05-orchestrate.md
         ├─ 06 Ship the app             journey/06-app.md
         └─ 07 Vibe-coding history      journey/07-vibe-coding.md
Architecture ─┬─ System overview        architecture/overview.md
              ├─ Privacy contract       architecture/privacy.md
              ├─ Data flows (A/B/C/D)   architecture/data-flows.md
              └─ Eight-agent topology   architecture/agents.md
MCP servers ─┬─ Overview                mcps/index.md
             ├─ vectorsurv-mcp          mcps/vectorsurv.md
             ├─ knowledge-graph-mcp     mcps/knowledge-graph.md
             ├─ ... (one per server)
App ─┬─ Pages tour                      app/pages.md
     ├─ Privacy & EXIF stripping        app/privacy.md
     └─ Offline retry queue             app/offline.md
Knowledge graph ─┬─ Schema reference    kg/schema.md
                 ├─ Seed load order     kg/seeds.md
                 └─ Example queries     kg/queries.md
Deploy ─┬─ Local development            deploy/local.md
        ├─ Ansible / Jetstream2         deploy/ansible.md
        └─ GitHub Pages                 deploy/gh-pages.md
Reference ─┬─ OpenAPI spec              reference/openapi.md
           ├─ MCP tool inventory        reference/mcp-tools.md
           ├─ Test matrix               reference/test-matrix.md
           └─ Glossary                  reference/glossary.md
About ─┬─ Governance                    about/governance.md
       ├─ Security                      about/security.md
       ├─ Contributing                  about/contributing.md
       ├─ Changelog                     about/changelog.md
       └─ Citation                      about/citation.md
```

Most "About" pages are stubs that include the existing top-level markdown via `{% include-markdown "../GOVERNANCE.md" %}` (mkdocs-include-markdown-plugin) — no duplication.

### Phase 3 — Author the journey

Each `journey/0N-*.md` page has the same structure:

1. **What we wanted** (one paragraph)
2. **What we built** (concrete components: file paths, tool counts, links into Reference)
3. **What it looks like** (screenshots from Phase 5)
4. **Decisions & trade-offs** (why DuckLake + Mongo split; why coarse-only geo; why never-diagnose triage)
5. **Where to go next** (link to next journey page + relevant reference)

Drafting cadence: one journey page per pomodoro, drawn from the corresponding `plan/0N-*.md` source.

### Phase 4 — Vibe-coding history

`journey/07-vibe-coding.md`. Distilled from the 9 transcripts under `/home/exouser/.claude/projects/-home-exouser-epihack-2026/`:

| Transcript | Lines | Approx. focus (guess from size) |
|---|---|---|
| 173972db | 3200 | the long main thread |
| 849197ca | 946 | |
| 924a2aed | 546 | |
| ff2c20eb | 402 | |
| 367a72c1 | 259 | |
| 2442be0b | 224 | |
| 0d7738c5 | 217 | |
| 02a81450 | 66 | |
| 9b4b90bf | 47 | |

Delegated to a `general-purpose` subagent. Output structure:

- **Timeline**: chronological one-liner per session ("session 4 — added MAG HRN MCP after Phoenix outreach asked about cooling centers")
- **Prompts that produced the most code**: top 10 prompts ranked by diff size, each with a short excerpt and a link to the resulting commit.
- **Pivots**: places where we changed direction mid-session (e.g. when we replaced AWS/DynamoDB framing with DuckLake + Mongo per `pitch-vs-repo-reconciliation` memory).
- **What worked**: prompting patterns that produced shippable code first-try.
- **What didn't**: where Claude needed a second pass, and what the user said to course-correct.
- **Reproducibility note**: how to re-run any prompt (the transcripts include the exact commands).

**Important:** redact any user names, tokens, or per-session UUIDs before publishing.

### Phase 5 — Headless inspection (parallel sub-agents)

Goals:

1. Screenshot every URL under `https://tyson-swetnam.github.io/epihack-2026/` for embedding in journey pages.
2. Screenshot every page of the live app at `http://epihack-test.cis240692.projects.jetstream-cloud.org/`.
3. Detect 404s and JS console errors → file as tasks.

**Tool:** `mesa-mcp` (when its tools land) for high-level browser control. Fallback: `npx playwright` invoked from a one-off Python script — already a sibling project dependency.

URL list (auto-generated from a `find . -name index.html` plus the live-app routes — `/`, `/sign-in`, `/report/{human,animal,environmental,heat}`, `/profile`, `/dashboard`).

Output: `docs/_screenshots/<page-slug>.png`, referenced from the journey/app pages.

### Phase 6 — Smoke-test everything

A `scripts/smoke-all.sh` (new) that runs:

```bash
# Per MCP
for d in mcp/*/; do (cd "$d" && uv sync --frozen && uv run pytest -q) ; done
# Agents
(cd agents && uv sync && uv run pytest -q)
# App
(cd app && npm ci && npm run gen:api && npm run typecheck && npm run lint && npm run build)
# OpenAPI
redocly lint api/openapi.yaml
```

Output: `docs/reference/test-matrix.md` table — green/yellow/red per component, with logs linked.

`/loop` use: invoke this as `/loop 1h scripts/smoke-all.sh` on the Jetstream2 VM for the final 24 hours before tagging archive — gives a visible "still green" trail in CI history.

### Phase 7 — Ansible refresh

For each role under `ansible/roles/`:

1. Diff `tasks/main.yml` against the corresponding component's `pyproject.toml` / `package.json` / `Dockerfile` / systemd unit.
2. Verify env vars listed in `.env.example` are mirrored in `group_vars/all.yml` (or `all.vault.example.yml`).
3. Add anything missing. Bump `ansible/CHANGELOG.md`.

Specific items I already know need attention:

- `app` role: needs `NEXT_PUBLIC_API_BASE` and the Mongo client env if not already there.
- `mongodb` role: confirm it exists end-to-end (memory says "2026-05-20 datastore split" added this).
- `ducklake` + `postgres` roles: confirm seed-load order matches CLAUDE.md (`standards.sql`, `pathogens.sql` first).
- `mcp_servers`: enumerate all 11 services as `loop` items.

Output: `docs/deploy/ansible.md` — a walkthrough from `inventory.yml` to "the VM is up".

### Phase 8 — Archival polish & deploy

- Rewrite top of `README.md` as an *archival* landing: status badge, "as of 2026-05-23", "to revive: …", citation block.
- Add `CITATION.cff` (so GitHub shows the "Cite this repository" button).
- Final pass on `CHANGELOG.md` — collapse the EpiHack sprint commits into a single "v1.0 — EpiHack Arizona 2026 release" entry.
- Tag `v1.0-archive` once both deploys are green.
- Optionally: GitHub repo settings → "Archive this repository" (the user's call; this plan only readies it).

---

## 4 — Sub-agent delegation

Designed for parallelism. Each numbered phase can launch independent agents:

| Phase | Sub-agent type | Inputs | Output |
|---|---|---|---|
| 3 | `general-purpose` × 7 (one per journey page) | `plan/0N-*.md` + relevant code | `docs/journey/0N-*.md` |
| 4 | `general-purpose` | transcript jsonl files | `docs/journey/07-vibe-coding.md` |
| 5 | `general-purpose` × 2 (Jekyll site + live app) | URL list | screenshots + 404 report |
| 6 | `Explore` | repo state | smoke-test inventory before scripting |
| 7 | `general-purpose` × N (one per role) | `ansible/roles/<role>/` + corresponding component | role diffs |

Agents run in parallel where independent (Phase 3 pages, Phase 7 roles).

---

## 5 — `/loop` use

Two loops only:

- **Phase 5**: `/loop` the screenshot script every 10 min while iterating on the redesign, so I see fresh thumbnails as I edit.
- **Phase 6**: `/loop 1h scripts/smoke-all.sh` for 24 h pre-tag.

Other phases are one-shot, not recurring.

---

## 6 — Risks & open questions

1. **`docs/` URL collisions with existing top-level `docs` content?** None: no `docs/` directory exists today.
2. **MkDocs Material vs "Zensical"** — Zensical is an internal Material variant. We default to vanilla `mkdocs-material`; if Zensical specifics are required, swap the theme line and re-deploy.
3. **Transcript privacy** — Claude Code transcripts may contain tokens, API keys, hostnames, or third-party emails. Phase 4 must scrub these before publishing.
4. **Tribal-data disclosure** — same governance rules apply to the docs site as to the code. Tribal-specific seeds remain `MOU_RENEWED_THROUGH`-gated; the docs page describes the *mechanism*, not the data.
5. **Bit-rot found by Phase 6** — likely. We absorb small fixes into the plan; anything large becomes a follow-up task and ships in v1.1-archive.

---

## 7 — Done criteria

- [ ] `index.html` ships the new journey layout; old card grid preserved under `<details>`.
- [ ] `docs/` builds locally (`mkdocs serve`) and on GH Actions; landing page reachable at `/epihack-2026/docs/`.
- [ ] Every component has a journey page + a reference page.
- [ ] Vibe-coding history published, scrubbed.
- [ ] Phase 6 smoke matrix is all green (or yellow with documented exceptions).
- [ ] Ansible CHANGELOG updated; `ansible-playbook --check` clean against a fresh inventory.
- [ ] `v1.0-archive` tag pushed; both Pages workflows publish without `keep_files` conflicts.

---

## 8 — One-PR-per-concern map

Per the repo's ~200-line-diff rule:

1. `plan/10-archival-and-docs.md` (this file).
2. `index.html` redesign + new SVG.
3. `docs/` scaffold + `mkdocs.yml` + `.github/workflows/deploy-docs.yml` + `_config.yml` exclude.
4. Journey pages (split into ~3 PRs if each runs long).
5. Vibe-coding history.
6. Screenshots batch.
7. Test-matrix + `scripts/smoke-all.sh`.
8. Ansible refresh (split per role family).
9. README rewrite + `CITATION.cff` + `v1.0-archive` tag.
