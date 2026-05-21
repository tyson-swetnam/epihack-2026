"""Tests for the FastMCP tool layer.

Exercises the public surface of `adhs_mcp.client.ADHSClient` (which is
what the FastMCP tools delegate to) and round-trips every row through
the pydantic models defined in `adhs_mcp.server` so a shape regression
fails CI loudly. All offline -- no network, no credentials.
"""

from __future__ import annotations

import pytest

from adhs_mcp.client import ADHSClient
from adhs_mcp.server import (
    ArbovirusSurveillanceRow,
    HeatMortalityRow,
    RecentCaseRow,
    ReportableConditionRow,
)


# --------------------------------------------------------------- fixtures
@pytest.fixture
def client() -> ADHSClient:
    """Fresh canned-mode client (no ADHS_BACKEND_URL)."""
    return ADHSClient(backend_url=None)


# ------------------------------------------------------------ recent_cases
def test_recent_cases_filters_by_pathogen(client):
    wnv = client.recent_cases(pathogen="WNV")
    hps = client.recent_cases(pathogen="HANTAVIRUS")
    assert len(wnv) == 12
    assert len(hps) >= 2
    # No cross-talk between pathogens
    assert all(r["county"] == "Maricopa" for r in wnv)


def test_recent_cases_filters_by_county(client):
    rows = client.recent_cases(pathogen="HANTAVIRUS", county="coconino")
    assert rows
    assert all(r["county"].lower() == "coconino" for r in rows)


def test_recent_cases_filters_by_year(client):
    rows = client.recent_cases(pathogen="WNV", surv_year=2024)
    assert len(rows) == 12
    none_rows = client.recent_cases(pathogen="WNV", surv_year=1999)
    assert none_rows == []


def test_recent_cases_combined_filters(client):
    rows = client.recent_cases(
        pathogen="HANTAVIRUS", county="Apache", surv_year=2024,
    )
    assert all(r["county"] == "Apache" for r in rows)
    assert all(r["week_of"].startswith("2024-") for r in rows)


def test_recent_cases_rejects_unknown_pathogen(client):
    with pytest.raises(ValueError):
        client.recent_cases(pathogen="EBOLA")


def test_recent_cases_pydantic_round_trip(client):
    rows = client.recent_cases(pathogen="WNV")
    for r in rows:
        model = RecentCaseRow.model_validate(r)
        # Round-tripping back to a dict must give the same shape.
        assert model.model_dump().keys() == r.keys()
        assert model.confirmed >= 0


# ----------------------------------------------- heat_mortality_summary
def test_heat_mortality_summary_default_returns_2013_2024(client):
    rows = client.heat_mortality_summary()
    assert [r["year"] for r in rows] == list(range(2013, 2025))


def test_heat_mortality_summary_filters_by_year(client):
    rows = client.heat_mortality_summary(year=2023)
    assert len(rows) == 1
    assert rows[0]["statewide_deaths"] == 990


def test_heat_mortality_summary_unknown_year_returns_empty(client):
    assert client.heat_mortality_summary(year=1900) == []


def test_heat_mortality_pydantic_round_trip(client):
    rows = client.heat_mortality_summary()
    for r in rows:
        model = HeatMortalityRow.model_validate(r)
        assert model.statewide_deaths >= model.maricopa_deaths
        # statewide must equal the per-county sum.
        s = (
            model.maricopa_deaths
            + model.pima_deaths
            + model.yuma_deaths
            + model.other_counties_deaths
        )
        assert s == model.statewide_deaths


# ------------------------------------ arbovirus_surveillance_summary
def test_arbovirus_summary_returns_all_rows_by_default(client):
    rows = client.arbovirus_surveillance()
    assert len(rows) >= 14
    # All rows carry both Maricopa and Pima
    counties = {r["county"] for r in rows}
    assert "Maricopa" in counties
    assert "Pima" in counties


def test_arbovirus_summary_filters_by_county(client):
    rows = client.arbovirus_surveillance(county="pima")
    assert rows
    assert all(r["county"].lower() == "pima" for r in rows)


def test_arbovirus_summary_filters_by_year(client):
    rows_24 = client.arbovirus_surveillance(surv_year=2024)
    assert rows_24
    assert all(r["surv_year"] == 2024 for r in rows_24)
    assert client.arbovirus_surveillance(surv_year=1999) == []


def test_arbovirus_summary_pydantic_round_trip(client):
    rows = client.arbovirus_surveillance(county="Maricopa")
    for r in rows:
        model = ArbovirusSurveillanceRow.model_validate(r)
        assert model.positive_pools <= model.pools_tested
        if model.sentinel_chicken_seroconversions is not None:
            assert model.sentinel_chicken_seroconversions >= 0


# -------------------------------------------- vbzd_program / heat network
def test_vbzd_program_shape(client):
    program = client.vbzd_program()
    assert program["url"].startswith("https://www.azdhs.gov/")
    assert "vector-borne-zoonotic-diseases" in program["url"]
    assert "WNV" in program["pathogens_monitored"]
    assert "HANTAVIRUS" in program["pathogens_monitored"]
    assert "RABIES" in program["pathogens_monitored"]
    assert program["primary_labs"]
    assert all("name" in lab and "role" in lab for lab in program["primary_labs"])
    assert "arbovirus_summary" in program["reporting_cadence"]


def test_heat_preparedness_network_shape(client):
    hpn = client.heat_preparedness_network()
    assert hpn["arcgis_experience_url"] == (
        "https://experience.arcgis.com/experience/c5bdf9ab90894e1baa5860c450dedb3b"
    )
    season = hpn["season_window"]
    assert season["start"] == "May 1"
    assert season["end"] == "September 30"
    # Cross-link to mag-hrn-mcp for detailed records
    assert "mag-hrn-mcp" in hpn["detailed_records_note"]


# -------------------------------------------- reportable_conditions shape
def test_reportable_conditions_pydantic_round_trip(client):
    rows = client.reportable_conditions()
    assert rows
    for r in rows:
        model = ReportableConditionRow.model_validate(r)
        assert model.condition
        assert model.az_reporting_rule


# ----------------------------------------- HTTP-backend fail-loud contract
def test_http_backend_raises_until_real_api_exists():
    c = ADHSClient(backend_url="https://example.invalid/api")
    assert c.mode == "http"
    with pytest.raises(NotImplementedError):
        c.recent_cases(pathogen="WNV")
    with pytest.raises(NotImplementedError):
        c.heat_mortality_summary()
    with pytest.raises(NotImplementedError):
        c.arbovirus_surveillance()
    with pytest.raises(NotImplementedError):
        c.vbzd_program()
    with pytest.raises(NotImplementedError):
        c.heat_preparedness_network()
    with pytest.raises(NotImplementedError):
        c.reportable_conditions()
