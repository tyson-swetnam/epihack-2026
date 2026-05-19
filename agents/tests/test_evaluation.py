"""Offline tests for ``onehealth_agents.evaluation``.

These exercise the pure-function row path so the suite stays fast
and DuckDB-free. The DuckDB-bound code path is smoke-tested in
``test_audit.py`` (the ``v_observation_timeliness`` view round-trip),
so this file focuses on:

* stat computation (median + IQR + pct-change vs baseline);
* the Phase-3 success-criterion verdict logic;
* JSON round-trip of :class:`EvaluationReport`;
* markdown rendering;
* baseline JSON loading.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from onehealth_agents.contracts import Vertical
from onehealth_agents.evaluation import (
    AGENT_TO_MILESTONE,
    Baseline,
    EvaluationConfig,
    EvaluationReport,
    MILESTONE_PAIRS,
    MilestoneEvaluator,
    PHASE3_DETECT_TO_NOTIFY_TARGET_PCT_SHORTER,
    Phase3Verdict,
    TimelinessRow,
    _percentile,
    render_markdown,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = REPO_ROOT / "evaluation" / "baseline-2024.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _t(base: datetime, *, minutes: float) -> datetime:
    return base + timedelta(minutes=minutes)


def _row(
    obs_id: str,
    vertical: Vertical,
    agency: str,
    *,
    detect_min: float | None = 0.0,
    notify_min: float | None = None,
    verify_min: float | None = None,
    lab_min: float | None = None,
    respond_min: float | None = None,
    anchor: datetime | None = None,
) -> TimelinessRow:
    """Build a TimelinessRow from minute offsets vs a fixed anchor."""
    anchor = anchor or datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    return TimelinessRow(
        observation_id=obs_id,
        vertical=vertical,
        agency=agency,
        detect_at=None if detect_min is None else _t(anchor, minutes=detect_min),
        notify_at=None if notify_min is None else _t(anchor, minutes=notify_min),
        verify_at=None if verify_min is None else _t(anchor, minutes=verify_min),
        lab_at=None if lab_min is None else _t(anchor, minutes=lab_min),
        respond_at=None if respond_min is None else _t(anchor, minutes=respond_min),
    )


def _config(**overrides) -> EvaluationConfig:
    base = dict(
        start_date=date(2026, 5, 1),
        end_date=date(2026, 9, 30),
        verticals=[Vertical.VBD, Vertical.HEAT],
        agencies=[],
        historical_baseline_year=2024,
    )
    base.update(overrides)
    return EvaluationConfig(**base)


# ---------------------------------------------------------------------------
# Module-level sanity checks
# ---------------------------------------------------------------------------
def test_agent_to_milestone_mapping_matches_audit_sql():
    # The five intake/validation/triage/enrichment/notification -> milestone
    # rows in schema/deep/audit.sql. If the SQL header ever changes, this
    # test should fail loudly.
    assert AGENT_TO_MILESTONE == {
        "intake": "detect",
        "validation": "notify",
        "triage": "verify",
        "enrichment": "lab",
        "notification": "respond",
    }


def test_percentile_handles_singletons_and_pairs():
    assert _percentile([5.0], 50.0) == pytest.approx(5.0)
    assert _percentile([10.0, 20.0], 50.0) == pytest.approx(15.0)
    # Quartiles on 1..5 with linear method: p25=2, p75=4.
    assert _percentile([1.0, 2.0, 3.0, 4.0, 5.0], 25.0) == pytest.approx(2.0)
    assert _percentile([1.0, 2.0, 3.0, 4.0, 5.0], 75.0) == pytest.approx(4.0)


def test_milestone_pairs_cover_every_adjacent_step():
    # Detect -> Notify -> Verify -> Lab -> Respond plus the end-to-end one.
    assert ("detect", "notify") in MILESTONE_PAIRS
    assert ("lab", "respond") in MILESTONE_PAIRS
    assert ("detect", "respond") in MILESTONE_PAIRS


# ---------------------------------------------------------------------------
# Baseline loader
# ---------------------------------------------------------------------------
def test_baseline_2024_loads_with_expected_intervals():
    assert BASELINE_PATH.is_file(), "baseline-2024.json must exist in evaluation/"
    baseline = Baseline.load(BASELINE_PATH)
    assert baseline.year == 2024

    # Hantavirus 2024 Detect -> Notify is roughly 175 days = 252_000 min.
    vbd_adhs = baseline.interval(Vertical.VBD, "resource.adhs", "detect_to_notify")
    assert vbd_adhs is not None
    assert 240_000 < vbd_adhs < 260_000

    # Heat 2024 detect_to_notify is the 5-day estimate (7_200 min).
    heat_mcdph = baseline.interval(
        Vertical.HEAT, "resource.mcdph_heat", "detect_to_notify"
    )
    assert heat_mcdph == pytest.approx(7200.0)


# ---------------------------------------------------------------------------
# Stat computation: synthetic rows with a known median
# ---------------------------------------------------------------------------
def test_evaluator_computes_known_median_and_iqr():
    # Five Detect -> Notify intervals: 30, 45, 60, 90, 120 minutes.
    rows = [
        _row("obs.1", Vertical.HEAT, "resource.mcdph_heat", notify_min=30),
        _row("obs.2", Vertical.HEAT, "resource.mcdph_heat", notify_min=45),
        _row("obs.3", Vertical.HEAT, "resource.mcdph_heat", notify_min=60),
        _row("obs.4", Vertical.HEAT, "resource.mcdph_heat", notify_min=90),
        _row("obs.5", Vertical.HEAT, "resource.mcdph_heat", notify_min=120),
    ]
    cfg = _config()
    evaluator = MilestoneEvaluator(baseline_path=BASELINE_PATH)
    report = evaluator.evaluate_rows(cfg, rows)

    sc = report.scorecard_for("resource.mcdph_heat", Vertical.HEAT)
    assert sc is not None
    assert sc.n_observations == 5

    detect_to_notify = sc.interval("detect_to_notify")
    assert detect_to_notify is not None
    assert detect_to_notify.n == 5
    assert detect_to_notify.median_min == pytest.approx(60.0)
    # linear-method quartiles on [30,45,60,90,120]: p25=45, p75=90; iqr=45.
    assert detect_to_notify.p25_min == pytest.approx(45.0)
    assert detect_to_notify.p75_min == pytest.approx(90.0)
    assert detect_to_notify.iqr_min == pytest.approx(45.0)

    # Baseline for HEAT/MCDPH heat is 7200 min, so 60 min is 99.17% shorter.
    assert detect_to_notify.baseline_min == pytest.approx(7200.0)
    assert detect_to_notify.pct_shorter_vs_baseline == pytest.approx(
        (7200.0 - 60.0) / 7200.0 * 100, rel=1e-4
    )
    assert detect_to_notify.pct_change_vs_baseline == pytest.approx(
        (60.0 - 7200.0) / 7200.0 * 100, rel=1e-4
    )


def test_evaluator_handles_empty_intervals_for_unfired_milestones():
    # Detect fires but Notify never does; the pair should report n=0, no median.
    rows = [
        _row("obs.1", Vertical.VBD, "resource.adhs", notify_min=None, respond_min=240),
    ]
    cfg = _config(verticals=[Vertical.VBD])
    evaluator = MilestoneEvaluator(baseline_path=BASELINE_PATH)
    report = evaluator.evaluate_rows(cfg, rows)

    sc = report.scorecard_for("resource.adhs", Vertical.VBD)
    assert sc is not None
    dn = sc.interval("detect_to_notify")
    assert dn is not None
    assert dn.n == 0
    assert dn.median_min is None
    # Baseline is still surfaced even when there's nothing to compare to.
    assert dn.baseline_min is not None
    assert dn.pct_change_vs_baseline is None


# ---------------------------------------------------------------------------
# Phase-3 success-criterion verdicts
# ---------------------------------------------------------------------------
def test_phase3_verdict_passes_when_median_clears_30pct_threshold():
    # Baseline HEAT/MCDPH = 7_200 min. 30% shorter is <= 5_040 min.
    # Five intervals all at 3_000 min => clearly passes.
    rows = [
        _row(f"obs.{i}", Vertical.HEAT, "resource.mcdph_heat", notify_min=3000)
        for i in range(5)
    ]
    cfg = _config(verticals=[Vertical.HEAT])
    evaluator = MilestoneEvaluator(baseline_path=BASELINE_PATH)
    report = evaluator.evaluate_rows(cfg, rows)

    verdicts = [
        v for v in report.phase3_verdicts
        if v.agency == "resource.mcdph_heat" and v.vertical == Vertical.HEAT
    ]
    assert len(verdicts) == 1
    v = verdicts[0]
    assert v.passes is True
    assert v.target_pct_shorter == PHASE3_DETECT_TO_NOTIFY_TARGET_PCT_SHORTER
    assert v.pct_shorter is not None
    assert v.pct_shorter >= PHASE3_DETECT_TO_NOTIFY_TARGET_PCT_SHORTER


def test_phase3_verdict_fails_when_median_falls_short():
    # Baseline = 7_200 min. Notify at 5_500 min is only ~23.6% shorter -> fail.
    rows = [
        _row(f"obs.{i}", Vertical.HEAT, "resource.mcdph_heat", notify_min=5500)
        for i in range(5)
    ]
    cfg = _config(verticals=[Vertical.HEAT])
    evaluator = MilestoneEvaluator(baseline_path=BASELINE_PATH)
    report = evaluator.evaluate_rows(cfg, rows)

    v = next(
        v for v in report.phase3_verdicts
        if v.agency == "resource.mcdph_heat" and v.vertical == Vertical.HEAT
    )
    assert v.passes is False
    assert v.pct_shorter is not None
    assert v.pct_shorter < PHASE3_DETECT_TO_NOTIFY_TARGET_PCT_SHORTER
    assert "shorter" in v.reason


def test_phase3_verdict_fails_when_no_observations_in_window():
    # Detect timestamps outside the window are filtered out.
    rows = [
        _row(
            "obs.1",
            Vertical.HEAT,
            "resource.mcdph_heat",
            notify_min=60,
            # Anchor in 2020 -- well before the 2026 window in _config().
            anchor=datetime(2020, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
        )
    ]
    cfg = _config(verticals=[Vertical.HEAT], agencies=["resource.mcdph_heat"])
    evaluator = MilestoneEvaluator(baseline_path=BASELINE_PATH)
    report = evaluator.evaluate_rows(cfg, rows)

    v = next(
        v for v in report.phase3_verdicts
        if v.agency == "resource.mcdph_heat" and v.vertical == Vertical.HEAT
    )
    assert v.passes is False
    assert "no Detect" in v.reason


# ---------------------------------------------------------------------------
# JSON round-trip
# ---------------------------------------------------------------------------
def test_evaluation_report_round_trips_through_json():
    rows = [
        _row("obs.1", Vertical.VBD, "resource.adhs", notify_min=15_000),
        _row("obs.2", Vertical.VBD, "resource.adhs", notify_min=12_000, respond_min=30_000),
        _row("obs.3", Vertical.HEAT, "resource.mcdph_heat", notify_min=4_000),
    ]
    cfg = _config()
    evaluator = MilestoneEvaluator(baseline_path=BASELINE_PATH)
    report = evaluator.evaluate_rows(cfg, rows)

    encoded = report.model_dump_json()
    payload = json.loads(encoded)
    # Top-level structural shape:
    assert "config" in payload
    assert "scorecards" in payload
    assert "phase3_verdicts" in payload
    assert payload["total_observations"] == 3

    # Re-hydrate and confirm equivalence.
    rehydrated = EvaluationReport.model_validate(payload)
    assert rehydrated.config.start_date == cfg.start_date
    assert rehydrated.config.end_date == cfg.end_date
    assert rehydrated.total_observations == 3
    assert {sc.agency for sc in rehydrated.scorecards} == {
        "resource.adhs",
        "resource.mcdph_heat",
    }
    # Stats should survive the trip identically.
    orig_vbd = report.scorecard_for("resource.adhs", Vertical.VBD)
    new_vbd = rehydrated.scorecard_for("resource.adhs", Vertical.VBD)
    assert orig_vbd and new_vbd
    assert orig_vbd.interval("detect_to_notify").median_min == pytest.approx(
        new_vbd.interval("detect_to_notify").median_min
    )


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------
def test_render_markdown_emits_expected_sections():
    rows = [
        _row("obs.1", Vertical.HEAT, "resource.mcdph_heat", notify_min=3000),
        _row("obs.2", Vertical.HEAT, "resource.mcdph_heat", notify_min=3500),
    ]
    cfg = _config(verticals=[Vertical.HEAT], agencies=["resource.mcdph_heat"])
    evaluator = MilestoneEvaluator(baseline_path=BASELINE_PATH)
    report = evaluator.evaluate_rows(cfg, rows)

    md = render_markdown(report)
    assert "Figure-3 Timeliness Scorecard" in md
    assert "Phase-3 success criterion" in md
    assert "Per-agency, per-vertical interval scorecards" in md
    assert "resource.mcdph_heat" in md
    assert "detect_to_notify" in md
    assert "heat" in md
    # The verdict cell is one of PASS / FAIL.
    assert "PASS" in md or "FAIL" in md


# ---------------------------------------------------------------------------
# Config-pinned agencies appear even when n=0
# ---------------------------------------------------------------------------
def test_pinned_agencies_show_up_as_empty_cells():
    cfg = _config(
        verticals=[Vertical.VBD],
        agencies=["resource.adhs", "resource.coconino_hhs"],
    )
    evaluator = MilestoneEvaluator(baseline_path=BASELINE_PATH)
    report = evaluator.evaluate_rows(cfg, rows=[])

    agencies_seen = {sc.agency for sc in report.scorecards}
    assert agencies_seen == {"resource.adhs", "resource.coconino_hhs"}
    # All cells have n=0 but baseline is still attached.
    for sc in report.scorecards:
        dn = sc.interval("detect_to_notify")
        assert dn is not None
        assert dn.n == 0
        assert dn.baseline_min is not None
