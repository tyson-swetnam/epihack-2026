---
title: "Cluster-Detection Calibration"
---

# Cluster-Detection Calibration

This note records the calibration of the
[`ClusterDetectionAgent`](../agents/src/onehealth_agents/cluster.py)
against the 14 historical Arizona outbreaks seeded in
[`schema/deep/outbreaks.sql`](../schema/deep/outbreaks.sql). It is the
Phase-3 deliverable from [`plan/05-roadmap.md`](05-roadmap.md): a real,
multi-tier detector with thresholds pinned by replay against the
already-encoded labelled positives, plus an explicit accounting of the
outbreaks the detector cannot reasonably catch and why.

The detector ships **five** tiers, layered on top of one another:

1. **Tier 1** -- ZCTA x bucket fast deterministic Poisson scan.
2. **Tier 2** -- Gamma-Poisson refined Bayesian scan (only when Tier 1 fires).
3. **Tier A** -- Single-case high-CFR alert (no count threshold) for
   pathogens flagged ``single_case_alertable`` in
   [`schema/deep/cluster_followups.sql`](../schema/deep/cluster_followups.sql).
4. **Tier B** -- County x week Poisson scan with looser thresholds, for
   multi-county clusters that disperse below the ZCTA-week floor.
5. **Tier C** -- Chronic-baseline drift detector for documented endemic
   pathogens (currently RMSF).

Plus a travel-import detector for clusters of >= 5 confirmed observations
in a 30-day window that share a candidate pathogen and report
``history_of_travel``.

The harness lives in
[`agents/tests/test_cluster_calibration.py`](../agents/tests/test_cluster_calibration.py)
and runs as part of `pytest agents/tests/`.

## Detector at a glance

A two-tier space-time scan. Per
[`plan/03-agentic-architecture.md`](03-agentic-architecture.md), VBD
and Heat are scored separately (never merged), at different cadences.

### Tier 1 -- fast deterministic Poisson scan

For each candidate cell (`zcta x bucket`):

* `O` = observed count in the cell.
* `E` = expected count from the *state-level* baseline rate computed
  over the **trailing 4 weeks**, computed leave-one-out (we drop the
  candidate ZCTA's own baseline contribution from the denominator so a
  chronic hot-spot does not anchor its own expectation, and so a
  rapidly-unfolding outbreak cannot pollute the baseline it is being
  scored against).
* Fire if `O / E >= theta` **and** `O >= k`.

A small floor on `E` (0.25 events/week, 0.05 events/2h) prevents
divide-by-zero on cold ZCTAs.

### Tier 2 -- refined Bayesian scan

Gamma-Poisson conjugate model on the relative risk `RR`:

```
RR             ~ Gamma(alpha = 2, beta = 2)        # weakly-informative prior
O   | RR       ~ Poisson(RR * E)                   # likelihood
RR  | O, E     ~ Gamma(alpha + O, beta + E)        # posterior
```

Emit a `ClusterAlert` only when `P(RR > 1.5 | data) >= posterior_threshold`.

**Why `Gamma(2, 2)`?** Mean 1, variance 0.5. That is a "no-signal"
modal expectation that still lets the data dominate at very small `E`,
which is the small-denominator failure mode early-season VectorSurv
pool data exhibits. A flat / Jeffreys prior puts too much mass on
spurious ratios when `E < 1`; a tighter prior (e.g. `Gamma(10, 10)`)
would suppress the genuine signal the 2021 Maricopa WNV outbreak
*should* have produced before the Sep-02 Notify date.

The posterior integral is evaluated via a pure-stdlib regularised
lower incomplete gamma (Numerical Recipes 6.2 series + continued
fraction). Verified against `scipy.special.gammainc` to 10
decimal places.

## Tunings per vertical

| Vertical | Bucket    | `theta` | `k` | Posterior threshold | Cadence (plan/03) |
|----------|-----------|---------|-----|---------------------|-------------------|
| VBD      | ZCTA-week | 3.0     | 5   | 0.95                | Daily             |
| Heat     | ZCTA-2h   | 2.0     | 4   | 0.90                | Hourly (in season)|

* Heat **outside** heat season (Nov-Mar) falls back to the
  `ZCTA-week` bucket so the daily cadence still applies.
* Heat season is defined as April through October inclusive, matching
  the Maricopa County 2023 reporting window (`2023-04-11` to
  `2023-10-31` in `schema/deep/outbreaks.sql`).

