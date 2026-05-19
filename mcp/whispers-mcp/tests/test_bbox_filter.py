"""Spatial bounding-box filter behaviour against the canned dataset.

The dataset deliberately includes events in NM and CA so a strict AZ
bbox should exclude them.
"""

from __future__ import annotations

import asyncio

from whispers_mcp.canned import AZ_BBOX, CANNED_EVENTS
from whispers_mcp.client import WhispersClient


def _run(coro):
    return asyncio.run(coro)


def _all_az_canned_ids() -> set[int]:
    return {c.event_id for c in CANNED_EVENTS if c.state == "AZ"}


def test_az_bbox_returns_only_az_rows():
    client = WhispersClient(use_mock=True)
    try:
        rows = _run(
            client.fetch_events_bbox(
                min_lon=AZ_BBOX[0],
                min_lat=AZ_BBOX[1],
                max_lon=AZ_BBOX[2],
                max_lat=AZ_BBOX[3],
                days=0,  # date cutoff disabled
                limit=500,
            )
        )
    finally:
        _run(client.aclose())

    assert rows, "bbox should return at least one row"
    states = {r.state for r in rows}
    assert states == {"AZ"}, f"non-AZ rows leaked: {states}"

    returned_ids = {r.event_id for r in rows}
    assert returned_ids == _all_az_canned_ids()


def test_tight_bbox_around_flagstaff_only_returns_coconino():
    """A small bbox around Flagstaff (35.2,-111.65) should keep only
    Coconino-County rows from the canned dataset."""
    client = WhispersClient(use_mock=True)
    try:
        rows = _run(
            client.fetch_events_bbox(
                min_lon=-112.0,
                min_lat=34.9,
                max_lon=-111.3,
                max_lat=36.1,
                days=0,
                limit=500,
            )
        )
    finally:
        _run(client.aclose())

    counties = {r.county for r in rows}
    assert counties == {"Coconino"}, counties


def test_bbox_excludes_new_mexico_event():
    """The NM (San Juan County) event must NOT leak into an AZ-only bbox."""
    client = WhispersClient(use_mock=True)
    try:
        rows = _run(
            client.fetch_events_bbox(
                min_lon=AZ_BBOX[0],
                min_lat=AZ_BBOX[1],
                max_lon=AZ_BBOX[2],
                max_lat=AZ_BBOX[3],
                days=0,
                limit=500,
            )
        )
    finally:
        _run(client.aclose())

    nm_id = next(c.event_id for c in CANNED_EVENTS if c.state == "NM")
    assert nm_id not in {r.event_id for r in rows}
