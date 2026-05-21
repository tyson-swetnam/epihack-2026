"""Chained-dispatch tests for the 211 Arizona mock backend.

Verifies that:

* Calling ``az211_transport_to_cooling_center`` creates a dispatch
  with a stable ``dispatch_id`` and the ``source: "mock"`` tag.
* The dispatch is retrievable in the same session via the
  ``az211_get_dispatch`` lookup tool (chained call).
* ``az211_lines`` returns a structured phone directory containing
  the canonical 2-1-1 main-line entry.

No network. Drives the real client; verifies the mock backend is
selected when AZ211_BACKEND_URL is not set.
"""

from __future__ import annotations

import re

import pytest

from az211_mcp.client import SOURCE_MOCK, Az211Client


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Az211Client:
    # Make sure no leftover env points us at a real backend.
    monkeypatch.delenv("AZ211_BACKEND_URL", raising=False)
    monkeypatch.delenv("AZ211_API_KEY", raising=False)
    return Az211Client()


def test_client_uses_mock_backend_by_default(client: Az211Client) -> None:
    assert client.is_mock is True


def test_transport_returns_mock_dispatch_with_stable_id(client: Az211Client) -> None:
    record = client.create_transport(
        postal_code="85003",
        urgency="high",
        needs_wheelchair=False,
        has_pet=False,
    )
    # Required shape per the plan.
    assert record["source"] == SOURCE_MOCK
    assert record["urgency"] == "high"
    assert record["callback_phone"] == "1-877-211-8661"
    # ETA targets per urgency bucket.
    assert record["eta_minutes"] == 18
    # secrets.token_hex(6) -> 12 hex chars.
    assert re.fullmatch(r"[0-9a-f]{12}", record["dispatch_id"])
    # Maricopa-county ZIP routes to the metro provider.
    assert "Maricopa" in record["county"] or record["county"] == "Maricopa"
    assert "211 Arizona heat-relief" in record["provider"]


def test_dispatch_chain_lookup_returns_same_record(client: Az211Client) -> None:
    created = client.create_transport(
        postal_code="85003",
        urgency="emergency",
        needs_wheelchair=True,
        has_pet=True,
    )
    fetched = client.get_dispatch(created["dispatch_id"])
    assert fetched is not None
    assert fetched["dispatch_id"] == created["dispatch_id"]
    assert fetched["needs_wheelchair"] is True
    assert fetched["has_pet"] is True
    assert fetched["source"] == SOURCE_MOCK
    # Emergency-urgency ETA per the dispatch policy.
    assert fetched["eta_minutes"] == 8


def test_lines_directory_contains_main_211_and_988(client: Az211Client) -> None:
    directory = client.operator_directory()
    assert directory["source"] == SOURCE_MOCK
    assert directory["main_line"]["dial"] == "2-1-1"
    assert directory["main_line"]["alt"] == "1-877-211-8661"
    # Expanded heat-season operator hours are documented (May -> Sept).
    assert "May" in directory["main_line"]["heat_season_hours"]
    assert directory["crisis_lifeline_988"]["dial"] == "988"
    # Solari is the operating partner.
    assert "Solari" in directory["solari_crisis_response"]["hours"] or \
        directory["solari_crisis_response"]["dial"].startswith("1-844")
    assert "Veterans" in str(directory["veterans_crisis_line"]) or \
        "veterans" in str(directory).lower()
    assert "ASL" in str(directory["asl_video_relay"])


def test_dispatch_ids_are_unique_per_call(client: Az211Client) -> None:
    ids = {
        client.create_transport(postal_code="85003", urgency="standard")[
            "dispatch_id"
        ]
        for _ in range(10)
    }
    # 10 token_hex(6) draws should never collide.
    assert len(ids) == 10
