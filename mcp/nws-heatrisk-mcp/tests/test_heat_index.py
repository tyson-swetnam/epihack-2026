"""Unit tests for the NWS heat-index regression.

Canonical values from the WPC documentation at
https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml and the
standard NWS heat-index lookup table at
https://www.weather.gov/safety/heat-index .

The regression itself is good to about +/- 1.3 deg F vs. the
Steadman table, so we tolerate +/- 2 deg F in the checks.
"""

from nws_heatrisk_mcp.heat_index import heat_index_category, heat_index_f


def _approx(a: float, b: float, tol: float = 2.0) -> bool:
    return abs(a - b) <= tol


def test_below_threshold_returns_simple_average():
    # T < 80, RH any -> NWS just uses the simple average, which lands
    # very close to T itself for moderate humidities.
    hi = heat_index_f(70.0, 50.0)
    assert _approx(hi, 70.0, tol=2.0)


def test_canonical_80f_40rh():
    # Classic textbook value: T=80 F, RH=40% -> HI ~ 80 F.
    hi = heat_index_f(80.0, 40.0)
    assert _approx(hi, 80.0, tol=2.0)


def test_canonical_90f_70rh():
    # T=90 F, RH=70% -> table value ~ 106 F.
    hi = heat_index_f(90.0, 70.0)
    assert _approx(hi, 106.0, tol=2.0)


def test_canonical_100f_50rh():
    # T=100 F, RH=50% -> WPC example value ~ 119 F.
    hi = heat_index_f(100.0, 50.0)
    assert _approx(hi, 119.0, tol=2.0)


def test_canonical_110f_40rh():
    # T=110 F, RH=40% -> table value ~ 136 F.
    hi = heat_index_f(110.0, 40.0)
    assert _approx(hi, 136.0, tol=2.0)


def test_low_humidity_adjustment_applied():
    # At T=100, RH=10% the low-humidity adjustment should *lower* HI
    # vs. the bare regression. We just check it's reasonable.
    hi = heat_index_f(100.0, 10.0)
    # Table: ~95 F at 100 F / 10% RH.
    assert _approx(hi, 95.0, tol=3.0)


def test_high_humidity_adjustment_applied():
    # At T=85, RH=95% the high-humidity adjustment should *raise* HI.
    hi = heat_index_f(85.0, 95.0)
    # Table: ~107 F.
    assert _approx(hi, 107.0, tol=3.0)


def test_category_bands():
    assert heat_index_category(75.0) == "none"
    assert heat_index_category(85.0) == "Caution"
    assert heat_index_category(95.0) == "Extreme Caution"
    assert heat_index_category(110.0) == "Danger"
    assert heat_index_category(130.0) == "Extreme Danger"


def test_rh_validation():
    import pytest

    with pytest.raises(ValueError):
        heat_index_f(90.0, 150.0)
    with pytest.raises(ValueError):
        heat_index_f(90.0, -5.0)
