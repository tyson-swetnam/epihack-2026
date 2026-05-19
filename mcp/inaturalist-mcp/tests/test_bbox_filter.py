"""Tests for bounding-box + radius filtering on the canned dataset.

The canned observations sit at well-known AZ coordinates (Tucson,
Phoenix, Flagstaff, Yuma, etc.). These tests draw bounding boxes
around individual cities and verify only the observations within the
box come back, then exercise the radius wrapper to confirm the
haversine filter sorts results by distance.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("INAT_OFFLINE", "1")
os.environ.setdefault("INAT_USER_AGENT", "inaturalist-mcp-tests/0.1 (ci@example.org)")

from inaturalist_mcp.canned_data import (  # noqa: E402
    CANNED_OBSERVATIONS,
    TAXON_RHIPICEPHALUS_SANGUINEUS,
)
from inaturalist_mcp.client import (  # noqa: E402
    INaturalistClient,
    haversine_km,
    radius_to_bbox,
)


@pytest.fixture
def client() -> INaturalistClient:
    return INaturalistClient(offline=True)


# Tucson centroid.
TUCSON_LAT, TUCSON_LON = 32.2226, -110.9747


@pytest.mark.asyncio
async def test_bbox_around_tucson_only_returns_tucson_rows(client):
    """A tight box around Tucson returns only the Tucson observations."""
    # ~0.1deg box around Tucson -- excludes Phoenix (~1.2 degrees north).
    out = await client.observations_bbox(
        min_lon=TUCSON_LON - 0.1, min_lat=TUCSON_LAT - 0.1,
        max_lon=TUCSON_LON + 0.1, max_lat=TUCSON_LAT + 0.1,
        taxon="ticks",
        days=3650,
        quality_grade="research",
        limit=200,
    )
    assert out["source"] == "canned"
    assert out["results"], "expected at least one tick observation near Tucson"
    for row in out["results"]:
        assert TUCSON_LON - 0.1 <= row["lon"] <= TUCSON_LON + 0.1
        assert TUCSON_LAT - 0.1 <= row["lat"] <= TUCSON_LAT + 0.1
        # No Phoenix rows snuck in.
        assert "Phoenix" not in (row.get("place_guess") or "")


@pytest.mark.asyncio
async def test_bbox_taxon_filter_excludes_other_taxa(client):
    """Filtering by `taxon='ticks'` excludes mosquito + rodent rows."""
    # Wide AZ box.
    out = await client.observations_bbox(
        min_lon=-115, min_lat=31, max_lon=-109, max_lat=37,
        taxon="ticks",
        days=3650,
        quality_grade="research",
        limit=200,
    )
    # Every row's taxon must be in the Ixodida subtree (i.e. its own
    # id is the tick order, or its ancestor_ids include it).
    from inaturalist_mcp.canned_data import TAXON_REFERENCE, TAXON_TICKS
    ancestors = {t["id"]: set(t.get("ancestor_ids", [])) | {t["id"]} for t in TAXON_REFERENCE}
    for row in out["results"]:
        anc = ancestors.get(row["taxon_id"], {row["taxon_id"]})
        assert row["taxon_id"] == TAXON_TICKS or TAXON_TICKS in anc


@pytest.mark.asyncio
async def test_bbox_species_specific_taxon_id_filter(client):
    """Filtering by an exact species taxon_id returns only that species."""
    out = await client.observations_bbox(
        min_lon=-115, min_lat=31, max_lon=-109, max_lat=37,
        taxon=str(TAXON_RHIPICEPHALUS_SANGUINEUS),
        days=3650,
        quality_grade="research",
        limit=200,
    )
    assert out["results"]
    for row in out["results"]:
        assert row["taxon_id"] == TAXON_RHIPICEPHALUS_SANGUINEUS
        assert row["scientific_name"] == "Rhipicephalus sanguineus"


@pytest.mark.asyncio
async def test_radius_near_returns_sorted_by_distance(client):
    """`observations_near` adds `distance_km` and returns nearest-first."""
    out = await client.observations_near(
        lat=TUCSON_LAT, lon=TUCSON_LON,
        radius_km=20.0,
        taxon="ticks",
        days=3650,
        limit=50,
    )
    assert out["source"] == "canned"
    assert out["center"] == {"lat": TUCSON_LAT, "lon": TUCSON_LON, "radius_km": 20.0}
    distances = [r["distance_km"] for r in out["results"]]
    assert distances == sorted(distances), "expected nearest-first ordering"
    for d in distances:
        assert d <= 20.0


@pytest.mark.asyncio
async def test_radius_excludes_far_phoenix_when_centered_on_tucson(client):
    """A 20-km radius around Tucson must NOT include the Phoenix tick row."""
    out = await client.observations_near(
        lat=TUCSON_LAT, lon=TUCSON_LON,
        radius_km=20.0,
        taxon="ticks",
        days=3650,
        limit=50,
    )
    for row in out["results"]:
        assert "Phoenix" not in (row.get("place_guess") or "")


def test_radius_to_bbox_round_trip():
    """A point at the center of a (lat, lon, r) bbox lies inside it."""
    lat, lon, r = 33.4484, -112.0740, 25.0
    min_lon, min_lat, max_lon, max_lat = radius_to_bbox(lat, lon, r)
    assert min_lon < lon < max_lon
    assert min_lat < lat < max_lat


def test_haversine_known_distance():
    """Tucson <-> Phoenix is ~177 km as the crow flies."""
    d = haversine_km(32.2226, -110.9747, 33.4484, -112.0740)
    assert 150 < d < 210, f"unexpected Tucson-Phoenix distance: {d}"


@pytest.mark.asyncio
async def test_days_filter_excludes_old_observations(client):
    """A short lookback drops the oldest canned rows."""
    out_long = await client.observations_bbox(
        min_lon=-115, min_lat=31, max_lon=-109, max_lat=37,
        taxon="ticks",
        days=3650,
        quality_grade="research",
        limit=200,
    )
    out_short = await client.observations_bbox(
        min_lon=-115, min_lat=31, max_lon=-109, max_lat=37,
        taxon="ticks",
        days=30,
        quality_grade="research",
        limit=200,
    )
    assert len(out_long["results"]) >= len(out_short["results"])


def test_canned_dataset_has_expected_size():
    """The canned dataset is ~20 rows -- a regression in the constant
    list size catches accidental truncation in PRs."""
    assert 18 <= len(CANNED_OBSERVATIONS) <= 30
