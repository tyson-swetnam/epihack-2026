"""Search-tool tests for ``mag-hrn-mcp``.

Covers (fully offline):

- Haversine distance math against a hand-computed reference.
- The ``open_now`` filter (real hours window, day-of-week-aware).
- The ``pets_ok`` filter.
- The ``services`` filter (set-intersection semantics).
- Free-text search across name/address/notes/services.
- The ``off_season`` contract (May 1 - Sep 30).
- The mock dataset's known geography (downtown Phoenix surfaces
  Burton Barr and St. Vincent de Paul within 5 km).
- The canonical row shape (the keys plan/02 specifies).
"""

from __future__ import annotations

import asyncio

import pytest

from mag_hrn_mcp.client import (
    MAGHRNClient,
    MOCK_CENTERS,
    haversine_km,
    in_operating_season,
    is_open_at,
)


# A clearly in-season date used across tests: a Wednesday in June at
# noon. Wednesday is "Wed" in our day-name vocabulary; noon is open for
# essentially every site in the canned dataset.
NOON_WEDNESDAY_JUNE = "2026-06-10T12:00:00"
SUNDAY_MORNING_JUNE = "2026-06-14T08:00:00"     # Sunday early -- many closed
MIDNIGHT_JUNE = "2026-06-10T02:00:00"           # ~all closed
OFF_SEASON_DECEMBER = "2026-12-15T12:00:00"     # off-season


# ----------------------------------------------------------------- math
def test_haversine_zero_distance():
    assert haversine_km(33.45, -112.07, 33.45, -112.07) == pytest.approx(0.0, abs=1e-9)


def test_haversine_known_distance_phoenix_to_tempe():
    # Burton Barr (33.4734, -112.0740) -> Tempe Public Library
    # (33.3870, -111.9263). Hand-computed great-circle distance is
    # ~16.5 km; allow generous tolerance for tiny lat/lon rounding.
    d = haversine_km(33.4734, -112.0740, 33.3870, -111.9263)
    assert 15.5 < d < 17.5


def test_haversine_symmetric():
    a = haversine_km(33.45, -112.07, 33.50, -112.10)
    b = haversine_km(33.50, -112.10, 33.45, -112.07)
    assert a == pytest.approx(b, rel=1e-9)


# ------------------------------------------------------------- hours
def test_is_open_at_inside_window():
    hours = {"Wed": ["10:00", "20:00"]}
    from datetime import datetime

    when = datetime.fromisoformat("2026-06-10T12:00:00")
    assert is_open_at(hours, when) is True


def test_is_open_at_before_open():
    hours = {"Wed": ["10:00", "20:00"]}
    from datetime import datetime

    when = datetime.fromisoformat("2026-06-10T08:00:00")
    assert is_open_at(hours, when) is False


def test_is_open_at_closed_day():
    hours = {"Sun": "closed"}
    from datetime import datetime

    when = datetime.fromisoformat("2026-06-14T12:00:00")
    assert is_open_at(hours, when) is False


# ---------------------------------------------------------- season
def test_in_operating_season_summer():
    from datetime import datetime

    assert in_operating_season(datetime.fromisoformat(NOON_WEDNESDAY_JUNE)) is True


def test_off_season_december():
    from datetime import datetime

    assert in_operating_season(datetime.fromisoformat(OFF_SEASON_DECEMBER)) is False


def test_off_season_search_returns_empty():
    client = MAGHRNClient(feature_service_url=None)
    out = asyncio.run(
        client.search_centers(
            lat=33.45,
            lon=-112.07,
            radius_km=50,
            open_now=False,
            now_iso=OFF_SEASON_DECEMBER,
        )
    )
    assert out["off_season"] is True
    assert out["centers"] == []


# --------------------------------------------------- mock dataset shape
def test_mock_dataset_size_and_keys():
    assert 8 <= len(MOCK_CENTERS) <= 30
    required = {
        "id", "name", "address", "city", "postal_code",
        "lat", "lon", "services", "pets_ok", "hours",
    }
    for c in MOCK_CENTERS:
        assert required <= c.keys(), f"missing keys in {c['id']}"
        assert isinstance(c["services"], list)
        assert all(s in ("cooling", "hydration", "respite", "donation")
                   for s in c["services"])
        # Maricopa County: lat ~33-34, lon ~-112 to -113.
        assert 33.0 < c["lat"] < 34.0
        assert -113.0 < c["lon"] < -111.5
        # Postal codes are 5-digit AZ codes (85xxx).
        assert c["postal_code"].startswith("85")


