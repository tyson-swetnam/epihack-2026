---
title: "Ansible deployment — changelog"
---

# Ansible deployment changelog

Changes made to get the full stack deploying cleanly onto a single
Ubuntu 24.04 box (localhost, `ansible_connection: local`) and to wire the
DuckDB/DuckLake knowledge-graph backend end-to-end. A run now completes with
`failed=0` across all eleven roles; a live `POST /v1/reports` persists into
DuckLake with time-travel versioning, and all eleven MCP servers respond to an
MCP `initialize` handshake.

## post-EpiHack archive refresh — 2026-05-23

Tightening pass after the 2026-05-20 datastore split (Mongo for mobile,
DuckLake for web/analytics) and the profile-enrichment + personal-dashboard
landing. Drives the **RED** finding *and the YELLOW Phase 7b / 7c follow-ups*
in [`plan/ANSIBLE-AUDIT-2026-05-23.md`](../plan/ANSIBLE-AUDIT-2026-05-23.md)
to green.

### Changes

- **`roles/app`** + **`group_vars/all.yml`** — added
  `NEXT_PUBLIC_CLIENT_CHANNEL` to both the build env (`tasks/main.yml`)
  and `app.env.local.j2`, driven by a new `app_client_channel` group
  var (defaults to `"web"`). The Next.js api-client reads it at build
  time and sends it on every `POST /v1/reports` as the
  `X-Client-Channel` header; the FastAPI route uses that header to route
  `mobile` writes to MongoDB and `web` writes to DuckLake. Default
  `"web"` is correct for the VM, but a Capacitor mobile bundle off the
  same playbook MUST override or it will silently mis-route writes.

- **`roles/mcp_servers`** — new `tasks/http_units.yml` +
  `templates/mcp-http.service.j2` + `handlers/main.yml`. For every entry
  in `mcp_http_servers` (default `[]`), renders a hardened systemd unit
  that runs the server in FastMCP streamable-HTTP mode on
  `127.0.0.1:<port>` so nginx can proxy it as a Claude.ai custom
  connector. Pairs with the matching `location` block already in
  `roles/nginx/templates/onehealth.conf.j2`. Off by default.
- **`roles/mcp_servers/templates/claude.json.j2`** — moved the
  hard-coded `SMS_MODE: "mock"` to a new `sms_mode` group var; added an
  `NWS_USER_AGENT` env line for `nws-heatrisk-mcp` (the server's
  `.env.example` documents it as required).
- **`mcp/wearable-mcp/.env.example`** — added (was the only server
  without one). The empty-file path was previously handled by the
  template's default-branch fallback; now there's a clean per-server
  documented template. (Note: the prior phrasing here used literal
  Jinja `else`-tag syntax in backticks, which Jekyll's Liquid
  pre-processor parsed as a real tag and broke `deploy-jekyll.yml`
  on the post-EpiHack merge — see the hot-fix two commits down.)

- **`roles/ducklake`** + **`scripts/load_synthetic_observations.py`** —
  promoted the on-VM `/tmp/gen_synth.py` into the repo at
  `scripts/load_synthetic_observations.py` and added an opt-in
  `ducklake_load_synthetic_demo` toggle (defaults `false`) that runs it
  after the schema seed. Reproduces the 4,395-observation demo cohort
  with three intentional anomaly signals (Nogales febrile/rash, Lake
  Havasu City food-safety + GI, Portal animal die-off). Idempotent.

- **`roles/nginx`** — added a `/dashboard/` static-alias block (gated
  on a new `serve_dashboard` toggle, defaults `true`) so the
  signal-monitor at `dashboard/signals/` resolves on the live VM, not
  just on GitHub Pages.

- **`group_vars/all.yml`** — added: `app_client_channel`, `sms_mode`,
  `nws_user_agent`, `ducklake_load_synthetic_demo`, `serve_dashboard`.

### Known gaps (tracked, intentionally out of scope for archive)

- Only `vectorsurv-mcp` honors `FASTMCP_HOST` / `FASTMCP_PORT` /
  `FASTMCP_STREAMABLE_HTTP_PATH` in its `__main__.py`. The other ten
  MCP servers will need the same shim before they can be exposed as
  Claude.ai custom connectors. The Ansible side now ships the
  infrastructure (the systemd template + the nginx proxy block);
  the per-server shim is a repo change for revival.
- The live demo (`epihack-test.cis240692.projects.jetstream-cloud.org`)
  still terminates plain HTTP. Claude.ai custom connectors require
  HTTPS — flip `tls_enabled: true` and set `vault_tls_email` when DNS
  resolves to a host certbot can validate.

## New components

- **`roles/ducklake/`** — new role (runs after `mcp_servers`, before
  `fastapi`). Creates the Parquet data dir and seeds the DuckLake catalog from
  `schema/` via `files/bootstrap_ducklake.py`. Idempotent (skips if
  `kg.node` is already populated). See the DuckLake section in `README.md`.
- **`agents/src/onehealth_agents/kg_writer.py`** — the Phase-06.2 intake
  write-path. Each report submitted to `POST /v1/reports` is persisted as a
  `kg.node('observation')` + `kg.property` rows + a `kg.agent_run` intake row
  in DuckLake. Privacy-preserving: free-text `notes` and the `claim_token` are
  stored only as SHA-256 digests; coarse location is stored as-is. Also serves
  the `GET /v1/reports/{id}` status read-back with claim-token verification.