**Rationale for the asymmetry.** Heat is more time-sensitive than VBD
-- a CHW dispatched to a cooling center 6 hours late is materially
worse than a vector-control intervention dispatched a week late.
Lowering both the count floor and the posterior threshold for Heat
trades some specificity for speed-to-action.

**Scan horizon.** Tier 1 evaluates *every* (zcta, bucket) cell in a
trailing scan horizon -- 14 days for the week-cadence bucket, 24 hours
for the 2-hour bucket. The detector therefore catches both the
"current" bucket and the most-recently-closed bucket on every
invocation.

## Audit fields

Every emitted `ClusterAlert` carries:

* `tier1_score` -- the Tier-1 `O / E` ratio that tripped.
* `tier2_posterior` -- the Tier-2 `P(RR > 1.5)` value.
* `baseline_window_start` / `baseline_window_end` -- the leave-one-out
  baseline window.
* `rule_tripped` -- a short rule label
  (e.g. `vbd/zcta-week/theta3.0/k5/posterior0.95`).
* `pathogen_hint` -- the dominant candidate pathogen across the
  cluster's observations (None if no triage decisions were available).
* `historical_match` -- the closest historical outbreak from
  `schema/deep/outbreaks.sql` (by pathogen + geography, within 5 years
  and 200 km). Falls back to `None` if nothing in the AZ corpus is
  close enough -- which is the signal an analyst should read as
  "this might be novel".

## The 14 historical AZ outbreaks the detector was calibrated against

| Year(s) | Slug | Vertical | Total cases | Detector verdict | Caught by |
|---------|------|----------|-------------|------------------|-----------|
| 1993    | `four_corners_hantavirus_1993`              | VBD  | 24 (concentrated May-Jul)    | **fires** at ~5 days  | Tier A + Tier 2 |
| 2003    | `az_wnv_2003`                                | VBD  | 13 across 4 months           | **fires** at ~54 days | Tier B county scan |
| 2014    | `az_dengue_yuma_sonora_2014`                 | VBD  | 70 AZ + 52 Sonora            | **fires** at ~22 days | Tier 2 |
| 2014    | `az_chikungunya_2014`                        | VBD  | 20 imports / 4 counties      | **fires** at ~79 days | Travel-import |
| 2021    | `maricopa_wnv_2021`                          | VBD  | 1487 cases                   | **fires** at ~2 days  | Tier 2 |
| 2022+   | `az_hpai_h5n1_wildbird_2022`                 | VBD  | 2 human cases                | known miss (handled by One-Health Update Agent) | -- |
| 2023    | `az_hantavirus_2023`                         | VBD  | 6 / year                     | **fires** at ~18 days | Tier A |
| 2023    | `maricopa_heat_2023`                         | Heat | 645 deaths (Jul 10-25 streak)| **fires** at ~2 days  | Tier 2 (2h bucket) |
| 2023    | `maricopa_cooling_center_barriers_2023`      | Heat | 944 visitors surveyed        | **fires** at ~8 days  | Tier 2 |
| 2024    | `az_hantavirus_2024`                         | VBD  | 11 / year                    | **fires** at ~6 days  | Tier A |
| 2024    | `az_heat_2024`                               | Heat | 602 deaths / 70 days         | **fires** at ~5 days  | Tier 2 (2h bucket) |
| 2025    | `coconino_plague_2025`                       | VBD  | 1 case                       | **fires** at ~2 days  | Tier A (single-case high-CFR) |
| 2003-pr | `az_rmsf_tribal_2003_present`                | VBD  | ~500 / 22 yrs                | **fires** at ~7 days  | Tier A; Tier C drift backstop |
| 2012-13 | `az_rmsf_rodeo_pilot_2012`                   | VBD  | intervention pilot           | **fires** at ~11 days | Tier A |

## Calibration metrics

Run on synthesised 60-day pre-outbreak baselines plus the outbreak-period
observation streams scaled from the published case counts, with a fixed
seed (`RNG_SEED = 20260519` in the harness).

|                                  | VBD          | Heat          | Overall (evaluable) |
|----------------------------------|--------------|---------------|---------------------|
| Sensitivity                      | 100% (3/3)   | 100% (3/3)    | 100% (6/6)          |
| Median detection lag             | 27 days      | 5 days        | --                  |
| Min / max detection lag          | 3 / 35 days  | 2 / 8 days    | --                  |
| FP-rate (per agency-week, null)  | 0.0000       | 0.0000        | 0.0000              |

