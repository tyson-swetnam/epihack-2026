---
title: Deploying AZ One Health Sentinel to a VM
---

# `deploy/` — VM deployment for AZ One Health Sentinel

This document covers everything that's needed to take a fresh
Ubuntu 24.04 VM from `apt update` to a running deployment of:

- **Claude Code CLI** (with all MCP servers registered)
- **All eleven MCP servers** under [`mcp/`](../mcp/) (vectorsurv-mcp,
  knowledge-graph-mcp, great-az-tick-check-mcp, nws-heatrisk-mcp,
  mag-hrn-mcp, adhs-mcp, 211-az-mcp, whispers-mcp, inaturalist-mcp,
  sms-entry-mcp, wearable-mcp)
- **FastAPI backend** at `agents/src/onehealth_agents/api/` running
  under uvicorn as a `systemd` unit
- **Next.js reporting app** at [`app/`](../app/), statically exported
  and served by **nginx** with optional Let's Encrypt TLS
- **PostgreSQL** for the DuckLake catalog
  ([`schema/`](../schema/))

The provisioning is fully automated via the Ansible playbook in
[`../ansible/`](../ansible/) — run one command, get a working host.

## VM sizing

| Profile | Use case | vCPU | RAM | Disk |
|---|---|---|---|---|
| **Dev / demo** | One person clicking through the app | 2 | 4 GB | 40 GB |
| **Pilot** | One county + 10 CHWs | 4 | 8 GB | 100 GB |
| **Phase 3** | Maricopa + Coconino + agency dashboards | 8 | 16 GB | 250 GB |
| **Statewide** | Phase 4 — 15 counties | 16 | 32 GB | 500 GB + S3 |

Notes:
- Postgres needs the disk to be fast (NVMe). The Parquet data files
  for DuckLake can live on cheaper storage (e.g. S3 / R2).
- Memory pressure is dominated by Postgres + uvicorn workers + the
  MCP server processes. Each MCP server is ~30 MB resident; 11
  servers ≈ 350 MB before the agent chain runs.
- The Next.js static export is tiny (single-digit MB).

## Supported OS

- **Ubuntu 24.04 LTS** (default; tested)
- **Ubuntu 22.04 LTS** (works; Node and Python paths differ slightly)
- **Debian 12** (untested; should work — same Ansible roles)

Other distributions are not supported by the playbook; the manual
steps below should translate.

## Prerequisites

On your **workstation** (not the VM):

