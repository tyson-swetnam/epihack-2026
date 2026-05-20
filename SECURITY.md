---
title: "Security policy"
---

# Security policy

This repository contains a working participatory-surveillance stack
for One Health observations in Arizona. Bugs that affect the
**confidentiality of observations**, the **integrity of
cluster-detection signals**, or the **availability of agency-side
dashboards during an active outbreak** are treated as security
incidents — not just functional bugs.

## Reporting a vulnerability

> **Placeholder private channel — to be replaced at community handoff.**
> The maintaining team will publish a real private disclosure address
> (a `security@` mailbox and/or a [GitHub Security Advisory
> private-disclosure
> link](https://docs.github.com/en/code-security/security-advisories/working-with-repository-security-advisories/configuring-private-vulnerability-reporting-for-a-repository))
> as part of the v1.0 handoff. Until then, please use the temporary
> channel below.

**Temporary disclosure address (handoff placeholder):**
`epihack-security@arizona.edu` *(placeholder — confirm with the
maintainer before sending sensitive material)*.

When reporting, please include:

* A description of the vulnerability and the impacted file(s) /
  endpoint(s).
* A proof-of-concept or reproduction steps, if you have one.
* The MCP server, agent, or schema path involved.
* Whether the report covers a live deployment or only the public
  repo state.
* Your preferred attribution string (or "anonymous").

**Do not** open a public GitHub issue for security reports. Please
allow up to **10 business days** for an initial response and **90
days** for a coordinated fix before public disclosure. The standing
review board (see [GOVERNANCE.md](./GOVERNANCE.md)) is looped in on
any report that touches tribal data; ITCA-TEC is notified directly
on those.

## Scope

In scope:

* Anything under [`mcp/`](./mcp/), [`agents/`](./agents/),
  [`schema/`](./schema/), [`app/`](./app/), [`dashboard/`](./dashboard/),
  [`today/`](./today/), and the deploy config under [`ansible/`](./ansible/).
* The dual-sink report write path: the FastAPI `/v1/reports` endpoint,
  the DuckLake (`kg_writer`) and MongoDB (`mongo_writer`) sinks, and the
  `mongo_to_ducklake` sync (see [`plan/09`](./plan/09-mobile-datastore.md)).
* Documented integrations (VectorSurv, NWS, MAG HRN, USGS WHISPers,
  iNaturalist, the ADHS / 211 / Great AZ Tick Check mock backends).
* The static site served via GitHub Pages.

Out of scope:

* Upstream agency APIs themselves (report those to the agency
  directly).
* The unpkg / openfreemap / OpenStreetMap tile servers (report
  upstream).
* Issues that require physical access to a user device or social
  engineering of a known committer.

## Threat model

These are the five threat classes the repo is designed against, with
the mitigations already in place and the gaps that remain.

### 1. Re-identification of suppressed observations

**Threat.** An analyst or external party with access to a dashboard
or aggregated feed reverse-engineers individual line data — most
acutely for observations on tribal land or for low-incidence
pathogens (hantavirus, plague) where a single cell can identify a
household.

**Mitigations in place.**

* Row-level tribal-data suppression is enforced inside the Validation
  Agent (`agents/src/onehealth_agents/validation.py`) at *write
  time*, before any row reaches the kg.
* `consent_profile` defaults to `suppress` for every new `tribe.*`
  node until an MOU attaches an opt-in (see
  [GOVERNANCE.md](./GOVERNANCE.md)).
* Cluster detection operates at ZCTA-week (VBD) or ZCTA-2h (Heat)
  buckets with explicit `k` and `theta` floors; see
  [`plan/CLUSTER-CALIBRATION.md`](./plan/CLUSTER-CALIBRATION.md).
* Dashboards apply tribal suppression *before* aggregation so cell
  counts cannot be back-computed from neighbouring cells.
* The mobile **MongoDB sink stores the same coarse fields as DuckLake**
  (ZIP or 1 km grid only) and digests for free-text/claim tokens — the
  re-identification surface is identical across channels because
  coarsening and suppression run *before* the sink is chosen.

### 2. MCP-server credential leakage

**Threat.** An API key, agency token, or OAuth refresh credential
for VectorSurv / Twilio / a private agency endpoint is leaked via a
log, an `agent_run` row, a stack trace, a public bug report, or a
committed `.env`.

**Mitigations in place.**

* All MCP servers read credentials from `os.environ`. No tokens in
  source. Each server's `.env.example` lists the required vars.
* `.env` files are `.gitignore`d (see `.gitignore` at the repo root).
* `agent_run` audit rows store input/output **SHA-256 digests**, not
  raw payloads or headers.
* Credentials are per-process and per-MCP-server, not shared across
  the orchestrator.
* The MongoDB sink reads `MONGODB_URI` from the environment
  (vault-managed at deploy time); when it is unset the writer falls back
  to an in-memory `mongomock` client, so dev and tests need no real
  credential. Self-hosted MongoDB is bound to `127.0.0.1` with
  authorization enabled and an app user created from the vault password.

### 3. Malicious agency-token reuse

**Threat.** A legitimate agency-side credential is reused outside its
intended scope — for example, an ADHS token used to write into a
tribal-jurisdiction observation, or a CHW field-app token used to
read data outside that CHW's caseload.

**Mitigations in place.**

* The Validation Agent is the single write-enforcement point and
  checks `consent_profile` on every write regardless of caller
  identity — and it runs *before* the per-channel sink (DuckLake or
  MongoDB) is selected, so neither channel can bypass it.
* The `knowledge-graph-mcp` SQL escape-hatch (`kg_sql`) is **SELECT-only**:
  the server parses the SQL and rejects any non-SELECT keyword
  before execution. Do not weaken this filter.
* Agent-to-MCP calls are prefix-scoped (`vectorsurv_*` only reaches
  vectorsurv-mcp, etc.), so a misconfigured route cannot leak across
  servers.

### 4. Prompt-injection of agency-side dashboards

**Threat.** A user-controlled field on an observation (free-text
symptom note, species hint, address) contains LLM prompt-injection
content that, when summarised on an agency dashboard or by the
Triage Agent, causes the LLM to disclose data, change its triage
class, or call a different MCP tool.

**Mitigations in place.**

* The **Triage Agent uses deterministic enumeration** — the LLM can
  only choose from a small fixed set of triage classes (see
  [`plan/03-agentic-architecture.md`](./plan/03-agentic-architecture.md));
  free-form triage output is rejected by the orchestrator before
  reaching downstream agents. This is the single most important
  injection mitigation in the stack.
* Heat scoring uses the pinned `HEAT_SCORE_TABLE` (also in plan/03),
  not free-form LLM scoring.
* Dashboard summaries (`dashboard/`, `today/`) render only
  pre-aggregated fields from the kg, not raw observation text.
* All free-text fields are stored as `value_text` and shown only with
  HTML-escaping in vanilla DOM updates (no `innerHTML` shortcuts).

### 5. Cluster-detection false positives causing reactive over-response

**Threat.** A miscalibrated detector fires on noise, triggering an
emergency response (cooling-center surge dispatch, mosquito-control
intervention, public alert) that disrupts services without medical
justification — and erodes agency trust in the system.

**Mitigations in place.**

* Two-tier detector (deterministic Poisson scan + Bayesian
  refinement) with both count floors (`k`) and posterior thresholds.
  See [`plan/CLUSTER-CALIBRATION.md`](./plan/CLUSTER-CALIBRATION.md).
* Calibrated against 14 historical AZ outbreaks with explicit known
  misses documented; **zero false alerts** across 4,114 simulated
  null agency-weeks.
* Every `ClusterAlert` carries audit fields (`tier1_score`,
  `tier2_posterior`, `rule_tripped`, `historical_match`) so an
  analyst can decompose every fire.
* VBD and Heat scored separately; a heat wave does not raise the bar
  for a coincident VBD cluster.

## Known security gaps

We document gaps because hiding them does not make them go away. If
you can close any of these, please open a PR.

* **Single-case high-CFR alert layer missing.** The current detector
  cannot catch single-index-case outbreaks of high-case-fatality
  pathogens (plague, hantavirus, viral haemorrhagic fevers). The
  `coconino_plague_2025` historical case is the canonical example.
  *Mitigation gap:* no automated escalation today for `Y. pestis`,
  `Sin Nombre`, or similar pathogens at `n=1`. Planned for Phase 4.
* **Calibration with single seed.** Cluster-detection metrics in
  `plan/CLUSTER-CALIBRATION.md` come from a single fixed RNG seed.
  A statistically robust calibration should sweep ~100 seeds.
* **No private vulnerability-disclosure channel published.** The
  address above is a placeholder; the maintainers will replace it at
  v1.0 handoff with a published `security@` mailbox and a GitHub
  Security Advisory configuration.
* **Mock backends not authenticated.** The mock backends for ADHS,
  211 Arizona, MAG supply, Great AZ Tick Check, and the SMS gateway
  ship with no auth — they are explicitly marked "mock-only" and
  must be replaced with authenticated clients before any production
  rollout. Reviewers will reject PRs that route real observations
  through a mock backend without an env-var override.
* **No CSP on the static site.** `index.html` and the per-section
  pages load MapLibre and Cytoscape from unpkg without a Content
  Security Policy. A future PR should add a CSP header (via Jekyll
  `_includes`) restricting script sources to unpkg + self.
* **No SBOM published.** We list third-party dependencies in
  [`NOTICE`](./NOTICE) but do not yet ship a CycloneDX SBOM. Planned.
* **`agent_run` digest collisions.** SHA-256 of canonicalized JSON
  prevents accidental disclosure but does not prevent a
  determined attacker who has the raw observation from confirming a
  match. This is the intended threat model (audit, not
  encryption-at-rest) but worth being explicit about.
* **Wearable readings are mock-only today.** The `wearable-mcp`
  server is mock-by-default. The production privacy model
  (on-device-only with explicit per-metric consent) is in the README
  but not yet enforced at the wire level.
* **Tribal-data suppression has no formal audit.** Plan-02 requires a
  quarterly tabletop review; we have not yet scheduled the first
  one. ITCA-TEC notification on tribal-touching reports is policy,
  not yet automation.
* **Server-side EXIF check is a placeholder.** On the write-path branch
  the server-side `_photo_has_exif_gps` defence-in-depth check
  (`agents/.../api/routes/reports.py`) currently returns `False`; the
  **client-side strip** (`app/src/lib/exif-stripper.ts`) is the only
  active control today. The server-side check and the full
  Triage/Enrichment agent chain land in a later phase
  (plan/07, plan/09); until then the contract's `photo_exif_gps_present`
  (422) rejection is specified but not yet enforced at the wire.
* **Mobile→DuckLake sync is eventually consistent.** Mobile-channel
  reports persist to MongoDB immediately but reach DuckLake — and thus
  the agents, MCP analytics, and cluster detection — only on the next
  `mongo_to_ducklake` tick. Cluster signals from mobile-only reports
  therefore lag by the timer interval. The job is idempotent on
  `observation_id`, so re-runs are safe; a change-stream consumer is the
  lower-latency upgrade path.
* **Offline queue retains report JSON on-device.** The app's offline
  retry queue (`app/src/lib/offline-queue.ts`) parks the
  already-coarsened, EXIF-free report payload in the device's
  `localStorage` until it flushes on reconnect, and queued payloads
  survive app restarts. That payload includes any free-text `notes` in
  plaintext (the server digests them only on receipt); photos are not
  queued. On a shared or compromised device the cache is readable until
  the report lands.
* **MongoDB write-path is new.** Production deployments must set a real
  `MONGODB_URI` (vault-managed); the in-memory `mongomock` fallback
  persists nothing across restarts and must never back a live deployment.

## Disclosure timeline

1. **T+0:** report received.
2. **T+10 business days:** initial acknowledgement, severity
   assessment, scope decision (in-scope / out-of-scope).
3. **T+30 days:** patch in draft PR or workaround documented.
4. **T+90 days:** coordinated public disclosure (GitHub Security
   Advisory + a `CHANGELOG.md` entry).

We will credit reporters in the advisory and the changelog unless
asked otherwise.