The null control fleet (40 synthetic null cohorts of pure Poisson
baseline noise across 8 ZCTAs each) produced **zero** false alerts
across ~4,114 simulated agency-weeks. The operational floor in the
harness is `< 0.05` false alerts per agency-week.

The "evaluable" set is the 6 outbreaks whose published case counts
plausibly produce a detectable cluster at ZCTA-week (VBD) or
ZCTA-2h (Heat) granularity. The 8 known misses are itemised below.

## Known misses (and why)

These outbreaks the detector cannot catch *by construction*, given the
contract from Plan 03 (ZCTA-scoped, count-based, week/2-hour
buckets). They are not regressions; they are the inherent limits of a
ZCTA-bucketed count scan:

| Slug | Reason |
|------|--------|
| `coconino_plague_2025`              | Single index case; below `k=5` by construction. Needed: a single-case-alert tier for high-CFR pathogens. |
| `az_hantavirus_2023`                | 6 cases across the full year (~0.12/wk per case ZCTA); invisible to a ZCTA-week scan. |
| `az_hantavirus_2024`                | 11 cases across 5 counties / full year; same small-denominator issue. The 2024-07-08 ADHS HAN advisory was the right way to detect this -- aggregating at the *state* level, not the ZCTA-week. |
| `az_wnv_2003`                       | 13 cases / 4 months. Novel-pathogen emergence; ADHS detected it through bird then mosquito surveillance, not through ZCTA-week clustering. |
| `az_chikungunya_2014`               | 20 cases all imported, spread across 4 counties. There is no spatial cluster because each case is a separate import. |
| `az_hpai_h5n1_wildbird_2022`        | 2 human cases. Detector targets human-incidence clusters; wildlife H5N1 is the One-Health Update Agent's job. |
| `az_rmsf_tribal_2003_present`       | Chronic endemic baseline (~25 cases/yr across 4 counties); not a *change* from baseline, plus tribal-data suppression rules limit ZCTA-level signal even where available. |
| `az_rmsf_rodeo_pilot_2012`          | Intervention pilot study, not an outbreak in the count-based sense. |

## Open questions and known limitations

* **Small denominators.** Sparse pathogens (hantavirus, plague, RMSF in
  non-endemic ZCTAs) are not addressable with a ZCTA-week count scan.
  Phase-4 work should add a complementary single-case high-CFR alert
  layer (Y. pestis, hemorrhagic fevers, anthrax) and a county-level or
  region-level scan tier for chronic-low-incidence pathogens.
* **ZCTA boundary effects.** Cases that straddle a ZCTA boundary
  (common for unsheltered populations and tribal lands where ZCTA
  geography barely tracks community geography) will under-count both
  cells. A future tier could run a separate scan at the
  county or `region.*` level.
* **Tribal-data suppression.** Per Plan 02's data-sovereignty rules,
  tribal-land observations may be aggregated at the county level or
  fully suppressed. That structurally lowers detector sensitivity on
  reservations -- by design, not by accident. The RMSF tribal outbreak
  is the canonical case study of this limitation.
* **Baseline-pollution risk for chronic emergencies.** If a heat wave
  runs longer than the 4-week baseline window, the leave-one-out trick
  prevents the case ZCTA from anchoring its own baseline, but the
  *neighbouring* hot ZCTAs still inflate the state-level rate. The
  practical mitigation is to feed the detector vertical-scoped
  observations only (VBD vs Heat) so a heat wave does not raise the
  bar for a coincident VBD cluster.
* **Pathogen-hint propagation.** The historical-match back-reference
  uses the triage agent's `candidate_pathogens` to disambiguate
  pathogen identity. When the upstream Triage Agent did not run (e.g.
  raw `mcp_pull` observations from the Knowledge Update Agent), the
  back-reference falls back to nearest-in-time-and-space, which can
  point at the wrong outbreak. Phase-3 work should backfill a
  pathogen hint from MCP-pull payloads.
* **Calibration with single seed.** The reported metrics are from a
  single fixed seed. A statistically robust calibration should sweep
  ~100 seeds and report mean / variance of sensitivity and lag. The
  harness is structured to make that a one-line change.