- Ansible 2.16+
- `ssh` access to the VM as a user with `sudo`
- (Optional) Cloud provider CLI if you want to spin up the VM
  from this repo — see [Cloud provider templates](#cloud-provider-templates).

On the **VM**:

- A fresh Ubuntu 24.04 install
- A non-root user that can `sudo`
- SSH-key authentication (password auth disabled is a hard requirement
  for any non-dev deployment)

## Quick start (Ansible)

```bash
# 1. From your workstation, clone the repo
git clone https://github.com/tyson-swetnam/epihack-2026.git
cd epihack-2026/ansible

# 2. Copy the example inventory and edit it
cp inventory.example.yml inventory.yml
$EDITOR inventory.yml          # set ansible_host + ansible_user

# 3. Copy the example vars and fill in secrets
cp group_vars/all.yml          group_vars/all.local.yml
cp group_vars/all.vault.example.yml  group_vars/all.vault.yml
$EDITOR group_vars/all.vault.yml
ansible-vault encrypt group_vars/all.vault.yml

# 4. Install required Ansible Galaxy collections
ansible-galaxy install -r requirements.yml

# 5. Run the playbook end-to-end
ansible-playbook -i inventory.yml playbook.yml --ask-vault-pass
```

About 10–15 minutes later, the VM has:

- `claude` on the deploy user's `$PATH`, with all eleven MCP servers
  registered (`claude mcp list` shows them).
- `https://<your-domain>/` serving the Next.js app.
- `https://<your-domain>/api/v1/healthz` returning `{"status":"ok"}`.
- `psql -U onehealth epihack` working.
- All four `systemd` units enabled: `onehealth-api`, `nginx`,
  `postgresql`, `onehealth-mcp@<name>` (one per MCP server, if
  long-lived streamable-http transport is enabled).

## What the playbook does, role by role

| Role | What |
|---|---|
| `common` | Base packages (git, curl, ca-certs, jq, …), the `onehealth` deploy user + SSH key, UFW firewall (22, 80, 443), fail2ban on SSH, swap if missing, timezone. |
| `node` | Node.js 20 LTS via NodeSource, npm global prefix at `~/.npm-global` so the deploy user can install packages without sudo. |
| `python` | Python 3.11+ (Ubuntu 24.04 ships 3.12), the `uv` package manager. |
| `postgres` | PostgreSQL 16, a `onehealth` database + role, pg_hba.conf for local trust + scram-sha-256 from app. |
| `repo` | Clone the EpiHack repo to `/srv/onehealth/epihack-2026`. Idempotent — re-runs pull. |
| `claude_code` | `npm install -g @anthropic-ai/claude-code` for the deploy user. Writes `~/.claude/settings.json` with project-default model + ANTHROPIC_API_KEY from the vault. |
| `mcp_servers` | `uv sync` each `mcp/<name>-mcp/`. Writes a `~/.claude.json` snippet registering each server via stdio. Optional: `systemd` units for streamable-http mode. |
| `fastapi` | uvicorn `systemd` unit running `onehealth_agents.api:app` on `127.0.0.1:8000`. Reads `SUPABASE_URL` / JWT-validation config from the vault. |
| `app` | `npm ci && npm run gen:api && npm run build` in `app/`. Static export lands in `app/out/`. |
| `nginx` | nginx reverse-proxies `/api/` → `127.0.0.1:8000`, serves `/` from the static export. Lets-Encrypt-ready via `certbot --nginx`. |

## DNS + TLS

Point an A record at the VM's public IP before running the playbook
(or run the playbook first and add the record afterwards). Once DNS
resolves, the `nginx` role can issue a Let's Encrypt cert:

```bash
ssh onehealth@your-host
sudo certbot --nginx -d sentinel.example.org
```

The playbook can also do this automatically when `tls_email` is set
in the vault and `tls_enabled: true` in `group_vars/all.yml`.

## Cloud provider templates

The playbook is provider-agnostic — any VM with SSH + sudo works.
For convenience, [`deploy/providers/`](./providers/) holds minimal
templates for the cloud the user happens to have:

| Provider | Template | Status |
|---|---|---|
| AWS EC2 (Ubuntu 24.04, t3.medium) | `providers/aws-ec2.md` | TODO |
| DigitalOcean Droplet | `providers/digitalocean.md` | TODO |
| Linode | `providers/linode.md` | TODO |
| OCI Always Free | `providers/oracle-cloud.md` | TODO |
| Self-host (bare metal / Proxmox) | `providers/self-host.md` | TODO |

Adding a provider template is a 5-minute job — feel free to drop
one as a PR.

## Manual install (no Ansible)

If you'd rather provision by hand, every step in the playbook is a
documented Ansible task. Read [`../ansible/roles/<name>/tasks/main.yml`](../ansible/)
in order: `common → node → python → postgres → repo → claude_code →
mcp_servers → fastapi → app → nginx`. Each task corresponds to one
shell command on the VM.

## Operations

| Task | How |
|---|---|
| **Re-deploy after a `git pull` on main** | `ansible-playbook -i inventory.yml playbook.yml --tags repo,fastapi,app` |
| **Rotate the Anthropic API key** | Update the value in `group_vars/all.vault.yml`, then `ansible-playbook ... --tags claude_code` |
| **Restart the FastAPI backend** | `systemctl restart onehealth-api` |
| **Tail logs** | `journalctl -u onehealth-api -f` |
| **Re-issue TLS cert** | `certbot renew` (cron-managed by default) |
| **Back up Postgres** | `pg_dump -U onehealth epihack \| gzip > backup-$(date +%F).sql.gz`. Snapshot the DuckLake Parquet object store separately. |

## Cross-links

- [`../ansible/`](../ansible/) — the Ansible playbook.
- [`../plan/06-mobile-app.md`](../plan/06-mobile-app.md) — the
  privacy contract the app enforces.
- [`../plan/07-auth.md`](../plan/07-auth.md) — Supabase Auth
  integration; the VM holds the JWT-validation config, not the
  Supabase project itself.
- [`../api/openapi.yaml`](../api/openapi.yaml) — the HTTP contract
  the FastAPI backend serves.
