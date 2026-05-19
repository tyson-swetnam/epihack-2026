"""FastMCP server exposing the VectorSurv API as MCP tools.

Paths and parameter conventions verified against the OpenAPI spec at
https://api.vectorsurv.org/openapi (v1.0.44 at time of writing).

Designed for EpiHack Arizona 2026's wildlife and vector-borne diseases
focus group. An LLM client (Claude Desktop, Claude Code, ...) can
answer questions like:

    "Show me the WNV pool-positivity rate for Maricopa County mosquito
    collections during biweek 18 of 2025."

by calling the appropriate tools in sequence:

  1. vectorsurv_list_test_targets  -> find the WNV pathogen ID
  2. vectorsurv_agency_region_intersect / vectorsurv_list_agencies
     -> find the agency ID(s) for Maricopa County Vector Control
  3. vectorsurv_get_pools           -> pull pools in the window
  4. vectorsurv_calculate_infection_rate -> compute the MIR / bc-MLE
"""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .calculations import abundance as calc_abundance
from .calculations import infection_rate as calc_infection_rate
from .calculations import vector_index as calc_vector_index
from .client import VectorSurvClient


mcp = FastMCP(
    "vectorsurv",
    instructions=(
        "Programmatic access to the VectorSurv vector-borne disease "
        "surveillance API (mosquitoes, ticks, arboviruses, human/equine "
        "case counts). Start with `vectorsurv_list_agencies` and "
        "`vectorsurv_list_test_targets` to discover the IDs you need to "
        "filter by, then call collection / pool / calculation tools. "
        "Paths and parameter syntax follow the OpenAPI spec at "
        "https://api.vectorsurv.org/openapi."
    ),
)


_client: VectorSurvClient | None = None


def _get_client() -> VectorSurvClient:
    global _client
    if _client is None:
        _client = VectorSurvClient()
    return _client


# ---------------------------------------------------------------- meta
@mcp.tool()
async def vectorsurv_version() -> dict:
    """Return the VectorSurv API version string."""
    return {"version": await _get_client().get_version()}


# ---------------------------------------------------------------- discovery
@mcp.tool()
async def vectorsurv_list_agencies(
    populate: Annotated[
        list[str] | None,
        Field(description='Eager-load related fields; allowed: "region", "state", "aggregate".'),
    ] = None,
    page: int = 1,
    page_size: Annotated[int, Field(ge=1, le=500)] = 100,
) -> dict:
    """Agencies the authenticated user has access to."""
    return await _get_client().list_agencies(
        page=page, page_size=page_size, populate=populate
    )


@mcp.tool()
async def vectorsurv_agency_region_intersect() -> dict:
    """Agencies whose service area intersects each region.

    The fastest way to find every VectorSurv agency reporting from a
    given U.S. state or county (e.g. Arizona, Maricopa County).
    """
    return {"intersections": await _get_client().agency_region_intersect()}


@mcp.tool()
async def vectorsurv_list_regions(
    search: str | None = None,
    page: int = 1,
    page_size: Annotated[int, Field(ge=1, le=500)] = 100,
) -> dict:
    """Geographic regions (states, counties, custom polygons)."""
    return await _get_client().list_regions(
        page=page, page_size=page_size, search=search
    )


@mcp.tool()
async def vectorsurv_list_test_targets(
    page: int = 1,
    page_size: Annotated[int, Field(ge=1, le=500)] = 200,
) -> dict:
    """List of pathogens / test targets VectorSurv tracks.

    Each row carries ``acronym`` (e.g. ``WNV``), ``vector``
    (``mosquito``/``tick``/``both``), and an ICD-10 code where
    applicable.
    """
    return await _get_client().list_test_targets(page=page, page_size=page_size)


@mcp.tool()
async def vectorsurv_list_sites(
    agency_ids: list[int] | None = None,
    populate: list[str] | None = None,
    page: int = 1,
    page_size: Annotated[int, Field(ge=1, le=500)] = 100,
) -> dict:
    """List trap-location bookmarks (sites)."""
    return await _get_client().list_sites(
        agency_ids=agency_ids,
        populate=populate,
        page=page,
        page_size=page_size,
    )


# ----------------------------------------------------------------- raw data
@mcp.tool()
async def vectorsurv_get_collections(
    start_date: Annotated[str, Field(description="ISO date, e.g. '2025-05-01'.")],
    end_date: Annotated[str, Field(description="ISO date, e.g. '2025-09-30'.")],
    arthropod: Annotated[
        str,
        Field(description='"mosquito" / "nontick" hit /v1/arthropod/collection; "tick" hits /v1/tick/collection.'),
    ] = "mosquito",
    agency_ids: list[int] | None = None,
    page: int = 1,
    page_size: Annotated[int, Field(ge=1, le=5000)] = 1000,
    populate: list[str] | None = None,
) -> dict:
    """Arthropod or tick collection records."""
    return await _get_client().get_collections(
        start_date=start_date,
        end_date=end_date,
        arthropod=arthropod,
        agency_ids=agency_ids,
        page=page,
        page_size=page_size,
        populate=populate,
    )


@mcp.tool()
async def vectorsurv_get_pools(
    start_date: str,
    end_date: str,
    arthropod: Annotated[
        str, Field(description='"mosquito", "tick", or "nontick".')
    ] = "mosquito",
    agency_ids: list[int] | None = None,
    page: int = 1,
    page_size: Annotated[int, Field(ge=1, le=5000)] = 1000,
    populate: list[str] | None = None,
) -> dict:
    """Pooled-test results for arboviruses tested against mosquito or tick pools."""
    return await _get_client().get_pools(
        start_date=start_date,
        end_date=end_date,
        arthropod=arthropod,
        agency_ids=agency_ids,
        page=page,
        page_size=page_size,
        populate=populate,
    )


