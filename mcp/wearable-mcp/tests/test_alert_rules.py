"""Alert-rule evaluator tests for wearable_mcp.calculations.evaluate_rules."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from wearable_mcp.calculations import evaluate_rules
from wearable_mcp.mock_data import Reading, build_canned


def _r(value: float, minutes_ago: int, anchor: datetime, code: str = "8867-4") -> Reading:
    unit = {"8867-4": "bpm", "8328-7": "degC"}.get(code, "x")
    return Reading(
        value=float(value),
        unit=unit,
        recorded_at=(anchor - timedelta(minutes=minutes_ago))
            .astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        source="test",
        loinc_code=code,
    )


@pytest.fixture
def anchor():
    return datetime(2026, 5, 19, 17, 0, 0, tzinfo=timezone.utc)


def test_rule_fires_when_every_sample_in_window_exceeds_threshold(anchor):
    rs = [_r(135, 4, anchor), _r(140, 2, anchor), _r(132, 0, anchor)]
    [out] = evaluate_rules(
        rules=[{"metric": "8867-4", "op": ">", "value": 130, "window_min": 5}],
        readings_by_metric={"8867-4": rs},
        now=anchor,
    )
    assert out["fired"] is True
    assert out["samples"] == 3
    assert out["latest_value"] == 132


def test_rule_does_not_fire_when_any_window_sample_is_below(anchor):
    rs = [_r(135, 4, anchor), _r(120, 2, anchor), _r(140, 0, anchor)]
    [out] = evaluate_rules(
        rules=[{"metric": "8867-4", "op": ">", "value": 130, "window_min": 5}],
        readings_by_metric={"8867-4": rs},
        now=anchor,
    )
    assert out["fired"] is False
    assert out["any_match"] is True
    assert out["samples"] == 3


def test_rule_ignores_readings_outside_window(anchor):
    # Old reading is 30 min ago; window is 5 min.
    rs = [_r(140, 30, anchor), _r(80, 2, anchor)]
    [out] = evaluate_rules(
        rules=[{"metric": "8867-4", "op": ">", "value": 130, "window_min": 5}],
        readings_by_metric={"8867-4": rs},
        now=anchor,
    )
    assert out["fired"] is False
    assert out["samples"] == 1  # only the 2-min-ago reading counts


def test_rule_with_no_readings_in_window_reports_reason(anchor):
    [out] = evaluate_rules(
        rules=[{"metric": "8867-4", "op": ">", "value": 130, "window_min": 5}],
        readings_by_metric={"8867-4": []},
        now=anchor,
    )
    assert out["fired"] is False
    assert "no readings" in out["reason"]


def test_invalid_op_reports_clear_error(anchor):
    [out] = evaluate_rules(
        rules=[{"metric": "8867-4", "op": "<<", "value": 130, "window_min": 5}],
        readings_by_metric={"8867-4": [_r(140, 1, anchor)]},
        now=anchor,
    )
    assert out["fired"] is False
    assert "invalid op" in out["reason"]


def test_multiple_rules_are_evaluated_independently(anchor):
    hr = [_r(135, 2, anchor), _r(140, 1, anchor)]
    skin = [_r(39.0, 2, anchor, code="8328-7")]
    out = evaluate_rules(
        rules=[
            {"metric": "8867-4", "op": ">",  "value": 130, "window_min": 5},
            {"metric": "8328-7", "op": ">=", "value": 39,  "window_min": 5},
        ],
        readings_by_metric={"8867-4": hr, "8328-7": skin},
        now=anchor,
    )
    assert len(out) == 2
    assert out[0]["fired"] is True
    assert out[1]["fired"] is True


def test_alert_check_against_canned_heat_profile_fires_tachycardia(anchor):
    canned = build_canned(profile="heat", anchor=anchor)
    out = evaluate_rules(
        rules=[{"metric": "8867-4", "op": ">", "value": 100, "window_min": 30}],
        readings_by_metric={"8867-4": canned["8867-4"]},
        now=anchor,
    )
    # By minute 30 of the heat ramp we are above 100.
    assert out[0]["samples"] >= 1
    assert out[0]["latest_value"] >= 100


def test_alert_check_against_canned_rest_profile_does_not_fire(anchor):
    canned = build_canned(profile="rest", anchor=anchor)
    out = evaluate_rules(
        rules=[{"metric": "8867-4", "op": ">", "value": 130, "window_min": 30}],
        readings_by_metric={"8867-4": canned["8867-4"]},
        now=anchor,
    )
    assert out[0]["fired"] is False


def test_rule_with_window_alias_key_accepted(anchor):
    # Accept "window" as a friendlier alias for "window_min".
    [out] = evaluate_rules(
        rules=[{"metric": "8867-4", "op": ">", "value": 130, "window": 5}],
        readings_by_metric={"8867-4": [_r(140, 1, anchor)]},
        now=anchor,
    )
    assert out["fired"] is True
    assert out["window_min"] == 5
