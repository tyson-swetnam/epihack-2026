---
title: "Plan 09 — Dual datastore: MongoDB for mobile, DuckLake for web + analytics"
---

# 09 — Dual datastore (MongoDB for mobile, DuckLake for web/analytics)

Decision (2026-05-20): the **mobile app persists reports to MongoDB**; the
**hosted website and the analytics/knowledge-graph backend stay on DuckLake**.
Both write paths go **through FastAPI** (chosen over direct device→Realm), so
the privacy contract stays enforced in one place. Mobile reports are then
**synced into DuckLake** so the agents, MCP servers, and cluster detection see
a unified dataset.

This plan slots into `plan/08-mobile-ux-revamp.md` **Phase 3** (backend wiring):
the polished UI keeps calling `createReport()` → `POST /v1/reports`; only the
server-side sink changes by channel.

## Architecture

```
            ┌─────────── same api/openapi.yaml contract ───────────┐
 Web build  │  POST /v1/reports                                     │
 (static) ──┤      X-Client-Channel: web    → FastAPI → DuckLake ───┼─► knowledge graph
            │                                   │  (kg_writer)      │   (agents, MCP,
 Mobile     │      X-Client-Channel: mobile  → FastAPI → MongoDB ───┤    cluster scan)
 (Capacitor)│                                   │  (mongo_writer)   │        ▲
            └───────────────────────────────────┼───────────────────┘        │
                       privacy enforcement       │                            │
                       (validate/coarsen/EXIF/   └── mongo→ducklake sync ──────┘
                        triage-guard) runs BEFORE     (idempotent on observation_id)
                        the sink, for BOTH channels
```

- **One contract, one enforcement point.** Both channels run
  `validation.py` coarsening + the EXIF/`photo_exif_gps_present` check + the
  triage output-guard *before* the sink is chosen. The sink is the only
  difference.
- **Channel selection.** The web and mobile builds ship the same bundle
  (plan/06 Capacitor), so the channel is a build-time flag baked into the
  client and sent as a header: `X-Client-Channel: mobile|web` (default `web`).
  Add it to `api/openapi.yaml` as an optional header param (spec-first).
- **Mobile offline.** Since the write path is server-mediated (not Realm),
  offline = a local cache + retry queue in the app keyed by `claim_token`
  (no Atlas Device Sync). Documented as such so expectations are clear.

## Why Mongo for mobile (given it still goes through FastAPI)

Operational separation: a flexible document store for an evolving mobile
payload and a separate high-write ingest path, decoupled from the analytical
lakehouse. Analytics unification is preserved by the sync. (If true
offline-first ever becomes the priority, the alternative is direct
device→Atlas Device Sync — but that moves privacy enforcement off the server
and is explicitly **not** this plan.)

## Hosting + sync — recommendation (you'll confirm)

**Recommended: self-hosted MongoDB Community on the VM** (new `mongodb`
Ansible role), bound to `127.0.0.1`, alongside Postgres. Rationale: the stack
is already self-hosted (one-command VM deploy), data stays on the box (privacy),
and — because we chose server-mediated writes — we don't need Atlas Device
Sync. **Atlas (managed)** stays the alternative if you later want managed ops
or Device Sync.

**Sync: a scheduled `mongo_to_ducklake` job** (systemd timer, every N minutes)
that reads new Mongo report docs past a stored watermark (`created_at`/`_id`)
and writes each into DuckLake via the existing `kg_writer.persist_observation`
(idempotent on `observation_id`, so re-runs are safe). A change-stream consumer
is the lower-latency upgrade path later.

## Components to build

### FastAPI / agents
- **`agents/src/onehealth_agents/mongo_writer.py`** — `MongoWriter` mirroring
  `kg_writer`'s `persist_observation()`: writes one report document
  (structured fields verbatim; `notes`/`claim_token` as SHA-256 digests, same
  privacy posture) to the `reports` collection; returns `(observation_id,
  claim_token)`. Reads `MONGODB_URI`. In-memory/`mongomock` fallback when unset
  so tests stay offline (CLAUDE.md rule).
- **`api/routes/reports.py`** — after the shared privacy/validation step,
  select sink by `X-Client-Channel`: `mobile` → `MongoWriter`, else
  `kg_writer`. Status read-back (`GET /v1/reports/{id}`) checks Mongo first
  then DuckLake (or routes by channel recorded at write time).
- **`agents/pyproject.toml`** — add `pymongo>=4.8` (+ `mongomock` as a test
  extra).

### Mongo → DuckLake sync
- **`agents/.../sync/mongo_to_ducklake.py`** — watermarked, idempotent ETL;
  CLI entrypoint runnable by a timer. Writes via `kg_writer` so synced rows
  land as `kg.node('observation')` + `kg.agent_run` + a DuckLake snapshot.

### Ansible
- **`roles/mongodb/`** (if self-hosted) — install MongoDB CE, bind
  `127.0.0.1`, create the app DB + user; or, for Atlas, just consume
  `vault_mongodb_uri`.
- **`roles/fastapi`** — add `MONGODB_URI` to the API env; install a
  `onehealth-mongo-sync.timer` + service unit for the ETL.
- **`group_vars/all.yml`** — `mongodb_*` settings; **vault** — `vault_mongodb_uri`/password.
- **`playbook.yml`** — add `mongodb` role before `fastapi` (so the URI/health
  exist before the API + sync start).

### App
- **`app/src/lib/api-client.ts`** — send `X-Client-Channel` from
  `NEXT_PUBLIC_CLIENT_CHANNEL` (default `web`; the Capacitor build sets
  `mobile`). Add a local retry queue keyed by `claim_token` for offline.
- **`api/openapi.yaml`** — document the `X-Client-Channel` header.

## Phases

- **A — App-layer routing (no infra):** add the channel header + `MongoWriter`
  with `mongomock` fallback; reports route selects the sink; tests offline.
- **B — Mongo provisioning:** `mongodb` role (self-hosted) **or** Atlas URI in
  vault; wire `MONGODB_URI`. *(Gated on your hosting choice.)*
- **C — Sync:** `mongo_to_ducklake` ETL + systemd timer; verify a mobile-channel
  report appears in DuckLake with a new snapshot.
- **D — App offline queue + e2e:** retry queue; end-to-end test
  (mobile POST → Mongo doc → sync → DuckLake `AT (VERSION)` shows it).

## Guardrails (unchanged from the contract)

- Privacy enforcement runs before *both* sinks; no raw lat/lon, EXIF stripped,
  no diagnosis/score, audit/digest rules apply to the Mongo doc too.
- `api/openapi.yaml` stays the source of truth; regenerate `api-types.ts`.
- Tests must not hit the network — `mongomock` / skip when `MONGODB_URI` unset.

## Open decision (please confirm)

**Hosting:** self-hosted MongoDB CE on the VM *(recommended)* vs MongoDB Atlas.
Everything else above is independent of this choice; Phase B is the only part
that branches on it.
