"""Species and diagnosis filters against the canned dataset.

These exercise the same code path the live API takes after rows are
projected; the mock-only mode lets the test run hermetically.
"""

from __future__ import annotations

import asyncio

from whispers_mcp.client import WhispersClient


def _run(coro):
    return asyncio.run(coro)


def test_species_filter_finds_prairie_dog_plague_history():
    """Cynomys gunnisoni should surface both Coconino plague rows and
    the NM cross-border one, regardless of date window."""
    client = WhispersClient(use_mock=True)
    try:
        rows = _run(
            client.fetch_events(
                days=0, species="Cynomys gunnisoni", limit=100
            )
        )
    finally:
        _run(client.aclose())
    ids = {r.event_id for r in rows}
    assert {9000005, 9000006, 9000009}.issubset(ids)


def test_species_filter_is_case_insensitive_substring():
    client = WhispersClient(use_mock=True)
    try:
        rows = _run(
            client.fetch_events(
                days=0, species="peromyscus", limit=100
            )
        )
    finally:
        _run(client.aclose())
    diagnoses = {d for r in rows for d in r.diagnosis}
    assert any("Hantavirus" in d for d in diagnoses)


def test_diagnosis_filter_hpai():
    client = WhispersClient(use_mock=True)
    try:
        rows = _run(
            client.fetch_events(
                days=0, diagnosis="Avian influenza, HPAI", limit=100
            )
        )
    finally:
        _run(client.aclose())
    assert rows, "HPAI canned rows should be present"
    states = {r.state for r in rows}
    assert "AZ" in states


def test_diagnosis_filter_yersinia_pestis_az_only():
    """State + diagnosis combo: confine to AZ plague events."""
    client = WhispersClient(use_mock=True)
    try:
        rows = _run(
            client.fetch_events(
                days=0,
                state="AZ",
                diagnosis="Yersinia pestis",
                limit=100,
            )
        )
    finally:
        _run(client.aclose())
    ids = {r.event_id for r in rows}
    assert ids == {9000005, 9000006}, ids
    # NM plague row excluded by state filter
    assert 9000009 not in ids


def test_combined_species_and_diagnosis_filters_intersect():
    client = WhispersClient(use_mock=True)
    try:
        rows = _run(
            client.fetch_events(
                days=0,
                species="Cynomys gunnisoni",
                diagnosis="Yersinia pestis",
                limit=100,
            )
        )
    finally:
        _run(client.aclose())
    ids = {r.event_id for r in rows}
    # All three Cynomys plague rows match (two AZ + one NM)
    assert ids == {9000005, 9000006, 9000009}


def test_az_recent_summary_aggregates_counts():
    """End-to-end against the summary path the dashboard would call."""
    client = WhispersClient(use_mock=True)
    try:
        rows = _run(client.fetch_events(days=0, state="AZ", limit=500))
    finally:
        _run(client.aclose())
    counties = {r.county for r in rows}
    assert {"Coconino", "Maricopa", "Pima"}.issubset(counties)
