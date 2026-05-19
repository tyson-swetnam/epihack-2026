---
title: "Evaluation Harness"
---

# Evaluation Harness

This note describes the Phase-4 evaluation harness from
[`plan/05-roadmap.md`](05-roadmap.md): how the OneHealth eight-agent
pipeline is scored against the
[Figure-3 timeliness milestones](../figures/03-outbreak-timeliness-metrics.html),
how the 2024 historical-counterfactual baseline is constructed, and how
to read the per-agency, per-vertical scorecard the harness emits.

The implementation lives in
[`agents/src/onehealth_agents/evaluation.py`](../agents/src/onehealth_agents/evaluation.py)
with offline tests at
[`agents/tests/test_evaluation.py`](../agents/tests/test_evaluation.py)
and the pre-extracted baselines under
[`evaluation/baseline-2024.json`](../evaluation/baseline-2024.json).

## Methodology

### 1. Agent runs are the milestone clock

The orchestrator writes one row to `kg.agent_run` per agent invocation
(`schema/deep/audit.sql`). The accompanying view
`kg.v_observation_timeliness` pivots those rows into the five
Figure-3 milestones per observation:

| Agent (`agent_name`) | Figure-3 milestone | Column in the view |
|---|---|---|
| `intake`       | Detect  | `detect_at` |
| `validation`   | Notify  | `notify_at` |
| `triage`       | Verify  | `verify_at_provisional` |
| `enrichment`   | Lab     | `lab_at_provisional` |
| `notification` | Respond | `respond_at` |

The Verify and Lab mappings are marked **provisional** in the audit
SQL header because the canonical Figure-3 milestones for those steps
are owned by human authorities (ADHS field investigation, ADHS
diagnostic lab). The system-side timestamps are a proxy that
downstream evaluation should later overwrite or join with the
human-confirmed timestamp.

### 2. Intervals are computed per (vertical, agency)

For every observation in the configured window we compute the five
adjacent-milestone intervals (Detect→Notify, Notify→Verify,
Verify→Lab, Lab→Respond) plus the end-to-end Detect→Respond
interval. We then group observations by `(vertical, agency)` and
report:

- `n` -- number of observations contributing to each interval;
- `median` -- robust against the heavy right tail every real audit
  log has;
- `p25` / `p75` / `iqr` -- linear-method percentiles, pure-stdlib
  (no numpy dependency);
- `baseline_min` -- the 2024 counterfactual median for the same pair
  (see "Baseline construction" below);
- `pct_change_vs_baseline` -- `(median - baseline) / baseline * 100`
  (negative = faster than baseline);
- `pct_shorter_vs_baseline` -- positive-is-good restatement that
  matches the plan-05-roadmap success-criterion phrasing.

### 3. The Phase-3 success-criterion verdict

`plan/05-roadmap.md` Phase 3 reads:

> During the heat season and the WNV season, the median Detect →
> Notify interval for reports flowing through the app is at least
> **30% shorter** than the 2024 baseline for the same counties.

The harness encodes this as a `Phase3Verdict` per `(vertical,
agency)` cell. The cell **passes** when
`pct_shorter_vs_baseline ≥ 30`. It **fails** when the pipeline is
slower, when there is no in-window observation, or when no
baseline exists for that (vertical, agency).

## Baseline construction

The 2024 counterfactual baselines live in
[`evaluation/baseline-2024.json`](../evaluation/baseline-2024.json).
They are **pre-extracted by hand from
[`schema/deep/outbreaks.sql`](../schema/deep/outbreaks.sql)** rather
than parsed at runtime, because the seed encodes dates with mixed
precision (year-only, month-only, exact-day) and the json file is
the place to make that precision explicit.

The two 2024 outbreaks the seed encodes are:

1. **`outbreak.az_hantavirus_2024`** -- VBD. `start_date '2024-01'`,
   `notify_date '2024-07-08'` (the ADHS HAN advisory). We use
   January 15 as the Detect proxy (midpoint of the month-only start
   date) and July 8 as the Notify timestamp; the implied
   Detect → Notify interval is ~175 days (251,280 minutes). 11
   cases, 6 deaths combined with the 2023 cluster.

2. **`outbreak.az_heat_2024`** -- Heat. `start_date '2024-04'`, no
   explicit notify or respond dates in the seed (the season is the
   intervention). We use April 15 as the Detect proxy, April 20 as
   the Notify proxy (~5 days post-season-onset, when MCDPH heat
   surveillance typically declares the first cluster), and April 22
   for Respond / Public Comm. 602 deaths in Maricopa County across
   70 days at or above 110 °F.

Each cell in `per_vertical_per_agency_baseline` is attributed to the
agency that reported the outbreak (`reportedBy` edges in
`schema/deep/outbreaks.sql`). Cells where the milestone is missing
from the published record carry `null` -- the evaluator treats
`null` as "no comparison possible" rather than zero, so a `null`
baseline yields a `% shorter = n/a` cell in the scorecard.

## Scorecard structure

A rendered scorecard is divided into three sections:

1. **Header** -- window, verticals, agencies, baseline year + source
   path, generation timestamp, total observations.
2. **Phase-3 success criterion table** -- one row per `(agency,
   vertical)` cell with the Detect → Notify median, the baseline,
   the percent-shorter, and a PASS/FAIL verdict.
3. **Per-agency, per-vertical interval scorecards** -- one
   sub-section per cell with all five milestone-pair intervals.

The exact rendering is produced by `render_markdown(report)` and is
also available as JSON via `--format json` on the CLI.

## Example scorecard

The synthetic example below shows the layout. Numbers are from
five Heat observations routed to MCDPH and three VBD observations
routed to ADHS during a hypothetical 2026-05-01 → 2026-09-30 window.

