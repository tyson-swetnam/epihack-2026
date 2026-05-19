"""Calibration harness for the two-tier ClusterDetectionAgent.

Loads the 14 historical AZ outbreaks from ``schema/deep/outbreaks.sql``
(parsed with stdlib regex; no DuckDB), synthesises 60 days of baseline
plus the outbreak-period observations at realistic rates, and asserts
the detector fires within the documented detection window.

Also runs a null-control fleet (Poisson noise around baseline) and
asserts the detector does *not* fire spuriously.

Reports sensitivity, FP-rate per agency-week, and median lag.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from onehealth_agents import (
    ClusterDetectionAgent,
    GeneralClass,
    GeoEnrichment,
    Kind,
    MinimumDataset,
    Observation,
    Vertical,
)
from onehealth_agents.cluster import (
    HISTORICAL_OUTBREAKS,
    HistoricalOutbreak,
    _ZCTA_CENTROIDS,
    _COUNTY_CENTROIDS,
)


# ---------------------------------------------------------------------------
# Repo path -- assert we actually parsed the SQL file (don't depend on the
# cluster module having silently fallen back to an empty list).
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
SQL_PATH = REPO_ROOT / "schema" / "deep" / "outbreaks.sql"


def test_historical_corpus_loaded():
    assert SQL_PATH.exists(), f"missing seed file {SQL_PATH}"
    assert len(HISTORICAL_OUTBREAKS) == 14, (
        f"expected the 14 AZ outbreaks; got {len(HISTORICAL_OUTBREAKS)}"
    )
    slugs = {h.slug for h in HISTORICAL_OUTBREAKS}
    # Spot-check the named ones from the task brief.
    for required in (
        "outbreak.four_corners_hantavirus_1993",
        "outbreak.maricopa_wnv_2021",
        "outbreak.maricopa_heat_2023",
        "outbreak.az_heat_2024",
        "outbreak.az_hantavirus_2024",
        "outbreak.coconino_plague_2025",
        "outbreak.az_rmsf_tribal_2003_present",
    ):
        assert required in slugs


# ---------------------------------------------------------------------------
# Outbreak -> synthesis profile
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CalibrationCase:
    slug: str
    vertical: Vertical
    zcta: str
    # Outbreak-period: N reports across `period_days` starting at `start_offset`
    # days after the synthetic "now". (We anchor synthetic time so the
    # detector runs at "the end of the outbreak window".)
    period_days: int
    n_reports_during: int
    detection_target_days: int  # detector must fire within this many days of start
    # Pre-outbreak baseline (statewide, light Poisson noise).
    notes: str = ""


# Detection-window targets per outbreak. These reflect the real-world
# milestones and the agent contract (Heat is 2-hour, VBD weekly).
CASES: list[CalibrationCase] = [
    # Hantavirus 1993 -- detection at week-cadence; CDC notify lag ~6 weeks
    CalibrationCase("outbreak.four_corners_hantavirus_1993", Vertical.VBD,
                    "86503", period_days=60, n_reports_during=24,
                    detection_target_days=21,
                    notes="Sin Nombre discovery, Four Corners"),
    # 2003 Maricopa WNV emergence
    CalibrationCase("outbreak.az_wnv_2003", Vertical.VBD,
                    "85003", period_days=60, n_reports_during=13,
                    detection_target_days=28),
    # 2014 Yuma dengue (travel-associated, slow build)
    CalibrationCase("outbreak.az_dengue_yuma_sonora_2014", Vertical.VBD,
                    "85364", period_days=90, n_reports_during=70,
                    detection_target_days=21),
    # 2014 chikungunya importations
    CalibrationCase("outbreak.az_chikungunya_2014", Vertical.VBD,
                    "85003", period_days=120, n_reports_during=20,
                    detection_target_days=35),
    # 2021 Maricopa WNV -- 1487 cases over Jun-Dec; should fire well before
    # the real-world Sep-02 notify date.
    CalibrationCase("outbreak.maricopa_wnv_2021", Vertical.VBD,
                    "85003", period_days=120, n_reports_during=300,
                    detection_target_days=7,
                    notes="Largest US single-county WNV ever"),
    # HPAI in wild birds (slow burn; we test it can fire on the human-case
    # window when the Pinal poultry workers got sick).
    CalibrationCase("outbreak.az_hpai_h5n1_wildbird_2022", Vertical.VBD,
                    "85201", period_days=30, n_reports_during=8,
                    detection_target_days=14),
    # 2023 hantavirus spike
    CalibrationCase("outbreak.az_hantavirus_2023", Vertical.VBD,
                    "86001", period_days=180, n_reports_during=6,
                    detection_target_days=60,
                    notes="Small denominator -- 6 cases across full year"),
    # 2023 Maricopa heat -- hot in the Jul 10-25 streak
    CalibrationCase("outbreak.maricopa_heat_2023", Vertical.HEAT,
                    "85009", period_days=16, n_reports_during=303,
                    detection_target_days=2,
                    notes="Jul 10-25 streak; 2h cadence"),
    # 2023 cooling-center barriers MMWR observation cluster (Aug-Sep)
    CalibrationCase("outbreak.maricopa_cooling_center_barriers_2023", Vertical.HEAT,
                    "85009", period_days=45, n_reports_during=200,
                    detection_target_days=3),
    # 2024 hantavirus
    CalibrationCase("outbreak.az_hantavirus_2024", Vertical.VBD,
                    "86001", period_days=180, n_reports_during=11,
                    detection_target_days=60),
    # 2024 record heat
    CalibrationCase("outbreak.az_heat_2024", Vertical.HEAT,
                    "85009", period_days=70, n_reports_during=602,
                    detection_target_days=2,
                    notes="113 consecutive 100+ days"),
    # 2025 Coconino plague (single index case; we expect it NOT to fire on
    # the cluster detector -- documented limitation, see notes).
    CalibrationCase("outbreak.coconino_plague_2025", Vertical.VBD,
                    "86001", period_days=2, n_reports_during=1,
                    detection_target_days=14,
                    notes="single index case; expected detector miss"),
    # RMSF tribal 2003-present -- chronic cluster, we test a one-year window
    CalibrationCase("outbreak.az_rmsf_tribal_2003_present", Vertical.VBD,
                    "85546", period_days=180, n_reports_during=40,
                    detection_target_days=21),
    # RMSF rodeo pilot 2012 -- ALSO test the pilot community signal
    CalibrationCase("outbreak.az_rmsf_rodeo_pilot_2012", Vertical.VBD,
                    "85501", period_days=180, n_reports_during=30,
                    detection_target_days=28),
]

# Outbreaks the detector is *expected* to miss with reasons. These are
# treated as known-misses, not test failures, and surfaced in metrics.
EXPECTED_MISSES: set[str] = {
    # Single index case can't possibly trigger a count-based scan.
    "outbreak.coconino_plague_2025",
}


# ---------------------------------------------------------------------------
# Synthesis helpers
# ---------------------------------------------------------------------------
RNG_SEED = 20260519


def _baseline_zctas(case: CalibrationCase) -> list[str]:
    """ZCTAs to populate with baseline noise (state-level denominator).

    Always include a handful of other ZCTAs so the state-level baseline is
    realistic (you can't have a 1-ZCTA state).
    """
    others = [z for z in _ZCTA_CENTROIDS if z != case.zcta]
    # Take a stable subset of 6 other ZCTAs for the baseline.
    return [case.zcta] + sorted(others)[:6]


def _make_obs(*, zcta: str, ts: datetime, vertical: Vertical) -> Observation:
    geo = GeoEnrichment(zcta=zcta)
    return Observation(
        kind=Kind.MCP_PULL,
        vertical=vertical,
        received_at=ts.isoformat(),
        dataset=MinimumDataset(general=GeneralClass(postal_code=zcta)),
        geo=geo,
    )


def synthesise_observations(
    case: CalibrationCase,
    *,
    now: datetime,
    rng: random.Random,
    baseline_per_zcta_per_day: float,
) -> tuple[list[Observation], datetime]:
    """Build 60 days of baseline + the outbreak-period observations.

    Returns (observations, outbreak_start_datetime).
    """
    observations: list[Observation] = []
    zctas = _baseline_zctas(case)

    # 60 days of baseline state-wide Poisson(baseline_per_zcta_per_day).
    baseline_days = 60
    baseline_start = now - timedelta(days=baseline_days + case.period_days)
    outbreak_start = now - timedelta(days=case.period_days)

    for z in zctas:
        # Spread baseline events uniformly across the baseline window.
        n = _poisson(baseline_per_zcta_per_day * baseline_days, rng)
        for _ in range(n):
            offset_h = rng.uniform(0, baseline_days * 24)
            ts = baseline_start + timedelta(hours=offset_h)
            observations.append(_make_obs(zcta=z, ts=ts, vertical=case.vertical))

    # Continue background baseline through the outbreak window so the
    # state-level denominator stays realistic.
    for z in zctas:
        n = _poisson(baseline_per_zcta_per_day * case.period_days, rng)
        for _ in range(n):
            offset_h = rng.uniform(0, case.period_days * 24)
            ts = outbreak_start + timedelta(hours=offset_h)
            observations.append(_make_obs(zcta=z, ts=ts, vertical=case.vertical))

    # Outbreak-period observations in the case's ZCTA. Heat events cluster
    # in the late-afternoon / early-evening 2-hour windows; VBD events are
    # spread uniformly across the period.
    is_heat = case.vertical is Vertical.HEAT
    for _ in range(case.n_reports_during):
        day_offset = rng.uniform(0, case.period_days)
        if is_heat:
            # Sample diurnally: 70% of events fall into a 6-hour peak
            # window (15:00-21:00 local-ish, treated as UTC for the test).
            if rng.random() < 0.7:
                hour = rng.uniform(15, 21)
            else:
                hour = rng.uniform(0, 24)
        else:
            hour = rng.uniform(0, 24)
        ts = outbreak_start + timedelta(days=day_offset, hours=hour)
        observations.append(_make_obs(zcta=case.zcta, ts=ts, vertical=case.vertical))

    return observations, outbreak_start


def _poisson(lam: float, rng: random.Random) -> int:
    """Knuth's Poisson sampler -- fine for small lambda."""
    if lam <= 0:
        return 0
    if lam > 30:
        # Normal approximation -- floored at zero.
        return max(0, int(rng.gauss(lam, math.sqrt(lam))))
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= L:
            return k - 1


# ---------------------------------------------------------------------------
# Calibration test
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def calibration_run():
    """Run the detector against every synthesised case once, return metrics."""
    rng = random.Random(RNG_SEED)
    agent = ClusterDetectionAgent()

    @dataclass
    class CaseResult:
        case: CalibrationCase
        fired: bool
        first_alert_offset_days: float | None
        n_alerts: int

    results: list[CaseResult] = []
    for case in CASES:
        # Anchor "now" at the end of the outbreak period for week-cadence
        # cases; for heat we sweep through the bucket to find the first hit.
        now = datetime(2024, 8, 1, 12, 0, tzinfo=timezone.utc) \
            if case.vertical is Vertical.HEAT \
            else datetime(2024, 6, 1, 0, 0, tzinfo=timezone.utc)

        baseline_per_zcta_per_day = (
            0.20 if case.vertical is Vertical.HEAT else 0.02
        )
        obs, outbreak_start = synthesise_observations(
            case, now=now, rng=rng,
            baseline_per_zcta_per_day=baseline_per_zcta_per_day,
        )

        # Sweep the detector forward day-by-day to find the first alert.
        fired = False
        first_offset: float | None = None
        n_alerts = 0
        for day in range(case.period_days + 1):
            scan_now = outbreak_start + timedelta(days=day)
            alerts = agent.run(obs, now=scan_now)
            hits = [
                a for a in alerts
                if a.zcta == case.zcta and a.vertical == case.vertical
            ]
            if hits and not fired:
                fired = True
                first_offset = day
                n_alerts = len(hits)
                break

        results.append(CaseResult(
            case=case, fired=fired,
            first_alert_offset_days=first_offset, n_alerts=n_alerts,
        ))

    # Null-control fleet -- 40 synthetic null cohorts of pure Poisson noise.
    null_rng = random.Random(RNG_SEED + 1)
    null_fires = 0
    null_total_agency_weeks = 0
    for trial in range(40):
        zctas = list(_ZCTA_CENTROIDS)[:8]
        baseline_days = 90
        now = datetime(2024, 5, 1, tzinfo=timezone.utc)
        obs: list[Observation] = []
        for z in zctas:
            n = _poisson(0.02 * baseline_days, null_rng)
            for _ in range(n):
                ts = now - timedelta(hours=null_rng.uniform(0, baseline_days * 24))
                obs.append(_make_obs(zcta=z, ts=ts, vertical=Vertical.VBD))
        alerts = ClusterDetectionAgent().run(obs, now=now)
        if alerts:
            null_fires += len(alerts)
        # Each trial covers ~baseline_days / 7 = ~13 agency-weeks per ZCTA.
        null_total_agency_weeks += len(zctas) * (baseline_days / 7)

    return {
        "results": results,
        "fp_alerts": null_fires,
        "agency_weeks": null_total_agency_weeks,
    }


def test_detector_fires_on_positive_cases(calibration_run):
    """Each non-expected-miss historical outbreak must fire within its
    documented detection-window."""
    results = calibration_run["results"]
    failures: list[str] = []
    for r in results:
        if r.case.slug in EXPECTED_MISSES:
            continue
        if not r.fired:
            failures.append(f"{r.case.slug}: never fired")
            continue
        if r.first_alert_offset_days > r.case.detection_target_days:
            failures.append(
                f"{r.case.slug}: fired at day {r.first_alert_offset_days} "
                f"> target {r.case.detection_target_days}"
            )
    assert not failures, "Detector regressions:\n  " + "\n  ".join(failures)


def test_detector_silent_on_null_controls(calibration_run):
    """The null-control fleet should be very quiet."""
    fp = calibration_run["fp_alerts"]
    weeks = calibration_run["agency_weeks"]
    fp_rate = fp / max(weeks, 1)
    # < 0.05 false alerts per agency-week is the operational target.
    assert fp_rate < 0.05, f"FP rate too high: {fp_rate:.4f} per agency-week"


def test_calibration_metrics_summary(calibration_run, capsys):
    """Emit the sensitivity + median-lag metrics in the test output."""
    results = calibration_run["results"]
    evaluable = [r for r in results if r.case.slug not in EXPECTED_MISSES]

    vbd = [r for r in evaluable if r.case.vertical is Vertical.VBD]
    heat = [r for r in evaluable if r.case.vertical is Vertical.HEAT]

    def _sens(rs):
        return sum(1 for r in rs if r.fired) / max(len(rs), 1)

    def _median_lag(rs):
        hits = sorted(r.first_alert_offset_days for r in rs if r.fired)
        if not hits:
            return float("nan")
        n = len(hits)
        return hits[n // 2] if n % 2 else 0.5 * (hits[n // 2 - 1] + hits[n // 2])

    fp_rate = calibration_run["fp_alerts"] / max(calibration_run["agency_weeks"], 1)

    lines = [
        "=" * 60,
        "Cluster Detection Calibration Metrics",
        "=" * 60,
        f"VBD sensitivity:        {_sens(vbd):.2%}  ({sum(1 for r in vbd if r.fired)}/{len(vbd)})",
        f"VBD median lag (days):  {_median_lag(vbd):.1f}",
        f"Heat sensitivity:       {_sens(heat):.2%}  ({sum(1 for r in heat if r.fired)}/{len(heat)})",
        f"Heat median lag (days): {_median_lag(heat):.1f}",
        f"Overall sensitivity:    {_sens(evaluable):.2%}",
        f"FP-rate / agency-week:  {fp_rate:.4f}",
        "Per-case:",
    ]
    for r in results:
        tag = "MISS-OK" if r.case.slug in EXPECTED_MISSES else ("FIRE" if r.fired else "MISS")
        lag = f"{r.first_alert_offset_days:.0f}d" if r.first_alert_offset_days is not None else " - "
        lines.append(f"  [{tag:7s}] lag={lag:>5s}  {r.case.slug}")
    print("\n".join(lines))
    # Use the capsys fixture to make sure pytest -s shows it.
    out = capsys.readouterr().out
    assert "Cluster Detection Calibration Metrics" in out

    # Operational floor: overall sensitivity must be at least 85% on the
    # evaluable set; VBD must clear 80%; Heat must clear 100%.
    assert _sens(evaluable) >= 0.85
    assert _sens(vbd) >= 0.80
    assert _sens(heat) >= 1.00


def test_audit_fields_populated_on_alerts(calibration_run):
    """At least one alert must carry every documented audit field."""
    # Re-run a known-firing case to inspect the audit payload.
    case = next(c for c in CASES if c.slug == "outbreak.maricopa_wnv_2021")
    rng = random.Random(RNG_SEED + 99)
    now = datetime(2024, 6, 1, tzinfo=timezone.utc)
    obs, _ = synthesise_observations(
        case, now=now, rng=rng, baseline_per_zcta_per_day=0.02,
    )
    alerts = ClusterDetectionAgent().run(obs, now=now)
    assert alerts, "WNV 2021 calibration case must produce at least one alert"
    a = alerts[0]
    assert a.tier1_score is not None and a.tier1_score >= 3.0
    assert a.tier2_posterior is not None and a.tier2_posterior >= 0.95
    assert a.baseline_window_start is not None
    assert a.baseline_window_end is not None
    assert a.rule_tripped and a.rule_tripped.startswith("vbd/zcta-week/")
    # Historical match should point at the closest known Maricopa WNV record.
    # (Either the 2003 emergence or the 2021 outbreak depending on temporal
    # proximity to the synthetic "now".)
    assert a.historical_match in {
        "outbreak.maricopa_wnv_2021",
        "outbreak.az_wnv_2003",
    }, a.historical_match


def test_heat_2h_bucket_audit_fields():
    """Heat alerts during the heat season should use the 2h cadence rule."""
    case = next(c for c in CASES if c.slug == "outbreak.az_heat_2024")
    rng = random.Random(RNG_SEED + 7)
    now = datetime(2024, 8, 15, 18, 0, tzinfo=timezone.utc)
    obs, _ = synthesise_observations(
        case, now=now, rng=rng, baseline_per_zcta_per_day=0.20,
    )
    alerts = ClusterDetectionAgent().run(obs, now=now)
    assert alerts, "Heat 2024 case must produce at least one alert"
    rules = {a.rule_tripped for a in alerts}
    assert any("heat/zcta-2h/" in (r or "") for r in rules), rules
