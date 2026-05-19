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

## Layout

```
ansible/
  ansible.cfg               Inventory pointer + roles_path + vault prompt
  inventory.example.yml     Host + ssh user; copy → inventory.yml
  playbook.yml              The entry-point; one play, ten roles in order
  requirements.yml          Ansible Galaxy collections (community.postgresql, …)
  group_vars/
    all.yml                 Non-secret defaults — edit in place is fine
    all.vault.example.yml   Secret template — copy + encrypt as all.vault.yml
  roles/
    common/                 base apt packages, deploy user, ufw, fail2ban, swap
    node/                   Node.js 20 LTS via NodeSource
    python/                 Python 3.12 + uv
    postgres/               PostgreSQL 16 + onehealth DB + role
    repo/                   clone the repo to /srv/onehealth/epihack-2026
    claude_code/            `npm i -g @anthropic-ai/claude-code` + ~/.claude/settings.json
    mcp_servers/            `uv sync` each mcp/<name>-mcp/; write ~/.claude.json
    fastapi/                uvicorn systemd unit for onehealth_agents.api:app
    app/                    npm ci + npm run gen:api + npm run build (static export)
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
| 8 | fastapi | `fastapi`, `api` |
| 9 | app | `app`, `frontend` |
| 10 | nginx | `nginx`, `web` |

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

## Caveats

- **Supabase project is external.** The playbook configures the VM
  to *talk to* Supabase via the URL + JWT secret in the vault. It
  does not create the Supabase project, configure OAuth providers,
  or seed any tables. See [`../plan/07-auth.md`](../plan/07-auth.md)
  for the manual Supabase setup steps.
- **DuckLake Parquet storage is external.** Postgres holds the
  catalog; the actual Parquet files live in S3 / R2 / a local path,
  configured via the `DUCKLAKE_DATA_PATH` env var in
  `group_vars/all.yml`. The playbook does not provision S3.
- **OAuth callback domain.** The Supabase Auth dashboard needs the
  VM's public hostname in its allow-list before the OAuth dance
  works end-to-end. Add it after DNS resolves.
