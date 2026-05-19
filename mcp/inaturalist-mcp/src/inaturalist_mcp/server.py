"""FastMCP server exposing iNaturalist citizen-science observations.

Built for EpiHack Arizona 2026's wildlife and vector-borne diseases
focus group. An LLM client (Claude Desktop, Claude Code, Claude API
agents) can answer questions like:

    "Show me research-grade brown-dog-tick observations in Pima County
    in the last year, with a monthly histogram and a county-breakdown."

by calling ``inat_taxon_lookup('brown dog tick')`` -> get the taxon
ID -> ``inat_species_summary_az(taxon_id)`` for the histogram, then
``inat_observations_near(...)`` for nearby raw observations.

The server is **mock-by-default** in the sense that ``INAT_OFFLINE=1``
or a network failure transparently falls back to the canned dataset
in ``canned_data.py``. Tools tag their response with
``source: "live" | "canned"`` so the calling LLM knows which it got.
"""

from __future__ import annotations

from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .canned_data import (
    AZ_PLACE_ID,
    AZ_TICK_GENERA,
    RATE_LIMIT_POLICY,
)
from .client import INaturalistClient


mcp = FastMCP(
    "inaturalist",
    instructions=(
        "Programmatic access to iNaturalist citizen-science observations "
        "of vectors (ticks, mosquitoes, fleas) and wildlife disease "
        "reservoirs (deer mice, prairie dogs, rock squirrels, "
        "cottontails) relevant to Arizona One Health surveillance. "
        "Start with `inat_taxon_lookup` to resolve a common name to a "
        "taxon_id, then call `inat_observations_bbox`, "
        "`inat_observations_near`, or `inat_observations_by_taxon` to "
        "pull observations. `inat_species_summary_az` is the quick "
        "month-by-month + county-by-county histogram. "
        "`inat_tick_observations_az` is the citizen-science cross-check "
        "for the `great-az-tick-check-mcp` mail-in submissions. "
        "Every observation row carries the iNaturalist observation URL "
        "so downstream tools can link back to the source."
    ),
)


_client: INaturalistClient | None = None


def _get_client() -> INaturalistClient:
    global _client
    if _client is None:
        _client = INaturalistClient()
    return _client


# ---------------------------------------------------------- observation tools
@mcp.tool()
async def inat_observations_bbox(
    min_lon: Annotated[float, Field(description="Western longitude (decimal degrees).")],
    min_lat: Annotated[float, Field(description="Southern latitude (decimal degrees).")],
    max_lon: Annotated[float, Field(description="Eastern longitude (decimal degrees).")],
    max_lat: Annotated[float, Field(description="Northern latitude (decimal degrees).")],
    taxon: Annotated[
        str,
        Field(
            description=(
                "Either a known keyword (`ticks`, `mosquitoes`, `fleas`, "
                "`rodents`) or a numeric iNat taxon_id."
            )
        ),
    ] = "ticks",
    days: Annotated[int, Field(ge=1, le=3650, description="Lookback window in days.")] = 90,
    quality_grade: Annotated[
        Literal["research", "any"],
        Field(description="iNaturalist quality grade filter."),
    ] = "research",
    limit: Annotated[int, Field(ge=1, le=200)] = 200,
) -> dict:
    """Public iNaturalist observations inside a bounding box.

    Each row: ``observation_id``, ``observed_on``, ``lat``, ``lon``,
    ``geoprivacy``, ``taxon_id``, ``taxon_name``, ``scientific_name``,
    ``user_login``, ``photo_url``, ``place_guess``,
    ``identifications_count``, ``comments_count``, ``url``.
    """
    return await _get_client().observations_bbox(
        min_lon=min_lon, min_lat=min_lat,
        max_lon=max_lon, max_lat=max_lat,
        taxon=taxon,
        days=days,
        quality_grade=quality_grade,
        limit=limit,
    )


@mcp.tool()
async def inat_observations_near(
    lat: Annotated[float, Field(ge=-90, le=90)],
    lon: Annotated[float, Field(ge=-180, le=180)],
    radius_km: Annotated[float, Field(gt=0, le=500)] = 10.0,
    taxon: str = "ticks",
    days: Annotated[int, Field(ge=1, le=3650)] = 90,
    quality_grade: Literal["research", "any"] = "research",
    limit: Annotated[int, Field(ge=1, le=200)] = 200,
) -> dict:
    """Observations within ``radius_km`` of a point.

    A convenience wrapper around :func:`inat_observations_bbox` -- the
    radius is converted to a bounding box, then the haversine filter
    is applied to the candidate rows so distance ranking is accurate
    at the corners.
    """
    return await _get_client().observations_near(
        lat=lat, lon=lon, radius_km=radius_km,
        taxon=taxon, days=days,
        quality_grade=quality_grade,
        limit=limit,
    )


