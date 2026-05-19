"""Tests for the mock-only ``mag_supply_status`` tool.

The contract is the headline thing the rest of the EpiHack stack will
depend on: when MAG (or any operator) ships a real feed, the only thing
that changes is ``source: "mock"`` -> ``source: "feed"`` and the
populated values. The keys must remain stable. These tests freeze the
documented shape.

Heat-Q2 of plan/01-parameter-mapping.html is the gap this tool is
shaped to close.
"""

from __future__ import annotations

import asyncio

import pytest

from mag_hrn_mcp.client import MAGHRNClient


@pytest.fixture
def client() -> MAGHRNClient:
    return MAGHRNClient(feature_service_url=None)


# ----------------------------------------------------------------- shape
def test_supply_status_shape_for_known_center(client):
    out = asyncio.run(client.supply_status("mag.hrn.mock.0001"))
    assert out["found"] is True
    # Required keys per the README contract.
    required = {
        "center_id",
        "found",
        "water_status",
        "seats_available",
        "last_updated_iso",
        "source",
    }
    assert required <= out.keys()
    # Mock identification is non-negotiable: callers must be able to
    # distinguish the placeholder from a real feed.
    assert out["source"] == "mock"
    assert out["water_status"] in ("ok", "low", "out")
    seats = out["seats_available"]
    assert seats is None or isinstance(seats, int)
    # ISO timestamp parses.
    from datetime import datetime

    datetime.fromisoformat(out["last_updated_iso"])


def test_supply_status_returns_mock_flag_for_unknown_id(client):
    out = asyncio.run(client.supply_status("mag.hrn.mock.does-not-exist"))
    assert out["found"] is False
    assert out["source"] == "mock"
    assert out["water_status"] is None
    assert out["seats_available"] is None


def test_supply_status_is_deterministic(client):
    """Same center, same session -> same values, so a demo doesn't
    flicker between calls."""
    a = asyncio.run(client.supply_status("mag.hrn.mock.0002"))
    b = asyncio.run(client.supply_status("mag.hrn.mock.0002"))
    assert a["water_status"] == b["water_status"]
    assert a["seats_available"] == b["seats_available"]


def test_supply_status_water_status_alphabet(client):
    """Across every mock center, water_status stays in the documented
    three-value alphabet."""
    from mag_hrn_mcp.client import MOCK_CENTERS

    for c in MOCK_CENTERS:
        out = asyncio.run(client.supply_status(c["id"]))
        assert out["water_status"] in ("ok", "low", "out"), (
            f"unexpected water_status {out['water_status']} for {c['id']}"
        )


def test_supply_status_respite_seats_null(client):
    """Respite-style sites surface seats_available=null because their
    capacity is overflow / not seat-counted in the mock."""
    # 0002 (Andre House) and 0008 (St. Vincent de Paul) are respite.
    for sid in ("mag.hrn.mock.0002", "mag.hrn.mock.0008"):
        out = asyncio.run(client.supply_status(sid))
        assert out["seats_available"] is None, (
            f"{sid} carries respite service but reports seats_available"
        )


def test_supply_status_note_mentions_mock_and_heat_q2(client):
    """A consumer reading the JSON should see, in the response, both
    that this is mock data AND a pointer to plan/01 Heat-Q2."""
    out = asyncio.run(client.supply_status("mag.hrn.mock.0001"))
    note = (out.get("note") or "").lower()
    assert "mock" in note
    assert "heat-q2" in note or "plan/01" in note
