---
title: AZ One Health Sentinel — Ansible deployment
---

# `ansible/` — Ansible playbook for AZ One Health Sentinel

One command turns a fresh Ubuntu 24.04 VM into a running deployment
of Claude Code + every MCP server in [`../mcp/`](../mcp/) + the
FastAPI backend + the Next.js reporting app + Postgres for the
DuckLake catalog.

For an overview (VM sizing, DNS, providers, operations runbook) see
[`../deploy/README.md`](../deploy/README.md). This file covers the
playbook itself.

## Run it

```bash
cd ansible
cp inventory.example.yml inventory.yml
cp group_vars/all.vault.example.yml group_vars/all.vault.yml
$EDITOR inventory.yml group_vars/all.vault.yml
ansible-vault encrypt group_vars/all.vault.yml
ansible-galaxy install -r requirements.yml
ansible-playbook -i inventory.yml playbook.yml --ask-vault-pass
```

10–15 minutes later: a working deployment.

### Localhost (single-box) deployment

To deploy onto the machine you're sitting at (no remote VM), the
`inventory.yml` here points at `127.0.0.1` with `ansible_connection: local`
and overrides a few host vars. Two things differ from a remote run:

- **Source is rsynced from the local working copy, not cloned from
  GitHub.** Set `onehealth_repo_url` to a local path (e.g.
  `/home/you/epihack-2026`) as a *host* var; the `repo` role then rsyncs
  the working tree (uncommitted edits included) into
  `/srv/onehealth/epihack-2026`, excluding build artifacts. A `https://`
  or `git@` URL still triggers the git-clone path.
- **Localhost overrides must be HOST vars, not group vars.** The play
  auto-loads `group_vars/all.yml`; if you put overrides under a group's
  inline `vars:` they rank *below* `group_vars/all` and get clobbered.
  Put `onehealth_fqdn`, `fastapi_auth_mock`, `app_api_base`, etc. under
  the host entry. (The play loads only `all.vault.yml` via `vars_files`,
  never `all.yml`, precisely so host overrides win.)

```bash
# vault may be plaintext for a throwaway local box (skip --ask-vault-pass):
ansible-playbook -i inventory.yml playbook.yml
```

## Layout

```
ansible/
  ansible.cfg               Inventory pointer + roles_path + vault prompt
  inventory.example.yml     Host + ssh user; copy → inventory.yml
  playbook.yml              The entry-point; one play, eleven roles in order
  requirements.yml          Ansible Galaxy collections (community.postgresql, …)
  group_vars/
    all.yml                 Non-secret defaults — edit in place is fine
    all.vault.example.yml   Secret template — copy + encrypt as all.vault.yml
  roles/
    common/                 base apt packages, deploy user, ufw, fail2ban, swap
    node/                   Node.js 20 LTS via NodeSource
    python/                 Python 3.12 + uv
    postgres/               PostgreSQL 16 + onehealth DB + role
    repo/                   put source at /srv/onehealth/epihack-2026 (git clone OR local rsync)
    claude_code/            `npm i -g @anthropic-ai/claude-code` + ~/.claude/settings.json
    mcp_servers/            `uv sync` each mcp/<name>-mcp/; write ~/.claude.json
    ducklake/               seed the DuckLake catalog (Postgres + local Parquet) from schema/
    fastapi/                uvicorn systemd unit for onehealth_agents.api:app
    app/                    npm install + npm run gen:api + npm run build (static export)
    nginx/                  reverse-proxy /api/ → :8000, serve /app/ → static export
```

## Roles in order

The playbook runs roles sequentially because each step depends on
the last. Ansible runs are idempotent — re-running the playbook
after a `git pull` updates the repo, rebuilds the app, and restarts
the services without touching anything else.

| # | Role | Tags |
|---|---|---|
| 1 | common | `common` |
| 2 | node | `node` |
| 3 | python | `python` |
| 4 | postgres | `postgres`, `db` |
| 5 | repo | `repo` |
| 6 | claude_code | `claude_code`, `claude` |
| 7 | mcp_servers | `mcp_servers`, `mcp` |
| 8 | ducklake | `ducklake`, `kg`, `db` |
| 9 | fastapi | `fastapi`, `api` |
| 10 | app | `app`, `frontend` |
| 11 | nginx | `nginx`, `web` |

Tag a subset to run just one step, e.g.:

