"""Summary-math tests for wearable_mcp.calculations.summary_24h."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from wearable_mcp.calculations import summary_24h
from wearable_mcp.mock_data import Reading, build_canned


def _r(value: float, minutes_ago: int, anchor: datetime, code: str = "8867-4") -> Reading:
    return Reading(
        value=float(value),
        unit="bpm",
        recorded_at=(anchor - timedelta(minutes=minutes_ago))
            .astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        source="test",
        loinc_code=code,
    )


@pytest.fixture
def anchor():
    return datetime(2026, 5, 19, 17, 0, 0, tzinfo=timezone.utc)


def test_summary_min_max_mean_count_basic(anchor):
    rs = [_r(60, 60, anchor), _r(80, 30, anchor), _r(100, 5, anchor)]
    s = summary_24h(rs, now=anchor)
    assert s["count"] == 3
    assert s["min"] == 60
    assert s["max"] == 100
    assert s["mean"] == 80
    assert s["unit"] == "bpm"
    assert s["loinc_code"] == "8867-4"


def test_summary_drops_readings_older_than_24h(anchor):
    rs = [
        _r(40, 25 * 60, anchor),  # 25h ago -- excluded
        _r(70, 6 * 60,  anchor),  # 6h ago  -- included
        _r(90, 30,      anchor),  # 30m ago -- included
    ]
    s = summary_24h(rs, now=anchor)
    assert s["count"] == 2
    assert s["min"] == 70
    assert s["max"] == 90


def test_summary_handles_empty_window(anchor):
    rs = [_r(70, 25 * 60, anchor)]   # only sample is 25h old
    s = summary_24h(rs, now=anchor)
    assert s["count"] == 0
    assert s["min"] is None
    assert s["max"] is None
    assert s["mean"] is None
    assert s["last_recorded_at"] is None


def test_summary_with_canned_heat_profile_has_hr_above_baseline(anchor):
    canned = build_canned(profile="heat", anchor=anchor)
    s = summary_24h(canned["8867-4"], now=anchor)
    assert s["count"] > 0
    # Heat ramp pushes max well over 100 bpm; baseline is ~70.
    assert s["max"] >= 100
    assert s["mean"] > 60


def test_summary_with_canned_rest_profile_stays_below_threshold(anchor):
    canned = build_canned(profile="rest", anchor=anchor)
    s = summary_24h(canned["8867-4"], now=anchor)
    assert s["max"] < 100
    assert s["mean"] < 85


def test_summary_records_unit_from_first_reading(anchor):
    skin = build_canned(profile="rest", anchor=anchor)["8328-7"]
    s = summary_24h(skin, now=anchor)
    assert s["unit"] == "degC"
    assert s["loinc_code"] == "8328-7"
    # Skin temp baseline ~33.5 °C.
    assert 30 < s["mean"] < 36