# ------------------------------------------------------ row shape
def test_search_row_carries_documented_keys():
    client = MAGHRNClient(feature_service_url=None)
    out = asyncio.run(
        client.search_centers(
            lat=33.4500,
            lon=-112.0700,
            radius_km=50,
            open_now=False,
            now_iso=NOON_WEDNESDAY_JUNE,
        )
    )
    assert out["mode"] == "mock"
    assert out["total"] >= 1
    row = out["centers"][0]
    expected = {
        "id", "name", "address", "city", "postal_code",
        "lat", "lon", "services", "hours_today",
        "pets_ok", "distance_km", "kg_node_id",
    }
    assert expected <= row.keys()
    # kg_node_id is reserved for the graph integration; null until then.
    assert row["kg_node_id"] is None


# ------------------------------------------------------ geo + radius
def test_downtown_phoenix_finds_burton_barr_within_5km():
    """Burton Barr (33.4734, -112.0740) is ~3 km from the downtown
    Civic Plaza point used by Scenario C."""
    client = MAGHRNClient(feature_service_url=None)
    out = asyncio.run(
        client.search_centers(
            lat=33.4480,
            lon=-112.0740,
            radius_km=5.0,
            open_now=False,
            now_iso=NOON_WEDNESDAY_JUNE,
        )
    )
    ids = [r["id"] for r in out["centers"]]
    assert "mag.hrn.mock.0001" in ids


def test_radius_filter_excludes_far_away():
    """A 1 km radius around Burton Barr must not include Goodyear
    (~25 km west)."""
    client = MAGHRNClient(feature_service_url=None)
    out = asyncio.run(
        client.search_centers(
            lat=33.4734,
            lon=-112.0740,
            radius_km=1.0,
            open_now=False,
            now_iso=NOON_WEDNESDAY_JUNE,
        )
    )
    ids = [r["id"] for r in out["centers"]]
    assert "mag.hrn.mock.0012" not in ids  # Goodyear


def test_results_sorted_by_distance():
    client = MAGHRNClient(feature_service_url=None)
    out = asyncio.run(
        client.search_centers(
            lat=33.4500,
            lon=-112.0700,
            radius_km=50,
            open_now=False,
            now_iso=NOON_WEDNESDAY_JUNE,
        )
    )
    dists = [r["distance_km"] for r in out["centers"]]
    assert dists == sorted(dists)


# ----------------------------------------------------- open_now filter
def test_open_now_filter_drops_closed():
    """At 02:00 every mock center is closed; the filter must empty."""
    client = MAGHRNClient(feature_service_url=None)
    out = asyncio.run(
        client.search_centers(
            lat=33.45, lon=-112.07,
            radius_km=50, open_now=True, now_iso=MIDNIGHT_JUNE,
        )
    )
    assert out["total"] == 0


def test_open_now_off_still_returns_centers():
    client = MAGHRNClient(feature_service_url=None)
    out = asyncio.run(
        client.search_centers(
            lat=33.45, lon=-112.07,
            radius_km=50, open_now=False, now_iso=MIDNIGHT_JUNE,
        )
    )
    assert out["total"] >= 1


def test_open_now_respects_sunday_closures():
    client = MAGHRNClient(feature_service_url=None)
    out = asyncio.run(
        client.search_centers(
            lat=33.45, lon=-112.07,
            radius_km=50, open_now=True, now_iso=SUNDAY_MORNING_JUNE,
        )
    )
    ids = [r["id"] for r in out["centers"]]
    # Mesa Main closes on Sunday in our mock; must not appear.
    assert "mag.hrn.mock.0003" not in ids


# ----------------------------------------------------- pets_ok filter
def test_pets_ok_true_filters_to_pet_friendly():
    client = MAGHRNClient(feature_service_url=None)
    out = asyncio.run(
        client.search_centers(
            lat=33.45, lon=-112.07,
            radius_km=50, open_now=False, pets_ok=True,
            now_iso=NOON_WEDNESDAY_JUNE,
        )
    )
    assert out["total"] >= 1
    assert all(r["pets_ok"] is True for r in out["centers"])