```bash
# Just rebuild + redeploy the Next.js app after a code change:
ansible-playbook -i inventory.yml playbook.yml --tags repo,app

# Just rotate the Anthropic API key:
ansible-playbook -i inventory.yml playbook.yml --tags claude_code
```

## Vault

`group_vars/all.vault.yml` carries every secret the playbook needs:

- `vault_anthropic_api_key` — for Claude Code on the VM
- `vault_postgres_password` — onehealth DB role
- `vault_supabase_jwt_secret` (or `vault_supabase_url`) — for the
  FastAPI backend's JWT validation
- `vault_tls_email` — Let's Encrypt registration email
- Per-MCP-server credentials (VectorSurv username/password, etc.)

The `.example` file ships every key with an empty value so a new
deployer knows what to fill in. Encrypt the real file with
`ansible-vault encrypt group_vars/all.vault.yml` before committing
to a private fork.

## Testing the playbook

The fastest loop is a throwaway local VM (e.g. Multipass on macOS,
Vagrant + libvirt on Linux, or a $5/month DigitalOcean droplet you
destroy after each smoke test). Multipass example:

```bash
multipass launch 24.04 -n onehealth-test -c 4 -m 8G -d 40G
multipass info onehealth-test           # grab the IP
# add the IP to inventory.yml as ansible_host
ansible-playbook -i inventory.yml playbook.yml --ask-vault-pass
multipass shell onehealth-test          # poke around
multipass delete onehealth-test && multipass purge
```

The playbook is **not** idempotent on the *first* run if it gets
interrupted mid-way (e.g. SSH drops during `npm ci`). Just re-run
and Ansible will pick up where it left off.

## DuckLake knowledge graph

The `ducklake` role (runs after `mcp_servers`, before `fastapi`) brings up
the knowledge-graph lakehouse so user reports are logged durably with
time-travel versioning:

- **Catalog:** a DuckLake catalog in the epihack Postgres DB
  (`ducklake:postgres:dbname=epihack ...`, the `ducklake_uri` var).
- **Data:** Parquet files under `ducklake_data_path`
  (`/srv/onehealth/ducklake-data`).
- **Seeding:** `roles/ducklake/files/bootstrap_ducklake.py` loads the
  `schema/*.sql` + `schema/deep/*.sql` into an in-memory DuckDB (which
  supports PK/FK), then **CTAS-copies** every table + view into DuckLake.
  This is required because DuckLake does **not** support PRIMARY KEY /
  UNIQUE / FK constraints or indexes — a plain `.read schema.sql` against
  DuckLake fails. The seed is idempotent (skips if `kg.node` is populated).
- **Runtime readers/writers:** `knowledge-graph-mcp` reads the catalog
  (`KG_DUCKLAKE_URI` in `~/.claude.json`); the FastAPI reports write-path
  (`agents/.../kg_writer.py`) and the audit sink write to it
  (`KG_DUCKLAKE_URI` + `KG_DUCKLAKE_DATA_PATH` in the API env). The API
  service needs `duckdb` (an `agents/` dependency) and a writable DuckDB
  extension home — the `fastapi` role sets `HOME={{ ducklake_duckdb_home }}`
  in the unit, widens `ReadWritePaths`, and pre-installs the
  `ducklake`+`postgres` extensions for the API's duckdb version.

Verify time-travel after a deploy:

```sql
-- in duckdb, attached as epihack:
SELECT max(snapshot_id) FROM ducklake_snapshots('epihack');
SELECT count(*) FROM kg.node AT (VERSION => 22);   -- historical read
```

## Caveats

- **Supabase project is external.** The playbook configures the VM
  to *talk to* Supabase via the URL + JWT secret in the vault. It
  does not create the Supabase project, configure OAuth providers,
  or seed any tables. See [`../plan/07-auth.md`](../plan/07-auth.md)
  for the manual Supabase setup steps.
- **DuckLake is provisioned locally; object storage is optional.** The
  `ducklake` role attaches a DuckLake catalog in the epihack Postgres DB
  and seeds the `schema/` knowledge graph into it, with the Parquet data
  files under `{{ ducklake_data_path }}` (default
  `/srv/onehealth/ducklake-data`) on local disk — no S3 required. For a
  production multi-node lakehouse you can repoint the data path at
  S3 / R2 instead. See the `DuckLake` section below.
- **OAuth callback domain.** The Supabase Auth dashboard needs the
  VM's public hostname in its allow-list before the OAuth dance
  works end-to-end. Add it after DNS resolves.
