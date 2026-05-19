# `evaluation/`

Pre-extracted historical baselines and reproducibility recipes for the
Phase-4 evaluation harness from
[`plan/05-roadmap.md`](../plan/05-roadmap.md). See
[`plan/EVALUATION.md`](../plan/EVALUATION.md) for the full methodology
and example scorecard.

## Files

| Path | Purpose |
|---|---|
| `baseline-2024.json` | 2024 Arizona historical-counterfactual baselines, extracted by hand from [`schema/deep/outbreaks.sql`](../schema/deep/outbreaks.sql). The `per_vertical_per_agency_baseline` block is the canonical lookup table the [`MilestoneEvaluator`](../agents/src/onehealth_agents/evaluation.py) joins against. |

`baseline-<year>.json` is what the evaluator looks for. New years
(`baseline-2025.json`, `baseline-2026.json`, …) can be added by
copying `baseline-2024.json`, replacing the contents, and pointing
the CLI at the new year via `--baseline-year 2025`.

## How `baseline-2024.json` was constructed

The 2024 outbreaks encoded in `schema/deep/outbreaks.sql` are:

- **`outbreak.az_hantavirus_2024`** -- 11 cases across 5 counties, 6
  combined 2023-2024 deaths. `start_date '2024-01'`, ADHS HAN
  advisory on `2024-07-08`. Reported by `resource.adhs` and
  `resource.coconino_hhs`.
- **`outbreak.az_heat_2024`** -- 602 Maricopa heat-associated
  deaths, 70 days at or above 110 °F, 113 consecutive days at or
  above 100 °F. `start_date '2024-04'`, ongoing-through-October.
  Reported by `resource.mcdph_heat`, `resource.adhs_heat`,
  `resource.phoenix_ohrm`.

For each outbreak we extracted (or computed) the Figure-3 milestone
timestamps from the published record:

| Milestone | Hantavirus 2024 | Heat 2024 |
|---|---|---|
| Detect | `2024-01-15` (midpoint of month-only start) | `2024-04-15` (midpoint of month-only start; proxied as first heat-attributable ED cluster) |
| Notify | `2024-07-08` (HAN advisory, exact) | `2024-04-20` (estimated, ~5 days post-Detect) |
| Verify | not in published record | not in published record |
| Lab    | not in published record | not in published record |
| Respond | not in published record | `2024-04-22` (estimated, MCDPH cooling-center activation) |

The implied Detect → Notify intervals (in minutes) are then:

- **Hantavirus 2024:** 174 days, 12 hours -> 251,280 minutes.
- **Heat 2024:** 5 days -> 7,200 minutes.

`milestone_precision` in the JSON records which figures are exact vs
estimated. When a more authoritative published record becomes
available (MMWR follow-up, AAR), regenerate the JSON to overwrite
the estimates with ground truth.

## Reproducing the harness locally

```
# Install dependencies (one-time)
cd agents
uv sync --extra dev
uv pip install duckdb          # optional; only needed for the live SQL path

# Run the offline evaluation tests
uv run pytest tests/test_evaluation.py -v

# Generate an empty scorecard (no audit data wired)
uv run python -m onehealth_agents.evaluation \
    --start 2026-05-01 \
    --end 2026-09-30 \
    --format md

# Generate the JSON form (for piping into downstream tooling)
uv run python -m onehealth_agents.evaluation \
    --start 2026-05-01 \
    --end 2026-09-30 \
    --format json > /tmp/scorecard.json

# Point at the production DuckLake catalog
KG_DUCKLAKE_URI=postgres://... uv run python -m onehealth_agents.evaluation \
    --start 2026-05-01 \
    --end 2026-09-30 \
    --agency resource.mcdph_heat \
    --agency resource.adhs \
    --format md
```

The CLI uses `evaluation/baseline-<year>.json` from the repo root by
default. `--baseline-path /path/to/other.json` overrides the location.

## Adding a new baseline year

1. Copy `baseline-2024.json` to `baseline-<year>.json`.
2. Update `year`, `source`, `outbreaks[].slug`, milestone dates, and
   counts to match the relevant `schema/deep/outbreaks.sql` rows.
3. Update `per_vertical_per_agency_baseline` with the recomputed
   median intervals per (vertical, agency).
4. Add a test case in
   [`agents/tests/test_evaluation.py`](../agents/tests/test_evaluation.py)
   that loads the new file via `Baseline.load(...)` and asserts a
   key interval, mirroring `test_baseline_2024_loads_with_expected_intervals`.
5. Drive the CLI with `--baseline-year <year>` and confirm the
   PASS / FAIL verdicts on the rendered scorecard.