@mcp.tool()
async def inat_observations_by_taxon(
    taxon_id: Annotated[int, Field(ge=1, description="Numeric iNaturalist taxon_id.")],
    place_id: Annotated[
        int,
        Field(
            ge=1,
            description=(
                "iNaturalist place_id. Defaults to 53 (Arizona, US state)."
            ),
        ),
    ] = AZ_PLACE_ID,
    days: Annotated[int, Field(ge=1, le=3650)] = 365,
    quality_grade: Literal["research", "any"] = "research",
    limit: Annotated[int, Field(ge=1, le=200)] = 200,
) -> dict:
    """Observations of a specific taxon within an iNaturalist place.

    Defaults to ``place_id=53`` (the canonical Arizona state place;
    confirm at ``https://api.inaturalist.org/v1/places/53``).
    """
    return await _get_client().observations_by_taxon(
        taxon_id=taxon_id,
        place_id=place_id,
        days=days,
        quality_grade=quality_grade,
        limit=limit,
    )


@mcp.tool()
async def inat_taxon_lookup(
    name_or_id: Annotated[
        str,
        Field(
            description=(
                "Common name (e.g. 'deer mouse'), scientific name "
                "(e.g. 'Peromyscus maniculatus'), or a numeric "
                "iNaturalist taxon_id."
            )
        ),
    ],
) -> dict:
    """Resolve a name or numeric ID to one or more taxon records.

    Useful for turning *'deer mouse'* into the canonical
    *Peromyscus maniculatus* taxon_id before calling the observation
    tools.
    """
    return await _get_client().taxon_lookup(name_or_id)


@mcp.tool()
async def inat_species_summary_az(
    taxon: Annotated[
        str,
        Field(
            description=(
                "Either a known keyword (`ticks`, `mosquitoes`, `fleas`, "
                "`rodents`) or a numeric iNat taxon_id."
            )
        ),
    ],
    days: Annotated[int, Field(ge=1, le=3650)] = 365,
) -> dict:
    """Counts of AZ observations by month and by county-equivalent place.

    Buckets ``observed_on`` to ``YYYY-MM`` for the monthly histogram
    and to the ``"X County"`` chunk of the ``place_guess`` for the
    county histogram.
    """
    return await _get_client().species_summary_az(taxon=taxon, days=days)


@mcp.tool()
async def inat_tick_observations_az(
    days: Annotated[int, Field(ge=1, le=3650)] = 365,
    limit: Annotated[int, Field(ge=1, le=500)] = 500,
) -> dict:
    """Research-grade tick observations in Arizona (Ixodida, place_id=53).

    The citizen-science cross-check for ``great-az-tick-check-mcp``
    (Walker lab) and AZGFD wildlife data: hikers + naturalists post
    photos publicly to iNaturalist; the lab gets the physical
    specimens via mail. This tool surfaces the public photo stream.
    """
    out = await _get_client().observations_by_taxon(
        taxon_id=AZ_TICK_GENERA[0]["taxon_id"],  # Ixodida
        place_id=AZ_PLACE_ID,
        days=days,
        quality_grade="research",
        limit=min(limit, 200),
    )
    return out


# -------------------------------------------------------- reference resources
@mcp.resource("inat://tick-genera-az")
def tick_genera_az() -> str:
    """AZ-relevant tick genera + species with their iNaturalist taxon IDs.

    Use this as a quick reference when an LLM needs to plug a taxon_id
    into ``inat_observations_by_taxon`` without an extra
    ``inat_taxon_lookup`` round-trip.
    """
    lines = []
    for row in AZ_TICK_GENERA:
        lines.append(
            f"{row['scientific_name']}  ({row.get('common_name', '')})\n"
            f"  taxon_id: {row['taxon_id']}  rank: {row['rank']}\n"
            f"  {row['notes']}"
        )
    return "\n\n".join(lines)


@mcp.resource("inat://rate-limits")
def rate_limits() -> str:
    """Documented iNaturalist API rate-limit policy + this server's behaviour."""
    return RATE_LIMIT_POLICY