@mcp.tool()
async def vectorsurv_pools_are_positive(
    pool_ids: list[int],
    pathogen_ids: Annotated[
        list[int],
        Field(description="Test-target IDs (from vectorsurv_list_test_targets)."),
    ],
    presumptive: bool = False,
) -> dict:
    """Bulk-check pools for definitive-positive pathogen results."""
    return {
        "results": await _get_client().pools_are_positive(
            pool_ids=pool_ids,
            pathogen_ids=pathogen_ids,
            presumptive=presumptive,
        )
    }


@mcp.tool()
async def vectorsurv_get_case_counts(
    agency_ids: list[int] | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: Annotated[int, Field(ge=1, le=500)] = 100,
) -> dict:
    """Human / equine arbovirus case-count records by week, month, county."""
    return await _get_client().get_case_counts(
        agency_ids=agency_ids,
        search=search,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------- analytics
def _rows(envelope):
    """VectorSurv responses are usually {rows, total, page, ...}; passthrough lists."""
    if isinstance(envelope, list):
        return envelope
    if isinstance(envelope, dict):
        return envelope.get("rows") or envelope.get("data") or []
    return []


@mcp.tool()
async def vectorsurv_calculate_abundance(
    start_date: str,
    end_date: str,
    interval: Annotated[
        str, Field(description='"collection_date", "Week", "Biweek", or "Month".')
    ] = "Biweek",
    arthropod: str = "mosquito",
    species: str | None = None,
    trap: str | None = None,
    agency_ids: list[int] | None = None,
) -> dict:
    """Abundance per interval = total arthropods / total trap-nights."""
    coll = await _get_client().get_collections(
        start_date=start_date,
        end_date=end_date,
        arthropod=arthropod,
        agency_ids=agency_ids,
        page_size=5000,
        populate=["arthropods", "trap", "site"],
    )
    return {
        "abundance": calc_abundance(
            _rows(coll), interval=interval, species=species, trap=trap
        )
    }


@mcp.tool()
async def vectorsurv_calculate_infection_rate(
    start_date: str,
    end_date: str,
    target_disease: Annotated[str, Field(description='Disease acronym, e.g. "WNV".')],
    interval: str = "Biweek",
    method: Annotated[str, Field(description='"mir" or "bc-mle".')] = "mir",
    scale: float = 1000.0,
    arthropod: str = "mosquito",
    species: str | None = None,
    trap: str | None = None,
    agency_ids: list[int] | None = None,
) -> dict:
    """Estimated arbovirus infection rate per `scale` mosquitoes per interval."""
    pools = await _get_client().get_pools(
        start_date=start_date,
        end_date=end_date,
        arthropod=arthropod,
        agency_ids=agency_ids,
        page_size=5000,
        populate=["test", "species", "trap"],
    )
    return {
        "infection_rate": calc_infection_rate(
            _rows(pools),
            target_disease=target_disease,
            interval=interval,
            method=method,
            scale=scale,
            species=species,
            trap=trap,
        )
    }


@mcp.tool()
async def vectorsurv_calculate_vector_index(
    start_date: str,
    end_date: str,
    target_disease: str,
    interval: str = "Biweek",
    method: str = "mir",
    scale: float = 1000.0,
    arthropod: str = "mosquito",
    species: str | None = None,
    trap: str | None = None,
    agency_ids: list[int] | None = None,
) -> dict:
    """Vector Index = abundance × infection rate (expected infected mosquitoes per trap-night)."""
    coll = await _get_client().get_collections(
        start_date=start_date,
        end_date=end_date,
        arthropod=arthropod,
        agency_ids=agency_ids,
        page_size=5000,
        populate=["arthropods", "trap", "site"],
    )
    pools = await _get_client().get_pools(
        start_date=start_date,
        end_date=end_date,
        arthropod=arthropod,
        agency_ids=agency_ids,
        page_size=5000,
        populate=["test", "species", "trap"],
    )
    return {
        "vector_index": calc_vector_index(
            _rows(coll),
            _rows(pools),
            target_disease=target_disease,
            interval=interval,
            method=method,
            scale=scale,
            species=species,
            trap=trap,
        )
    }


# -------------------------------------------------------- reference resource
@mcp.resource("vectorsurv://disease-acronyms")
def disease_acronyms() -> str:
    """Common arbovirus / vector-borne disease acronyms recognized by VectorSurv."""
    return (
        "WNV   = West Nile virus\n"
        "SLEV  = St. Louis encephalitis virus\n"
        "WEEV  = Western equine encephalitis virus\n"
        "EEEV  = Eastern equine encephalitis virus\n"
        "DENV  = Dengue virus\n"
        "ZIKV  = Zika virus\n"
        "CHIKV = Chikungunya virus\n"
        "BORR  = Borrelia (Lyme)\n"
        "ANAP  = Anaplasma phagocytophilum\n"
        "BABE  = Babesia\n"
        "(call vectorsurv_list_test_targets for the authoritative list)"
    )


@mcp.resource("vectorsurv://query-syntax")
def query_syntax() -> str:
    """Cheat-sheet for VectorSurv API query parameters."""
    return (
        "VectorSurv uses Mongoose-style query strings:\n"
        "  query[collection_date][$gte]=2024-05-01\n"
        "  query[collection_date][$lte]=2024-09-30\n"
        "  query[agency]=55\n"
        "  query[agency][$in][0]=55&query[agency][$in][1]=72\n"
        "  query[surv_year]=2024\n"
        "Eager-load related records: populate[0]=test&populate[1]=site\n"
        "Pagination: page=1&pageSize=100   (lower pageSize if MAX_PAYLOAD_EXCEEDED).\n"
        "Sort: sort=-collection_date,id\n"
    )
