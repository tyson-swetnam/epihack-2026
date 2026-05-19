"""Tests for ``inat_taxon_lookup`` against the canned reference list.

All offline -- ``INAT_OFFLINE=1`` forces the client to skip HTTP and
resolve names via the alias table in
``inaturalist_mcp.canned_data.TAXON_REFERENCE``.
"""

from __future__ import annotations

import os

import pytest

# Ensure offline mode + UA satisfied before importing the client.
os.environ.setdefault("INAT_OFFLINE", "1")
os.environ.setdefault("INAT_USER_AGENT", "inaturalist-mcp-tests/0.1 (ci@example.org)")

from inaturalist_mcp.canned_data import (  # noqa: E402
    TAXON_PEROMYSCUS_MANICULATUS,
    TAXON_RHIPICEPHALUS_SANGUINEUS,
    TAXON_TICKS,
)
from inaturalist_mcp.client import INaturalistClient  # noqa: E402


@pytest.fixture
def client() -> INaturalistClient:
    return INaturalistClient(offline=True)


@pytest.mark.asyncio
async def test_lookup_common_name_resolves_to_deer_mouse(client):
    out = await client.taxon_lookup("deer mouse")
    assert out["source"] == "canned"
    ids = {r["id"] for r in out["results"]}
    assert TAXON_PEROMYSCUS_MANICULATUS in ids


@pytest.mark.asyncio
async def test_lookup_scientific_name_resolves_to_brown_dog_tick(client):
    out = await client.taxon_lookup("Rhipicephalus sanguineus")
    assert out["source"] == "canned"
    ids = {r["id"] for r in out["results"]}
    assert TAXON_RHIPICEPHALUS_SANGUINEUS in ids


@pytest.mark.asyncio
async def test_lookup_numeric_id_returns_single_record(client):
    out = await client.taxon_lookup(TAXON_TICKS)
    assert out["source"] == "canned"
    assert len(out["results"]) == 1
    assert out["results"][0]["id"] == TAXON_TICKS
    assert out["results"][0]["name"] == "Ixodida"


@pytest.mark.asyncio
async def test_lookup_string_numeric_id_also_works(client):
    out = await client.taxon_lookup(str(TAXON_TICKS))
    assert out["source"] == "canned"
    assert out["results"][0]["id"] == TAXON_TICKS


@pytest.mark.asyncio
async def test_lookup_unknown_name_returns_empty(client):
    out = await client.taxon_lookup("definitely-not-a-real-creature-xyzzy")
    assert out["source"] == "canned"
    assert out["results"] == []


@pytest.mark.asyncio
async def test_lookup_keyword_alias_resolves(client):
    # 'tick' is in the alias table for Ixodida
    out = await client.taxon_lookup("tick")
    assert out["source"] == "canned"
    ids = {r["id"] for r in out["results"]}
    assert TAXON_TICKS in ids