- **`plan/08-mobile-ux-revamp.md`** — plan to port the Elbaraaa/OneHealth
  mobile UX onto `app/` while keeping this backend.

## Ansible role fixes

- **`roles/python`** — uv was installed into `/root/.local/bin` and symlinked
  into `/usr/local/bin`; the unprivileged `onehealth` user got `EACCES`
  executing it (root home is `0700`). Now installs the real binary into
  `/usr/local/bin` via `UV_INSTALL_DIR`. Added `executable: /bin/bash` so
  `set -euo pipefail` works (the `shell` module defaults to dash).
- **`roles/claude_code`, `roles/mcp_servers`** — same `pipefail`-under-dash
  fix: `executable: /bin/bash` on the `set -euo pipefail` shell tasks. Also
  fixed a YAML parse error in the mcp_servers smoke task (free-form → dict
  `cmd:` form).
- **`roles/repo`** — added a **local working-copy mode**: when
  `onehealth_repo_url` is a local path (`/...` or `file://`), rsync the tree
  into `/srv/onehealth/epihack-2026` (excluding `.git`, `node_modules`,
  `.venv`, `out/`, etc.) instead of `git clone`; remote URLs still clone.
  `git` mode now uses `force: true` (build steps regenerate tracked lockfiles,
  dirtying the tree). Both modes `notify: Restart fastapi` so new source
  reaches the running API.
- **`roles/app`** — `npm ci` requires a committed lockfile, which the repo
  doesn't ship, so it failed on every fresh clone. Now detects the lockfile
  and falls back to `npm install` when absent.
- **`roles/fastapi`** —
  - dropped the `creates:` guard on `uv sync` so dependency changes (e.g. the
    new `duckdb`) are picked up on re-deploy; it now notifies `Restart fastapi`;
  - creates the DuckDB extension home (`ducklake_duckdb_home`) and
    pre-installs the `ducklake`+`postgres` extensions for the API's exact
    duckdb version (no network needed at request time);
  - the systemd unit now sets `Environment=HOME={{ ducklake_duckdb_home }}`
    (DuckDB needs a writable `$HOME/.duckdb`; `ProtectHome=true` hides `/home`)
    and widens `ReadWritePaths` to the repo + the DuckLake data dir + the
    DuckDB home.
- **`roles/mcp_servers` (`claude.json.j2`)** —
  - `knowledge-graph-mcp` now gets `KG_DUCKLAKE_URI`, `KG_DUCKLAKE_DATA_PATH`,
    `KG_SCHEMA_PATH` (the old `KG_DUCKDB_PATH` was never read by the loader);
  - **module-name override map** (`mcp_modules`) so `211-az-mcp` launches as
    `python -m az211_mcp` (a module name can't start with a digit);
  - **`INAT_USER_AGENT`** set for `inaturalist-mcp`, which refuses to start
    without it.
- **`playbook.yml`** — removed `group_vars/all.yml` from `vars_files` (it is
  auto-loaded; listing it under `vars_files` outranks inventory host vars and
  silently clobbered the localhost overrides). Only `all.vault.yml` is loaded
  via `vars_files` now. Added the `ducklake` role to the run order.
- **`group_vars/all.yml`** — added `ducklake_data_path`, `ducklake_uri`,
  `ducklake_duckdb_home`, `kg_mcp_venv_python`, `mcp_modules`,
  `inat_user_agent`.
- **`inventory.yml`** — localhost host-level overrides (incl. a local
  `onehealth_repo_url`), with a note explaining the host-vs-group precedence.

## Application / source fixes (required for the deploy to build & run)

- **`api/openapi.yaml`** — fixed a YAML typo (`coarse_location:{` → a space
  before the flow map) that broke `npm run gen:api`. The spec is the source of
  truth, so this is fixed upstream rather than worked around.
- **`app/package.json`** — pinned `eslint` to `^8.57.0`; `^9` conflicts with
  `eslint-config-next@14`'s peer range and broke `npm install`.
- **`agents/pyproject.toml`** — added `duckdb>=1.5` (the DuckLake write-path
  and audit sink need it; it was only present in the kg-mcp venv before).
- **`agents/src/onehealth_agents/audit.py`** — `DuckLakeAuditSink` now opens
  in-memory DuckDB and `ATTACH`es the DuckLake catalog instead of calling
  `duckdb.connect(uri)` (which treated the `ducklake:` URI as a file path).
- **`agents/src/onehealth_agents/kg_writer.py`** — no `ON CONFLICT` clauses
  (DuckLake tables carry no PK/UNIQUE constraint; UUID PKs make conflicts moot).
- **`agents/src/onehealth_agents/api/routes/reports.py`** — `_run_agent_chain`
  now persists via `kg_writer` (was a synthetic-ack stub); `GET` verifies the
  claim token against the stored digest.

## Verification (post-deploy)

- Playbook: `failed=0`, all eleven roles.
- Services: `onehealth-api`, `nginx`, `postgresql` active; `GET /v1/healthz`
  200; nginx serves the app; `/api` proxies to the backend.
- DuckLake: a live report POST increments `kg.node('observation')` and
  `kg.agent_run`, advances `ducklake_snapshots`, and
  `... AT (VERSION => N)` returns the prior state (time-travel).
- MCP: 11/11 servers respond to MCP `initialize` over stdio.