def test_pets_ok_false_excludes_pet_friendly():
    client = MAGHRNClient(feature_service_url=None)
    out = asyncio.run(
        client.search_centers(
            lat=33.45, lon=-112.07,
            radius_km=50, open_now=False, pets_ok=False,
            now_iso=NOON_WEDNESDAY_JUNE,
        )
    )
    assert out["total"] >= 1
    assert all(r["pets_ok"] is False for r in out["centers"])


# ---------------------------------------------------- services filter
def test_services_filter_respite_only():
    client = MAGHRNClient(feature_service_url=None)
    out = asyncio.run(
        client.search_centers(
            lat=33.45, lon=-112.07,
            radius_km=50, open_now=False, services=["respite"],
            now_iso=NOON_WEDNESDAY_JUNE,
        )
    )
    assert out["total"] >= 1
    for r in out["centers"]:
        assert "respite" in r["services"]


def test_services_filter_donation_only():
    client = MAGHRNClient(feature_service_url=None)
    out = asyncio.run(
        client.search_centers(
            lat=33.45, lon=-112.07,
            radius_km=50, open_now=False, services=["donation"],
            now_iso=NOON_WEDNESDAY_JUNE,
        )
    )
    for r in out["centers"]:
        assert "donation" in r["services"]


# -------------------------------------------------------- text search
def test_text_search_finds_libraries():
    client = MAGHRNClient(feature_service_url=None)
    out = asyncio.run(
        client.search_by_text(query="library", now_iso=NOON_WEDNESDAY_JUNE)
    )
    assert out["total"] >= 3
    for r in out["centers"]:
        haystack = " ".join(
            [r["name"] or "", r["address"] or "", r["city"] or ""]
        ).lower()
        assert "library" in haystack


def test_text_search_near_hint_sorts_by_distance():
    client = MAGHRNClient(feature_service_url=None)
    out = asyncio.run(
        client.search_by_text(
            query="library",
            near=(33.4480, -112.0740),  # downtown Phoenix
            now_iso=NOON_WEDNESDAY_JUNE,
        )
    )
    dists = [r["distance_km"] for r in out["centers"] if r["distance_km"] is not None]
    assert dists == sorted(dists)


def test_text_search_no_match_empty():
    client = MAGHRNClient(feature_service_url=None)
    out = asyncio.run(
        client.search_by_text(
            query="zzzz-not-a-real-token", now_iso=NOON_WEDNESDAY_JUNE
        )
    )
    assert out["total"] == 0


# ----------------------------------------------------- center detail
def test_center_detail_known_id():
    client = MAGHRNClient(feature_service_url=None)
    out = asyncio.run(client.center_detail("mag.hrn.mock.0001"))
    assert out["found"] is True
    assert out["name"] == "Burton Barr Central Library"
    assert "Mon" in out["hours"]
    assert out["kg_node_id"] is None


def test_center_detail_unknown_id():
    client = MAGHRNClient(feature_service_url=None)
    out = asyncio.run(client.center_detail("mag.hrn.mock.does-not-exist"))
    assert out["found"] is False


# ----------------------------------------------------- list open now
def test_list_open_now_in_season():
    client = MAGHRNClient(feature_service_url=None)
    out = asyncio.run(client.list_open_now(now_iso=NOON_WEDNESDAY_JUNE))
    assert out["mode"] == "mock"
    assert out["total"] >= 1


def test_list_open_now_off_season():
    client = MAGHRNClient(feature_service_url=None)
    out = asyncio.run(client.list_open_now(now_iso=OFF_SEASON_DECEMBER))
    assert out["off_season"] is True
    assert out["centers"] == []


# -------------------------------------------------- explicit feature URL
def test_client_mode_flips_on_feature_service_url():
    """If MAG_HRN_FEATURE_SERVICE_URL is passed, mode should be `feed`."""
    c = MAGHRNClient(
        feature_service_url="https://example.test/arcgis/rest/services/x"
    )
    assert c.mode == "feed"
