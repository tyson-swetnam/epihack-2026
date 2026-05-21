"""Filtering tests for utility-assistance, crisis-referrals, and cooling
centers from the 211 Arizona mock backend.

Each test exercises the filter behaviour the EnrichmentAgent /
NotificationAgent depend on: postal-code -> county routing, ``kind``
filter on utility assistance, ``topic`` filter on crisis referrals,
and ``urgency`` -> radius on cooling-center lookup.
"""

from __future__ import annotations

import pytest

from az211_mcp.client import SOURCE_MOCK, Az211Client


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Az211Client:
    monkeypatch.delenv("AZ211_BACKEND_URL", raising=False)
    return Az211Client()


# --- utility-assistance filtering -----------------------------------------
def test_utility_assistance_returns_same_county_first(client: Az211Client) -> None:
    # 85003 is downtown Phoenix -> Maricopa.
    rows = client.list_utility_assistance("85003", kind="any")
    assert rows[0]["county"] == "Maricopa"
    assert all(r["source"] == SOURCE_MOCK for r in rows)


def test_utility_assistance_pima_routing(client: Az211Client) -> None:
    # 85701 is Tucson -> Pima.
    rows = client.list_utility_assistance("85701", kind="any")
    assert rows[0]["county"] == "Pima"


def test_utility_assistance_yuma_routing(client: Az211Client) -> None:
    # 85364 is Yuma proper. Explicit override in county_for_zip.
    rows = client.list_utility_assistance("85364", kind="any")
    assert rows[0]["county"] == "Yuma"


def test_utility_assistance_coconino_routing(client: Az211Client) -> None:
    # 86001 is Flagstaff -> Coconino.
    rows = client.list_utility_assistance("86001", kind="any")
    assert rows[0]["county"] == "Coconino"


def test_utility_assistance_emergency_ac_repair_filter(client: Az211Client) -> None:
    rows = client.list_utility_assistance("85003", kind="emergency_ac_repair")
    assert len(rows) >= 1
    for r in rows:
        assert "emergency_ac_repair" in r["services"]


def test_utility_assistance_weatherization_filter(client: Az211Client) -> None:
    rows = client.list_utility_assistance("85701", kind="weatherization")
    assert len(rows) >= 1
    for r in rows:
        assert "weatherization" in r["services"]


def test_utility_assistance_unknown_zip_falls_back_to_maricopa(
    client: Az211Client,
) -> None:
    rows = client.list_utility_assistance("99999", kind="any")
    # The fallback prevents empty results in demos.
    assert len(rows) >= 1
    assert rows[0]["county"] == "Maricopa"


# --- crisis-referral filtering --------------------------------------------
def test_crisis_referrals_heat_topic(client: Az211Client) -> None:
    rows = client.list_crisis_referrals("85003", topic="heat")
    assert len(rows) >= 1
    for r in rows:
        assert r["topic"] == "heat"
    # 211 Arizona's main heat-relief number must be present.
    assert any(r["phone"] == "2-1-1" for r in rows if r.get("phone"))


def test_crisis_referrals_behavioral_health_topic(client: Az211Client) -> None:
    rows = client.list_crisis_referrals("85003", topic="behavioral_health")
    phones = {r.get("phone") for r in rows}
    assert "988" in phones
    # Solari Crisis Response Network is the partner behind 211 AZ.
    assert any("solari" in r["name"].lower() for r in rows)


def test_crisis_referrals_all_topics_returns_every_topic(
    client: Az211Client,
) -> None:
    rows = client.list_crisis_referrals("85003", topic="all")
    topics = {r["topic"] for r in rows}
    assert topics == {"heat", "housing", "food", "behavioral_health"}


# --- cooling-center referral / urgency -> radius --------------------------
def test_cooling_center_nearby_sorted_by_distance(client: Az211Client) -> None:
    # Downtown Phoenix.
    rows = client.nearby_cooling_centers(33.4458, -112.0938, urgency="standard")
    assert len(rows) >= 1
    distances = [r["distance_km"] for r in rows]
    assert distances == sorted(distances)
    assert all(r["source"] == SOURCE_MOCK for r in rows)


def test_cooling_center_emergency_urgency_returns_at_least_one(
    client: Az211Client,
) -> None:
    # Even with a tight 10 km emergency radius, the nearest result
    # must be returned so the agent isn't left empty-handed.
    rows = client.nearby_cooling_centers(35.1986, -111.6519, urgency="emergency")
    assert len(rows) >= 1
