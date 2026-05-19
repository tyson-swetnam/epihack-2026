"""FastMCP server exposing the USGS WHISPers wildlife event-reporting
system as a set of MCP tools.

Base URL convention (verified against
``USGS-WiM/whispers/src/environments/environment.prod.ts``):
``https://whispers.usgs.gov/api/`` -- override via ``WHISPERS_BASE_URL``.

All read endpoints documented here are unauthenticated (the upstream
``EventViewSet.get_queryset`` filters anonymous calls to
``public=True`` rows automatically).

If the live USGS host is unreachable, the client transparently serves
a small canned AZ-centric dataset in
``src/whispers_mcp/canned.py``. Set ``WHISPERS_DISABLE_FALLBACK=1`` to
surface upstream errors instead.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .client import WhispersClient
from .vocab import DIAGNOSIS_VOCABULARY, EVENT_TYPES

mcp = FastMCP(
    "whispers",
    instructions=(
        "Programmatic access to the USGS National Wildlife Health "
        "Center's WHISPers (Wildlife Health Information Sharing "
        "Partnership) event-reporting system "
        "(https://whispers.usgs.gov/). Use these tools to find "
        "wildlife mortality / morbidity events near a community "
        "report, by species (e.g. Cynomys gunnisoni for plague risk), "
        "or by confirmed diagnosis (e.g. 'Yersinia pestis', "
        "'Avian influenza, HPAI', 'Hantavirus'). Every event row "
        "carries a public_url permalink to whispers.usgs.gov for "
        "verification."
    ),
)


_client: WhispersClient | None = None


def _get_client() -> WhispersClient:
    global _client
    if _client is None:
        _client = WhispersClient()
    return _client


def _row_to_dict(row: Any) -> dict[str, Any]:
    return row.model_dump()


# ---------------------------------------------------------------- tools
@mcp.tool()
async def whispers_events_recent(
    days: Annotated[
        int,
        Field(
            ge=0,
            le=3650,
            description="Look back this many days from today. Default 90.",
        ),
    ] = 90,
    state: Annotated[
        str | None,
        Field(description="USPS state code to filter by, e.g. 'AZ'."),
    ] = None,
    county_fips: Annotated[
        str | None,
        Field(description="County FIPS / GNIS ID; passed through to the WHISPers gnis_id filter."),
    ] = None,
    species: Annotated[
        str | None,
        Field(description="Species name (scientific or common) substring match."),
    ] = None,
    limit: Annotated[int, Field(ge=1, le=1000)] = 100,
) -> dict:
    """Recent public WHISPers events.

    One row per event with ``event_id``, ``start_date``, ``end_date``,
    ``state``, ``county``, ``location``, ``species``,
    ``affected_count``, ``diagnosis``, ``event_type``, ``public_url``.
    """
    rows = await _get_client().fetch_events(
        days=days,
        state=state,
        county_fips=county_fips,
        species=species,
        limit=limit,
    )
    return {"count": len(rows), "events": [_row_to_dict(r) for r in rows]}


@mcp.tool()
async def whispers_event_detail(
    event_id: Annotated[int, Field(ge=1, description="WHISPers event id.")],
) -> dict:
    """Full nested record for one WHISPers event.

    Includes ``event_locations`` (with admin-level-one / -two,
    coordinates, and ``locationspecies``), ``event_diagnoses``,
    ``species_diagnoses`` (joining diagnosis basis + cause + lab to
    species), and a ``raw`` passthrough for clients that need every
    upstream field.
    """
    detail = await _get_client().fetch_event_detail(event_id)
    return detail.model_dump()


@mcp.tool()
async def whispers_events_bbox(
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    days: Annotated[int, Field(ge=0, le=3650)] = 90,
    limit: Annotated[int, Field(ge=1, le=1000)] = 200,
) -> dict:
    """Events whose first event-location falls inside the bounding box.

    Used by the EnrichmentAgent to find wildlife mortality co-located
    with a community report (`agents/src/onehealth_agents/enrichment.py`).
    Bbox is applied client-side because EventSummary does not expose a
    native geographic filter.
    """
    rows = await _get_client().fetch_events_bbox(
        min_lon=min_lon,
        min_lat=min_lat,
        max_lon=max_lon,
        max_lat=max_lat,
        days=days,
        limit=limit,
    )
    return {
        "bbox": [min_lon, min_lat, max_lon, max_lat],
        "count": len(rows),
        "events": [_row_to_dict(r) for r in rows],
    }


@mcp.tool()
async def whispers_events_by_species(
    species: Annotated[
        str,
        Field(description="Species name, scientific or common (substring match)."),
    ],
    days: Annotated[int, Field(ge=0, le=3650)] = 365,
    state: Annotated[str | None, Field(description="USPS state code, e.g. 'AZ'.")] = None,
    limit: Annotated[int, Field(ge=1, le=1000)] = 200,
) -> dict:
    """Events involving a particular species.

    Example: ``species='Cynomys gunnisoni'`` returns Gunnison's prairie
    dog mortality events (relevant to plague risk in Arizona).
    """
    rows = await _get_client().fetch_events(
        days=days,
        state=state,
        species=species,
        limit=limit,
    )
    return {"species": species, "count": len(rows), "events": [_row_to_dict(r) for r in rows]}


@mcp.tool()
async def whispers_events_by_diagnosis(
    diagnosis: Annotated[
        str,
        Field(description='Diagnosis name, e.g. "Yersinia pestis", "Avian influenza, HPAI", "Hantavirus".'),
    ],
    days: Annotated[int, Field(ge=0, le=3650)] = 365,
    state: Annotated[str | None, Field(description="USPS state code, e.g. 'AZ'.")] = None,
    limit: Annotated[int, Field(ge=1, le=1000)] = 200,
) -> dict:
    """Events with a particular confirmed diagnosis.

    Diagnosis names follow the WHISPers controlled vocabulary -- see
    the ``whispers://diagnosis-vocabulary`` resource.
    """
    rows = await _get_client().fetch_events(
        days=days,
        state=state,
        diagnosis=diagnosis,
        limit=limit,
    )
    return {"diagnosis": diagnosis, "count": len(rows), "events": [_row_to_dict(r) for r in rows]}


@mcp.tool()
async def whispers_az_recent_summary(
    days: Annotated[int, Field(ge=1, le=3650)] = 180,
) -> dict:
    """Structured digest of AZ events for the last ``days``.

    Returns counts by species, county, and diagnosis -- the kind of
    benchmark the Cluster Detection Agent compares new community
    reports against (see ``plan/04-data-flows.md`` Scenario D).
    """
    rows = await _get_client().fetch_events(
        days=days, state="AZ", limit=1000
    )
    by_species: Counter[str] = Counter()
    by_county: Counter[str] = Counter()
    by_diagnosis: Counter[str] = Counter()
    by_event_type: Counter[str] = Counter()
    for r in rows:
        for s in r.species:
            by_species[s] += 1
        if r.county:
            by_county[r.county] += 1
        for d in r.diagnosis:
            by_diagnosis[d] += 1
        if r.event_type:
            by_event_type[r.event_type] += 1
    return {
        "state": "AZ",
        "days": days,
        "event_count": len(rows),
        "by_species": dict(by_species.most_common()),
        "by_county": dict(by_county.most_common()),
        "by_diagnosis": dict(by_diagnosis.most_common()),
        "by_event_type": dict(by_event_type.most_common()),
        "events": [_row_to_dict(r) for r in rows],
    }


# ----------------------------------------------------------- resources
@mcp.resource("whispers://event-types")
def event_types_resource() -> str:
    """The WHISPers event-type enumeration (Mortality/Morbidity vs Surveillance)."""
    return json.dumps(EVENT_TYPES, indent=2)


@mcp.resource("whispers://diagnosis-vocabulary")
def diagnosis_vocabulary_resource() -> str:
    """A representative slice of the WHISPers diagnosis controlled vocabulary.

    The authoritative list lives at ``/api/diagnoses/?no_page=true`` on
    the live service; refresh ``src/whispers_mcp/vocab.py`` from
    there if the canonical list drifts.
    """
    return json.dumps(DIAGNOSIS_VOCABULARY, indent=2)


__all__ = ["mcp"]
