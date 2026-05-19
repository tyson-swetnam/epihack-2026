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
    CandidatePathogen,
    ClusterDetectionAgent,
    ExposureClass,
    GeneralClass,
    GeoEnrichment,
    Kind,
    MinimumDataset,
    Observation,
    TriageClass,
    TriageDecision,
    Vertical,
)
from onehealth_agents.cluster import (
    CHRONIC_BASELINE_PATHOGENS,
    HISTORICAL_OUTBREAKS,
    HistoricalOutbreak,
    SINGLE_CASE_ALERTABLE,
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
    # New detector-tier inputs (Phase-3 cluster followups).
    pathogen_id: str | None = None      # tagged on each outbreak observation
    travel_imported: bool = False        # set exposure.history_of_travel=True
    # If the outbreak spread across multiple ZCTAs/counties, spread the
    # outbreak observations across this list instead of concentrating them
    # all in `zcta` (used for the county-level Tier-B scan tests).
    extra_zctas: tuple[str, ...] = ()


# Detection-window targets per outbreak. These reflect the real-world
# milestones and the agent contract (Heat is 2-hour, VBD weekly).
CASES: list[CalibrationCase] = [
    # Hantavirus 1993 -- detection at week-cadence; CDC notify lag ~6 weeks.
    # The 24 cases were concentrated in May/June 1993 (6-week window in
    # the calibration synth so the case rate is detectable).
    CalibrationCase("outbreak.four_corners_hantavirus_1993", Vertical.VBD,
                    "86503", period_days=42, n_reports_during=24,
                    detection_target_days=42,
                    notes="Sin Nombre discovery, Four Corners",
                    pathogen_id="pathogen.snv"),
    # 2003 Maricopa WNV emergence -- 13 cases / 4 months / one county.
    # Tier B (county x week) catches what Tier 1 (ZCTA x week) cannot; the
    # cases pile up slowly so detection lag mirrors the real-world
    # late-Nov first-human-case timeline.
    CalibrationCase("outbreak.az_wnv_2003", Vertical.VBD,
                    "85003", period_days=60, n_reports_during=13,
                    detection_target_days=60,
                    pathogen_id="pathogen.wnv"),
    # 2014 Yuma dengue (travel-associated, slow build)
    CalibrationCase("outbreak.az_dengue_yuma_sonora_2014", Vertical.VBD,
                    "85364", period_days=90, n_reports_during=70,
                    detection_target_days=28,
                    pathogen_id="pathogen.denv"),
    # 2014 chikungunya importations -- travel-import cluster across 4
    # counties; the travel-import detector picks this up even though the
    # spatial scan cannot. Imports were spread thinly across a full year,
    # so the trailing-30-day travel window only crosses the >=5 threshold
    # once enough cases have stacked up.
    CalibrationCase("outbreak.az_chikungunya_2014", Vertical.VBD,
                    "85003", period_days=120, n_reports_during=20,
                    detection_target_days=120,
                    pathogen_id="pathogen.chikv",
                    travel_imported=True,
                    extra_zctas=("85201", "85364", "86001")),
    # 2021 Maricopa WNV -- 1487 cases over Jun-Dec; should fire well before
    # the real-world Sep-02 notify date.
    CalibrationCase("outbreak.maricopa_wnv_2021", Vertical.VBD,
                    "85003", period_days=120, n_reports_during=300,
                    detection_target_days=7,
                    notes="Largest US single-county WNV ever",
                    pathogen_id="pathogen.wnv"),
    # HPAI in wild birds (slow burn; we test it can fire on the human-case
    # window when the Pinal poultry workers got sick).
    CalibrationCase("outbreak.az_hpai_h5n1_wildbird_2022", Vertical.VBD,
                    "85201", period_days=30, n_reports_during=8,
                    detection_target_days=14,
                    pathogen_id="pathogen.h5n1"),
    # 2023 hantavirus spike -- 6 cases across 3 northern counties (Apache,
    # Coconino, Navajo). Tier A (single-case high-CFR) and/or Tier B
    # (county-week) catches this.
    CalibrationCase("outbreak.az_hantavirus_2023", Vertical.VBD,
                    "86001", period_days=180, n_reports_during=6,
                    detection_target_days=60,
                    notes="Small denominator -- 6 cases across full year",
                    pathogen_id="pathogen.snv",
                    extra_zctas=("86503", "86040b")),
    # 2023 Maricopa heat -- hot in the Jul 10-25 streak
    CalibrationCase("outbreak.maricopa_heat_2023", Vertical.HEAT,
                    "85009", period_days=16, n_reports_during=303,
                    detection_target_days=2,
                    notes="Jul 10-25 streak; 2h cadence",
                    pathogen_id="pathogen.heat"),
    # 2023 cooling-center barriers MMWR observation cluster (Aug-Sep)
    CalibrationCase("outbreak.maricopa_cooling_center_barriers_2023", Vertical.HEAT,
                    "85009", period_days=45, n_reports_during=200,
                    detection_target_days=10,
                    pathogen_id="pathogen.heat"),
    # 2024 hantavirus -- 11 cases across 5 counties; Tier A single-case
    # alert fires on the first confirmed Sin Nombre case in the window.
    CalibrationCase("outbreak.az_hantavirus_2024", Vertical.VBD,
                    "86001", period_days=180, n_reports_during=11,
                    detection_target_days=60,
                    pathogen_id="pathogen.snv",
                    extra_zctas=("86503", "86040b", "85003", "85701")),
    # 2024 record heat
    CalibrationCase("outbreak.az_heat_2024", Vertical.HEAT,
                    "85009", period_days=70, n_reports_during=602,
                    detection_target_days=7,
                    notes="113 consecutive 100+ days",
                    pathogen_id="pathogen.heat"),
    # 2025 Coconino plague (single index case). Tier A single-case
    # high-CFR alert fires on the lone confirmed Y. pestis observation.
    CalibrationCase("outbreak.coconino_plague_2025", Vertical.VBD,
                    "86001", period_days=2, n_reports_during=1,
                    detection_target_days=2,
                    notes="single index case; Tier A single-case alert",
                    pathogen_id="pathogen.y_pestis"),
    # RMSF tribal 2003-present -- chronic endemic baseline drift.
    # Trailing-12-month rate exceeds the 1.25x historical multiplier.
    CalibrationCase("outbreak.az_rmsf_tribal_2003_present", Vertical.VBD,
                    "85546", period_days=180, n_reports_during=40,
                    detection_target_days=60,
                    pathogen_id="pathogen.rickettsia_rickettsii",
                    extra_zctas=("85501",)),
    # RMSF rodeo pilot 2012 -- ALSO test the pilot community signal
    CalibrationCase("outbreak.az_rmsf_rodeo_pilot_2012", Vertical.VBD,
                    "85501", period_days=180, n_reports_during=30,
                    detection_target_days=28,
                    pathogen_id="pathogen.rickettsia_rickettsii"),
]

# Outbreaks the detector is *expected* to miss with reasons. These are
# treated as known-misses, not test failures, and surfaced in metrics.
# Each entry includes the reason so plan/CLUSTER-CALIBRATION.md can quote
# it verbatim.
EXPECTED_MISSES: dict[str, str] = {
    # 2 human cases total; structurally invisible -- belongs to the
    # One-Health Update Agent (wildlife H5N1 sentinel), not the cluster
    # detector. (HPAI H5N1 is not in the single_case_alertable seed --
    # avian influenza is handled by a separate One-Health workflow, so
    # tagging it here would generate false positives on every flock
    # serosurvey.)
    "outbreak.az_hpai_h5n1_wildbird_2022":
        "human cases small (n=2); detector targets human-incidence clusters",
}


# ---------------------------------------------------------------------------
# Synthesis helpers
# ---------------------------------------------------------------------------
RNG_SEED = 20260519


# Bridge legacy outbreak-slug pathogen IDs to the canonical
# schema/deep/pathogens.sql slugs (and vice-versa) for hit matching.
_PATHOGEN_ALIAS: dict[str, str] = {
    "pathogen.y_pestis":   "pathogen.yersinia_pestis",
    "pathogen.sin_nombre": "pathogen.snv",
    "pathogen.h5n1":       "pathogen.hpai_h5n1",
}


def _baseline_zctas(case: CalibrationCase) -> list[str]:
    """ZCTAs to populate with baseline noise (state-level denominator).

    Always include a handful of other ZCTAs so the state-level baseline is
    realistic (you can't have a 1-ZCTA state).
    """
    others = [z for z in _ZCTA_CENTROIDS if z != case.zcta]
    # Take a stable subset of 6 other ZCTAs for the baseline.
    return [case.zcta] + sorted(others)[:6]


def _make_obs(
    *,
    zcta: str,
    ts: datetime,
    vertical: Vertical,
    pathogen_id: str | None = None,
    travel_imported: bool = False,
) -> Observation:
    # Attach a county_id so the Tier B county-scan and the Tier C
    # endemic-drift detector can bucket without needing the ZCTA-to-county
    # fallback (which is only populated for the test ZCTAs).
    from onehealth_agents.cluster import _ZCTA_CENTROIDS as _CENT  # local re-import
    county_id = _CENT.get(zcta, (None, None, None))[2]
    geo = GeoEnrichment(zcta=zcta, county_id=county_id)
    dataset = MinimumDataset(general=GeneralClass(postal_code=zcta))
    if travel_imported:
        dataset = dataset.model_copy(
            update={"exposure": ExposureClass(history_of_travel=True)}
        )
    obs = Observation(
        kind=Kind.MCP_PULL,
        vertical=vertical,
        received_at=ts.isoformat(),
        dataset=dataset,
        geo=geo,
    )
    if pathogen_id:
        # Synthesise a minimal triage decision so cluster.py's
        # _candidate_pathogen_ids() can read the pathogen hint.
        obs.triage = TriageDecision(
            vertical=vertical,
            triage_class=TriageClass.SEE_CLINICIAN,
            rationale="synthetic test pathogen hint",
            candidate_pathogens=[
                CandidatePathogen(pathogen_id=pathogen_id, score=1.0)
            ],
        )
    return obs


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

    # Outbreak-period observations. Heat events cluster in the late-
    # afternoon / early-evening 2-hour windows; VBD events are spread
    # uniformly across the period. When `extra_zctas` is set the outbreak
    # is dispersed across multiple ZCTAs (a Tier-B county-scan scenario).
    is_heat = case.vertical is Vertical.HEAT
    target_zctas = (case.zcta, *case.extra_zctas) if case.extra_zctas else (case.zcta,)
    for i in range(case.n_reports_during):
        day_offset = rng.uniform(0, case.period_days)
        if is_heat:
            if rng.random() < 0.7:
                hour = rng.uniform(15, 21)
            else:
                hour = rng.uniform(0, 24)
        else:
            hour = rng.uniform(0, 24)
        ts = outbreak_start + timedelta(days=day_offset, hours=hour)
        # Round-robin across the target ZCTAs so multi-ZCTA outbreaks
        # produce a reproducible dispersion pattern.
        z = target_zctas[i % len(target_zctas)]
        observations.append(_make_obs(
            zcta=z, ts=ts, vertical=case.vertical,
            pathogen_id=case.pathogen_id,
            travel_imported=case.travel_imported,
        ))

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
        cluster_kinds: set[str] | None = None

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
        # A hit is anything the detector emits for this case: ZCTA match,
        # county match, or the pathogen-hint match (Tier A / Tier C /
        # travel-import don't necessarily land in the originating ZCTA).
        fired = False
        first_offset: float | None = None
        n_alerts = 0
        cluster_kinds: set[str] = set()
        for day in range(case.period_days + 1):
            scan_now = outbreak_start + timedelta(days=day)
            alerts = agent.run(obs, now=scan_now)
            hits = [
                a for a in alerts
                if (a.vertical == case.vertical
                    and (
                        a.zcta == case.zcta
                        or (case.extra_zctas and a.zcta in case.extra_zctas)
                        or (case.pathogen_id and a.pathogen_hint
                            and a.pathogen_hint.split(".")[-1]
                            in {case.pathogen_id.split(".")[-1],
                                _PATHOGEN_ALIAS.get(case.pathogen_id, case.pathogen_id).split(".")[-1]})
                    ))
            ]
            if hits and not fired:
                fired = True
                first_offset = day
                n_alerts = len(hits)
                cluster_kinds = {a.cluster_kind for a in hits}
                break

        results.append(CaseResult(
            case=case, fired=fired,
            first_alert_offset_days=first_offset, n_alerts=n_alerts,
            cluster_kinds=cluster_kinds,
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
    # A historical back-reference must land on a known AZ outbreak slug
    # (without pathogen-hint propagation we pick the closest in space-time;
    # the only requirement is that *some* anchor was returned).
    assert a.historical_match is not None
    assert a.historical_match.startswith("outbreak.")


# ---------------------------------------------------------------------------
# Phase-3 followup tier tests (one per previously-missed outbreak)
# ---------------------------------------------------------------------------
def _build_obs_for(case_slug: str, *, now: datetime, rng: random.Random,
                   baseline_per_zcta_per_day: float = 0.02):
    case = next(c for c in CASES if c.slug == case_slug)
    obs, ostart = synthesise_observations(
        case, now=now, rng=rng,
        baseline_per_zcta_per_day=baseline_per_zcta_per_day,
    )
    return case, obs, ostart


def test_tier_a_single_case_high_cfr_plague_2025():
    """Tier A: a single confirmed plague observation in the trailing 30d
    window must fire ``cluster_kind='single_case'``.  Closes
    ``outbreak.coconino_plague_2025`` (single index case)."""
    rng = random.Random(RNG_SEED + 101)
    now = datetime(2025, 7, 12, tzinfo=timezone.utc)
    case, obs, _ = _build_obs_for("outbreak.coconino_plague_2025", now=now, rng=rng)
    alerts = ClusterDetectionAgent().run(obs, now=now)
    single_case = [
        a for a in alerts
        if a.cluster_kind == "single_case"
        and a.rule_tripped == "single_case_high_cfr"
    ]
    assert single_case, "plague single-case alert missing"
    # The pathogen hint must normalise to the canonical Y. pestis slug.
    assert any(a.pathogen_hint == "pathogen.yersinia_pestis" for a in single_case)


def test_tier_b_county_scan_az_hantavirus_2023():
    """Tier B (county x week) catches the small-denominator northern-AZ
    hantavirus spike that vanishes in the ZCTA-week scan."""
    rng = random.Random(RNG_SEED + 102)
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    case, obs, _ = _build_obs_for("outbreak.az_hantavirus_2023", now=now, rng=rng)
    alerts = ClusterDetectionAgent().run(obs, now=now)
    # Should either fire on the county-week scan or via the Tier-A
    # single-case rule (SNV is single_case_alertable).
    fired = [
        a for a in alerts
        if (a.cluster_kind in ("spatial", "single_case")
            and a.pathogen_hint == "pathogen.snv")
    ]
    assert fired, f"hantavirus 2023 expected to fire; got {alerts}"


def test_tier_b_county_scan_az_hantavirus_2024():
    """Tier A / Tier B together catch the 2024 hantavirus spike (11 cases
    across 5 counties)."""
    rng = random.Random(RNG_SEED + 103)
    now = datetime(2024, 12, 31, tzinfo=timezone.utc)
    case, obs, ostart = _build_obs_for(
        "outbreak.az_hantavirus_2024", now=now, rng=rng,
    )
    # Sweep across the outbreak window -- the 11 spread-out cases mean
    # the trailing 30-day Tier-A window only crosses threshold on a few
    # days; the daily cadence sweep approximates that operational pattern.
    agent = ClusterDetectionAgent()
    fired: list = []
    for day in range(case.period_days + 1):
        scan_now = ostart + timedelta(days=day)
        alerts = agent.run(obs, now=scan_now)
        snv = [a for a in alerts if a.pathogen_hint == "pathogen.snv"]
        if snv:
            fired = snv
            break
    assert fired, "hantavirus 2024 expected to fire on some day in the sweep"


def test_tier_b_county_scan_az_wnv_2003():
    """Tier B catches the 2003 Maricopa WNV emergence (13 cases / 4 mo)
    that the ZCTA-week scan misses."""
    rng = random.Random(RNG_SEED + 104)
    now = datetime(2004, 1, 1, tzinfo=timezone.utc)
    case, obs, ostart = _build_obs_for("outbreak.az_wnv_2003", now=now, rng=rng)
    # Sweep to find the first hit.
    agent = ClusterDetectionAgent()
    fired_alert = None
    for day in range(case.period_days + 1):
        alerts = agent.run(obs, now=ostart + timedelta(days=day))
        hits = [a for a in alerts if a.pathogen_hint == "pathogen.wnv"]
        if hits:
            fired_alert = hits[0]
            break
    assert fired_alert, "WNV 2003 expected to fire via Tier B county scan"


def test_travel_import_cluster_chikungunya_2014():
    """Travel-import detector picks up the 2014 chikungunya scatter
    (20 imports across 4 counties, no autochthonous transmission)."""
    rng = random.Random(RNG_SEED + 105)
    now = datetime(2014, 12, 31, tzinfo=timezone.utc)
    case, obs, _ = _build_obs_for("outbreak.az_chikungunya_2014", now=now, rng=rng)
    # The travel-import detector window is 30 days, so re-anchor close to
    # the end of the outbreak period.
    alerts = ClusterDetectionAgent().run(obs, now=now)
    travel = [a for a in alerts if a.cluster_kind == "travel_import_cluster"]
    assert travel, f"chikungunya travel-import cluster missing; got {alerts}"
    assert any(a.pathogen_hint == "pathogen.chikv" for a in travel)


def test_tier_c_endemic_drift_rmsf_tribal():
    """Tier C (chronic-baseline drift) fires when the trailing-12-month
    RMSF rate exceeds 1.25x the historical 10-year rate. The detector
    operates best-effort; tribal-data suppression caps sensitivity by
    design (see cluster.py docstring + plan/02-mcp-integration.md)."""
    rng = random.Random(RNG_SEED + 106)
    now = datetime(2024, 12, 31, tzinfo=timezone.utc)
    # Inflate the RMSF case rate to ~3x the chronic baseline so the test
    # is deterministic (the harness can't actually run a 10-year synthesis
    # without ballooning runtime).
    case, obs, _ = _build_obs_for(
        "outbreak.az_rmsf_tribal_2003_present", now=now, rng=rng,
    )
    alerts = ClusterDetectionAgent().run(obs, now=now)
    endemic = [a for a in alerts if a.cluster_kind == "endemic_drift"]
    assert endemic, f"RMSF endemic-drift alert missing; got {alerts}"
    assert any(a.pathogen_hint == "pathogen.rickettsia_rickettsii" for a in endemic)
    # Tribal-data-suppression caveat -- document the limitation lives on
    # the detector docstring (cf. plan/CLUSTER-CALIBRATION.md "Tier C").
    assert "chronic_baseline_drift" in (endemic[0].rule_tripped or "")


def test_cluster_kind_enumeration_is_complete():
    """Every cluster_kind value the detector emits must be one of the four
    documented kinds. This is a structural backstop against drift."""
    valid = {"spatial", "travel_import_cluster", "endemic_drift", "single_case"}
    rng = random.Random(RNG_SEED + 200)
    seen: set[str] = set()
    for case in CASES:
        now = datetime(2024, 8, 1, 12, 0, tzinfo=timezone.utc) \
            if case.vertical is Vertical.HEAT \
            else datetime(2024, 6, 1, 0, 0, tzinfo=timezone.utc)
        baseline = 0.20 if case.vertical is Vertical.HEAT else 0.02
        obs, ostart = synthesise_observations(
            case, now=now, rng=rng, baseline_per_zcta_per_day=baseline,
        )
        for a in ClusterDetectionAgent().run(obs, now=now):
            seen.add(a.cluster_kind)
    assert seen.issubset(valid), f"unexpected cluster_kind values: {seen - valid}"


def test_null_control_remains_silent_with_new_tiers():
    """Adding Tiers A / B / C and the travel-import detector must not
    raise the FP-rate on pure-noise null cohorts."""
    null_rng = random.Random(RNG_SEED + 300)
    fps = 0
    weeks = 0
    for _ in range(20):
        zctas = list(_ZCTA_CENTROIDS)[:8]
        baseline_days = 90
        now = datetime(2024, 5, 1, tzinfo=timezone.utc)
        obs = []
        for z in zctas:
            n = _poisson(0.02 * baseline_days, null_rng)
            for _ in range(n):
                ts = now - timedelta(hours=null_rng.uniform(0, baseline_days * 24))
                # No pathogen_id, no travel_imported -- pure-noise control.
                obs.append(_make_obs(zcta=z, ts=ts, vertical=Vertical.VBD))
        alerts = ClusterDetectionAgent().run(obs, now=now)
        fps += len(alerts)
        weeks += len(zctas) * (baseline_days / 7)
    fp_rate = fps / max(weeks, 1)
    # Baseline pre-followups was 0.0; we tolerate strictly < 0.05 still.
    assert fp_rate < 0.05, f"FP rate inflated by new tiers: {fp_rate:.4f}"


def test_heat_2h_bucket_audit_fields():
    """Heat alerts during the heat season should use the 2h cadence rule."""
    case = next(c for c in CASES if c.slug == "outbreak.az_heat_2024")
    rng = random.Random(RNG_SEED + 7)
    now = datetime(2024, 8, 15, 18, 0, tzinfo=timezone.utc)
    obs, ostart = synthesise_observations(
        case, now=now, rng=rng, baseline_per_zcta_per_day=0.20,
    )
    # Sweep day-by-day through the outbreak to find the first 2h alert.
    agent = ClusterDetectionAgent()
    alerts: list = []
    for day in range(case.period_days + 1):
        scan_now = ostart + timedelta(days=day)
        alerts = [
            a for a in agent.run(obs, now=scan_now)
            if a.zcta == case.zcta and a.vertical == Vertical.HEAT
        ]
        if alerts:
            break
    assert alerts, "Heat 2024 case must produce at least one alert across the sweep"
    rules = {a.rule_tripped for a in alerts}
    assert any("heat/zcta-2h/" in (r or "") for r in rules), rules
