---
title: "Federated cluster detection (Phase 4 prototype)"
---

# Federated cluster detection

A Phase-4 deliverable from
[`plan/05-roadmap.md`](./05-roadmap.md): let tribal and agency
partners contribute to the state-wide
[Cluster Detection Agent](./03-agentic-architecture.md#7-cluster-detection-agent)
**without releasing line-level observations**. Each site computes
local sufficient statistics; the coordinator runs the Tier-1 + Tier-2
Poisson scan on the aggregate. The math is identical to a centralised
scan because the scan statistic is a function of bucket counts alone,
so summing per-bucket counts across sites is equivalent to pooling
the underlying line list -- *without any line list ever leaving a
site*.

The reference implementation is in
[`agents/src/onehealth_agents/federated.py`](../agents/src/onehealth_agents/federated.py)
and is exercised by
[`agents/tests/test_federated.py`](../agents/tests/test_federated.py)
against a synthesised four-site (ITCA-TEC, Coconino HHS, MCDPH, AZGFD)
replay of the 2021 Maricopa WNV outbreak.

## Protocol

```
                              ┌──────────────────────────────┐
                              │   Each participating site    │
                              │   (ITCA-TEC, MCDPH, Coconino │
                              │    HHS, AZGFD, ...)          │
                              └──────────────┬───────────────┘
                                             │
       LocalSiteAggregator(site_id).aggregate(observations, vertical, now)
                                             │
                                             ▼
                      ┌──────────────────────────────────────┐
                      │     SufficientStatistics payload      │
                      │  ┌────────────────────────────────┐  │
                      │  │ site_id_hash (SHA-256, salt'd) │  │
                      │  │ vertical, bucket {'week','2h'} │  │
                      │  │ window_start, window_end       │  │
                      │  │ cells: [{zcta, bucket_key,     │  │
                      │  │          count, pathogen_tally}]│ │
                      │  │ active_zctas: [...]            │  │
                      │  │ baseline_total, baseline_days  │  │
                      │  │ [optional] dp_epsilon          │  │
                      │  │ [optional] Ed25519 signature   │  │
                      │  └────────────────────────────────┘  │
                      └──────────────┬───────────────────────┘
                                     │ (HTTPS, mTLS recommended)
                                     ▼
        ┌────────────────────────────────────────────────────────┐
        │  FederatedScanCoordinator.detect(payloads, now=...)    │
        │  1. verify_signed() against trusted_pubkeys (optional) │
        │  2. assert uniform vertical + bucket across payloads   │
        │  3. sum per-(zcta, bucket_key) counts; sum baselines   │
        │  4. reconstruct minimal synthetic observation set      │
        │  5. delegate to ClusterDetectionAgent.run(synth, now)  │
        │  6. retag spatial alerts as cluster_kind='federated'   │
        │     and attach contributing_sites=[hashed_site_ids]    │
        └────────────────────────────────────────────────────────┘
```

The payload is a typed pydantic model with a strict invariant:
**no `Observation` reference is reachable from any field**. The
aggregator is the single chokepoint that enforces it.
`test_federated.py::test_sufficient_statistics_payload_contains_no_observation_reference`
walks every reference inside a payload and asserts the property.

## Why it's safe

* **Only aggregates leave the site.** The wire payload carries
  per-(ZCTA, bucket) counts, a hashed site identifier, and the
  trailing-baseline total. No row-level fields, no PII, no free
  text, no geometries finer than a ZCTA.
* **Cryptographic provenance.** Each payload can be signed with the
  site's Ed25519 private key over the canonical-JSON form of the
  payload (with `signature` + `site_pubkey` cleared). The
  coordinator verifies against a registered public key per
  `site_id_hash`; verification failure throws.
* **Tamper detection.** Re-running the canonical-JSON serialisation
  on the receiving side and re-verifying against the site's public
  key detects any in-flight mutation (count bumps, ZCTA swaps,
  window shifts). Covered by
  `test_signed_statistics_verify_and_tamper_detection` and
  `test_coordinator_rejects_bad_signature`.
* **Vertical scoping preserved.** The aggregator applies the same
  `Vertical.VBD` / `Vertical.HEAT` / `Vertical.BOTH` rules as the
  centralised detector before bucketing, so a federated round never
  accidentally mixes verticals (Plan 03 rule).
* **Tribal-sovereignty defaults.** Sites can choose to publish only
  county-coarsened ZCTA labels (e.g. by remapping `cells[].zcta` to
  the centroid ZCTA of the county) before aggregation. Combined
  with the row-level suppression in
  [`agents/src/onehealth_agents/validation.py`](../agents/src/onehealth_agents/validation.py),
  this gives a tribal partner two independent points of control
  over what leaves their network.

## Optional differential privacy

`apply_laplace_noise(stats, epsilon=1.0)` applies the Laplace
mechanism to each bucket count with scale `b = 1 / epsilon`.
Sensitivity is 1 -- a single contributor changes any bucket by at
most 1 -- so the mechanism is `epsilon`-DP per release.

### Privacy-budget trade-off table

| `epsilon` | Laplace scale `b` | Mean abs noise per bucket | Detection-impact on 2021 Maricopa-WNV scenario |
|----------:|------------------:|--------------------------:|------------------------------------------------|
| **0.1**   |              10.0 |                       ~10 | Hot ZCTAs (observed ~24, ~22) usually survive; small / mid clusters (k near 5) are destroyed. False-positive surge in baseline ZCTAs. Sensitivity drops sharply. |
| **0.5**   |               2.0 |                        ~2 | Hot ZCTAs almost always survive; FP-rate roughly 3-5x the no-noise baseline. |
| **1.0**   |               1.0 |                        ~1 | Default. Federated detector reproduces the centralised alert set as a *superset* on >= 80% of trials in `test_dp_variant_alert_set_is_superset_at_least_80pct`. |
| **5.0**   |               0.2 |                       ~0.2 | Essentially indistinguishable from the no-noise run. Privacy guarantee is weak. |
| **10.0**  |               0.1 |                       ~0.1 | Noise smaller than rounding. Use only for joint releases where the budget is dominated by other queries. |

Pick `epsilon` based on the threat model: lower is more private but
loses small-denominator clusters; higher preserves detection but
weakens the privacy floor. The default `epsilon=1.0` is calibrated
against the Maricopa-WNV-2021 case in `test_federated.py`.

When `apply_laplace_noise` is used, the payload's `dp_epsilon`
field records the budget so the coordinator can audit-trail it.
Noised payloads have their `signature` cleared (signing the
post-noise bytes would defeat replay protection); a production
deployment would sign the *post-noise* bytes at the same site as
the noise is applied.

## Why it's incomplete for production

This prototype is intentionally minimal. The pieces that would
need to land before a Phase-4 production deployment:

* **Secure MPC.** The coordinator currently sees per-site counts.
  Secure multi-party computation (or homomorphic encryption with
  threshold decryption) would let the coordinator compute the
  bucket sums *without* learning any single site's counts. The
  honest-but-curious coordinator surface is acceptable for an
  internal hackathon prototype; it is not acceptable for tribal
  data.
* **Formal privacy budget.** The Laplace mechanism gives
  `epsilon`-DP per release. Repeated releases compose linearly;
  a production system would track a running budget per site and
  refuse to release past a per-month / per-quarter cap. The
  prototype tracks `epsilon` per payload but does **not** compose
  across releases.
* **Malicious-aggregator hardening.** The current
  `FederatedScanCoordinator` does not implement: replay protection
  (monotonic nonces per site), anti-rollback (committed-window
  registry), de-duplication of payloads across rounds, or
  per-payload audit logging to an append-only store.
* **Sybil resistance.** Anyone with a registered public key can
  contribute a payload. A production deployment would gate
  registration through the governance board described in
  [`plan/05-roadmap.md`](./05-roadmap.md#cross-cutting-tracks).
* **Time-window alignment.** The coordinator asserts uniform
  vertical and bucket cadence across payloads but currently
  trusts the `window_start` / `window_end` declarations. A
  production version would require all payloads to use the same
  scan and baseline windows down to the second.
* **Crypto-signing roadmap.**
  * The reference implementation uses *raw* Ed25519 public keys
    (32 bytes / 64 hex chars). Production should pin keys via an
    X.509 / PKIX certificate chain anchored at the tribal-DUA
    registry, with key rotation playbooks per site.
  * Signature verification should be enforced (`require_signature=True`)
    in production, not optional.
  * Add a timestamp to the signed bytes so old payloads cannot be
    replayed inside a fresh round.
  * The canonical JSON form is a quick prototype choice. Production
    should adopt a stable, audited serialisation (e.g. RFC 8785
    JSON Canonicalization Scheme, or a CBOR-based scheme) so two
    correct implementations always produce identical bytes-to-sign.

## Onboarding a new site

The contract is small enough that a new tribal or agency partner
can onboard without bilateral integration work:

1. **Decide what to share.** Identify the vertical(s) (`VBD`,
   `HEAT`, or both) the site will contribute to. Decide whether
   ZCTAs will be released as-is or coarsened to county-centroid
   ZCTAs for additional sovereignty.
2. **Generate an Ed25519 keypair.**
   ```python
   from cryptography.hazmat.primitives import serialization
   from cryptography.hazmat.primitives.asymmetric.ed25519 import (
       Ed25519PrivateKey,
   )
   priv = Ed25519PrivateKey.generate()
   priv_pem = priv.private_bytes(
       encoding=serialization.Encoding.PEM,
       format=serialization.PrivateFormat.PKCS8,
       encryption_algorithm=serialization.BestAvailableEncryption(b"..."),
   )
   pub_hex = priv.public_key().public_bytes(
       encoding=serialization.Encoding.Raw,
       format=serialization.PublicFormat.Raw,
   ).hex()
   ```
   Hand `pub_hex` to the governance board; keep the private key
   inside the site's perimeter.
3. **Hash the site identifier.**
   ```python
   from onehealth_agents.federated import hash_site_id
   site_hash = hash_site_id("Navajo Epidemiology Center")
   ```
4. **Run the aggregator on each cycle.**
   ```python
   from onehealth_agents.federated import LocalSiteAggregator
   agg = LocalSiteAggregator(site_id="Navajo Epidemiology Center")
   stats = agg.aggregate(local_observations, vertical=Vertical.VBD)
   signed = agg.sign(stats, priv_pem)
   ```
   `local_observations` is whatever subset the site is willing to
   release into the federated round. The aggregator strips
   row-level data by construction.
5. **Optionally apply DP noise.**
   ```python
   from onehealth_agents.federated import apply_laplace_noise
   signed = apply_laplace_noise(signed, epsilon=1.0)
   # NB: noising strips the signature; re-sign post-noise if
   # signatures are required.
   ```
6. **Publish.** POST the JSON payload
   (`signed.model_dump_json()`) to the coordinator endpoint.
7. **Verify the contribution lands.** The coordinator's response
   includes the resulting `ClusterAlert`s; each is tagged with the
   site hash in `contributing_sites` for audit.
8. **MOU + DUA review.** Run the first three cycles in
   parallel-shadow mode; have the governance board review the
   payload-and-alert log before the site's results contribute to
   public dashboards.

## Optional `kg_federated_aggregate(...)` MCP tool -- *not shipped*

We considered exposing the `FederatedScanCoordinator` as a tool on
[`knowledge-graph-mcp`](../mcp/knowledge-graph-mcp/). It would have
let an LLM run a federated scan over a list of published payloads
the way it can already run `kg_outbreak_check`.

**Decision: skip in this round.** Adding `kg_federated_aggregate`
would have:

* Broken the read-only surface invariant the kg-MCP README explicitly
  guarantees -- a federated-detection tool is unavoidably a compute /
  side-effect surface, not a read-only graph lookup.
* Required gluing in an Ed25519 key registry and a per-site payload
  cache, neither of which has a natural home inside an MCP server
  whose only persistent state is a DuckDB connection.

The federated coordinator lives where it belongs: in the agents
package, invoked from the orchestrator or directly by the cluster
detection cron. A future MCP server (`federation-mcp`?) is the right
home for tool-style access; layering it onto `knowledge-graph-mcp`
would compromise both surfaces.
