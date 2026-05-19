"""Verify the canned dataset round-trips through the pydantic models.

No network, no live calls -- purely exercises the mock-fallback path
of WhispersClient.
"""

from __future__ import annotations

import asyncio

import pytest

from whispers_mcp.canned import CANNED_EVENTS
from whispers_mcp.client import WhispersClient
from whispers_mcp.models import CannedEvent, EventDetail, EventRow


def test_every_canned_event_validates_as_pydantic_model():
    for c in CANNED_EVENTS:
        assert isinstance(c, CannedEvent)
        row = c.to_row()
        assert isinstance(row, EventRow)
        assert row.event_id == c.event_id
        assert row.public is True
        assert row.public_url and str(row.event_id) in row.public_url
        detail = c.to_detail()
        assert isinstance(detail, EventDetail)
        assert detail.event_id == c.event_id


def test_canned_dataset_size_documented():
    """If you change the size of the canned dataset, update the README
    and bump this so it stays visible in CI diffs."""
    assert len(CANNED_EVENTS) == 10


def test_event_ids_are_unique():
    ids = [c.event_id for c in CANNED_EVENTS]
    assert len(ids) == len(set(ids))


def test_canned_events_have_az_coverage():
    az = [c for c in CANNED_EVENTS if c.state == "AZ"]
    # We need enough AZ rows for the AZ summary / bbox tests to be useful.
    assert len(az) >= 6


def test_mock_event_detail_round_trips():
    client = WhispersClient(use_mock=True)
    try:
        detail = asyncio.run(client.fetch_event_detail(9000005))
    finally:
        asyncio.run(client.aclose())
    assert detail.event_id == 9000005
    diagnoses = [d.get("diagnosis") for d in detail.event_diagnoses]
    assert "Yersinia pestis" in diagnoses


def test_mock_event_detail_missing_id_raises():
    client = WhispersClient(use_mock=True)
    try:
        with pytest.raises(LookupError):
            asyncio.run(client.fetch_event_detail(123456789))
    finally:
        asyncio.run(client.aclose())