```
# OneHealth Pipeline -- Figure-3 Timeliness Scorecard

**Window:** 2026-05-01 → 2026-09-30
**Verticals:** vbd, heat
**Agencies:** resource.mcdph_heat, resource.adhs
**Historical baseline year:** 2024
**Total observations in window:** 8

## Phase-3 success criterion (Detect → Notify ≥ 30% shorter vs 2024)

| Agency              | Vertical | Median (pipeline) | Baseline (2024) | % shorter | Verdict |
|---------------------|----------|------------------:|----------------:|----------:|:-------:|
| resource.mcdph_heat | heat     | 6.0 min           | 5.0 d           | 99.9%     | PASS    |
| resource.adhs       | vbd      | 3.0 d             | 174.5 d         | 98.3%     | PASS    |
| resource.adhs       | heat     | n/a               | n/a             | n/a       | FAIL    |
| resource.mcdph_heat | vbd      | n/a               | n/a             | n/a       | FAIL    |

## Per-agency, per-vertical interval scorecards

### resource.mcdph_heat -- heat
_n_ = 5 observations

| Pair               | n | Median | IQR (p25-p75)    | Baseline | Δ vs base | % shorter |
|--------------------|--:|-------:|------------------:|---------:|----------:|----------:|
| detect_to_notify   | 5 | 6.0 min | 5.0 min - 7.0 min | 5.0 d   | -99.9%    | 99.9%     |
| notify_to_verify   | 5 | 3.0 min | 3.0 min - 3.0 min | n/a     | n/a       | n/a       |
| verify_to_lab      | 0 | n/a     | n/a               | n/a     | n/a       | n/a       |
| lab_to_respond     | 0 | n/a     | n/a               | 2.0 d   | n/a       | n/a       |
| detect_to_respond  | 5 | 13.0 min| 12.0 min - 15.0 m | 7.0 d   | -99.9%    | 99.9%     |
```

The two FAIL rows are not regressions -- they are cells where the
configured agency had **no in-window observations of that
vertical**. The Phase-3 verdict honestly distinguishes "no data"
from "data, but slower than baseline" via the `reason` field on the
`Phase3Verdict` model.

## CLI usage

```
$ python -m onehealth_agents.evaluation \
    --start 2026-05-01 \
    --end 2026-09-30 \
    --vertical vbd --vertical heat \
    --agency resource.mcdph_heat --agency resource.adhs \
    --format md
```

`--format json` emits the same `EvaluationReport` as machine-readable
JSON (pydantic `model_dump_json`). `--ducklake-uri` (or the
`KG_DUCKLAKE_URI` env var) points at the production DuckLake URI; if
unset and no `--baseline-path` override is supplied, the harness
runs purely on the on-disk baseline and reports 0 observations.

## Known limitations

These are surfaced explicitly so a reviewer reading the scorecard
knows what *not* to over-interpret.

- **Agent-run audit data isn't real surveillance data.** Every
  milestone here is timestamped by an agent invocation, not by a
  field epidemiologist's case-confirmation. A 6-minute Detect →
  Notify in the scorecard means the orchestrator wrote both rows
  6 minutes apart -- it does not mean ADHS *acted on* the report
  6 minutes after the user submitted it. The system-side numbers
  are an upper bound on how fast the human workflow can possibly be
  given the same intake stream.

- **The Detect milestone shifts with human-vs-machine review.** The
  audit-SQL header explicitly marks Verify and Lab as PROVISIONAL.
  The same applies to Detect for any vertical where the canonical
  Detect milestone is "symptom onset" rather than "report
  received". Heat is the cleanest fit (CHW check-in ~ symptom
  onset); VBD tick reports are typically days-to-weeks behind
  symptom onset, so the apparent Detect-to-Notify speedup in the
  scorecard is partly an artifact of starting the clock late.

- **Tribal-data suppression caps some intervals.** Per Plan 02's
  data-sovereignty rules, observations from tribal lands may be
  county-level aggregated or fully suppressed. That structurally
  lowers the `n` in any cell that includes those geographies, and
  in extreme cases can leave a scorecard row with `n=0` even
  though the underlying community is generating real reports. The
  RMSF tribal outbreak is the canonical case study -- see
  [`plan/CLUSTER-CALIBRATION.md`](CLUSTER-CALIBRATION.md) for the
  same trade-off on the detection side.

- **Baseline precision is mixed.** The 2024 hantavirus Detect proxy
  is mid-January (the seed has month-only precision). The 2024 heat
  Notify proxy is estimated. The baselines are useful as
  order-of-magnitude counterfactuals, not as ground truth.
  When a more precise published record (MMWR follow-up, AAR) becomes
  available, the json baseline should be regenerated against it.

- **Per-pair baselines for Verify / Lab / Notify→Verify intervals
  are mostly null.** Published outbreak records rarely note the
  field-investigation or lab-confirmation timestamps separately, so
  most non-Detect→Notify cells in the baseline are `null`. The
  scorecard renders those cells as `n/a`, signalling "no
  counterfactual to compare against".

## Reproducing locally

```
cd agents
uv sync --extra dev
uv pip install duckdb            # optional; only needed for the live SQL path
uv run pytest tests/test_evaluation.py -v
uv run python -m onehealth_agents.evaluation --start 2026-05-01 --end 2026-09-30
```

The tests are pure-stdlib and run in under a second. The DuckLake-bound
code path is smoke-tested by `tests/test_audit.py` (the
`v_observation_timeliness` view round-trip), so end-to-end coverage is
maintained without coupling the evaluation tests to a database.
