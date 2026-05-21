"""Canned-reading shape tests.

Verifies the mock data set:

* every supported LOINC has at least one reading
* every reading carries the normalised five-field shape
  (value, unit, recorded_at, source, loinc_code)
* timestamps are ISO-8601 UTC, monotonically non-decreasing per metric
* the catalog matches what the LLM is told via wearable_supported_metrics
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import pytest

from wearable_mcp.catalog import METRIC_CATALOG, SUPPORTED_LOINC
from wearable_mcp.mock_data import build_canned, filter_since


ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


@pytest.fixture
def canned():
    # Pin the anchor so every test sees the same picture.
    anchor = datetime(2026, 5, 19, 17, 0, 0, tzinfo=timezone.utc)
    return build_canned(profile="heat", anchor=anchor)


def test_every_supported_metric_has_readings(canned):
    for code in SUPPORTED_LOINC:
        assert code in canned, f"{code} missing from canned data"
        assert len(canned[code]) >= 1, f"{code} has no readings"


def test_every_reading_has_the_normalised_shape(canned):
    for code, readings in canned.items():
        for r in readings:
            d = r.to_dict()
            assert set(d.keys()) == {"value", "unit", "recorded_at", "source", "loinc_code"}
            assert d["loinc_code"] == code
            assert d["unit"] == METRIC_CATALOG[code]["unit"]
            assert isinstance(d["value"], float)
            assert ISO_RE.match(d["recorded_at"]), f"{d['recorded_at']!r} is not ISO UTC"
            assert d["source"]   # non-empty


def test_timestamps_are_monotonically_non_decreasing(canned):
    for code, readings in canned.items():
        prev = None
        for r in readings:
            t = datetime.fromisoformat(r.recorded_at.replace("Z", "+00:00"))
            if prev is not None:
                assert t >= prev, f"{code}: timestamps out of order"
            prev = t


def test_filter_since_returns_only_newer_readings(canned):
    hr = canned["8867-4"]
    midpoint = hr[len(hr) // 2].recorded_at
    after = filter_since(hr, midpoint)
    assert all(r.recorded_at >= midpoint for r in after)
    assert len(after) == len(hr) - len(hr) // 2


def test_filter_since_limit_caps_result(canned):
    hr = canned["8867-4"]
    capped = filter_since(hr, since_iso=None, limit=10)
    assert len(capped) == 10
    # When capping, we keep the most recent.
    assert capped[-1].recorded_at == hr[-1].recorded_at


def test_unsupported_profile_rejected():
    with pytest.raises(ValueError):
        build_canned(profile="moonwalk")


def test_heat_profile_shows_late_ramp_in_hr(canned):
    hr = canned["8867-4"]
    # Last reading well above first reading because of the heat ramp.
    assert hr[-1].value - hr[0].value >= 20


def test_steps_metric_is_a_single_daily_total(canned):
    steps = canned["41950-7"]
    assert len(steps) == 1
    assert steps[0].value > 0
    assert steps[0].unit == "steps"
