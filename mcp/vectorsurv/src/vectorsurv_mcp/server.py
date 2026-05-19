"""FastMCP server exposing the VectorSurv API as MCP tools.

Each tool is a thin wrapper around either a `VectorSurvClient` call
or one of the surveillance calculations (`abundance`,
`infection_rate`, `vector_index`).

Designed for EpiHack Arizona 2026's wildlife and vector-borne
diseases focus group. The intent is that an LLM client (Claude
Desktop, Claude Code, etc.) can answer questions like:

    "What was the West Nile vector index in Maricopa County during
    biweek 18 of 2025?"

by calling the appropriate tools in sequence.
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
        "surveillance API (mosquitoes, ticks, arboviruses). "
        "Use `vectorsurv_list_agencies` first to discover which "
        "agency IDs the authenticated user has access to, then call "
        "the collections / pools / calculation tools to pull data."
    ),
)


_client: VectorSurvClient | None = None


def _get_client() -> VectorSurvClient:
    global _client
    if _client is None:
        _client = VectorSurvClient()
    return _client


# ---------------------------------------------------------------- discovery
@mcp.tool()
async def vectorsurv_list_agencies() -> dict:
    """List VectorSurv agencies the authenticated user has access to.

    Run this first to discover the `agency_ids` to filter by in
    subsequent calls.
    """
    return {"agencies": await _get_client().list_agencies()}


@mcp.tool()
async def vectorsurv_list_sites(
    agency_ids: Annotated[
        list[int] | None,
        Field(description="Restrict to these agency IDs; omit for all accessible."),
    ] = None,
    page: int = 1,
    page_size: Annotated[int, Field(ge=1, le=500)] = 100,
) -> dict:
    """List trap sites (bookmarked trap locations) the user has access to."""
    return {
        "sites": await _get_client().list_sites(
            agency_ids=agency_ids, page=page, page_size=page_size
        )
    }


# ----------------------------------------------------------------- raw data
@mcp.tool()
async def vectorsurv_get_collections(
    start_date: Annotated[str, Field(description="ISO date, e.g. '2025-05-01'.")],
    end_date: Annotated[str, Field(description="ISO date, e.g. '2025-09-30'.")],
    arthropod: Annotated[str, Field(description="'mosquito' or 'tick'.")] = "mosquito",
    agency_ids: list[int] | None = None,
    page: int = 1,
    page_size: Annotated[int, Field(ge=1, le=5000)] = 1000,
) -> dict:
    """Arthropod collection records (raw trap captures, not pooled testing)."""
    return {
        "collections": await _get_client().get_collections(
            start_date=start_date,
            end_date=end_date,
            arthropod=arthropod,
            agency_ids=agency_ids,
            page=page,
            page_size=page_size,
        )
    }


@mcp.tool()
async def vectorsurv_get_pools(
    start_date: str,
    end_date: str,
    arthropod: str = "mosquito",
    target_acronym: Annotated[
        str | None,
        Field(description="Disease acronym (e.g. 'WNV', 'SLEV')."),
    ] = None,
    agency_ids: list[int] | None = None,
    page: int = 1,
    page_size: Annotated[int, Field(ge=1, le=5000)] = 1000,
) -> dict:
    """Pooled-test results for arboviruses tested against mosquito pools."""
    return {
        "pools": await _get_client().get_pools(
            start_date=start_date,
            end_date=end_date,
            arthropod=arthropod,
            agency_ids=agency_ids,
            target_acronym=target_acronym,
            page=page,
            page_size=page_size,
        )
    }


# ---------------------------------------------------------------- analytics
@mcp.tool()
async def vectorsurv_calculate_abundance(
    start_date: str,
    end_date: str,
    interval: Annotated[
        str, Field(description="'collection_date', 'Week', 'Biweek', or 'Month'.")
    ] = "Biweek",
    species: str | None = None,
    trap: str | None = None,
    agency_ids: list[int] | None = None,
) -> dict:
    """Abundance per interval = total arthropods / total trap-nights."""
    client = _get_client()
    raw = await client.get_collections(
        start_date=start_date,
        end_date=end_date,
        agency_ids=agency_ids,
        page_size=5000,
    )
    rows = raw if isinstance(raw, list) else raw.get("data", raw.get("rows", raw))
    return {
        "abundance": calc_abundance(
            rows, interval=interval, species=species, trap=trap
        )
    }


@mcp.tool()
async def vectorsurv_calculate_infection_rate(
    start_date: str,
    end_date: str,
    target_disease: Annotated[str, Field(description="Disease acronym, e.g. 'WNV'.")],
    interval: str = "Biweek",
    method: Annotated[str, Field(description="'mir' or 'bc-mle'.")] = "mir",
    scale: float = 1000.0,
    species: str | None = None,
    trap: str | None = None,
    agency_ids: list[int] | None = None,
) -> dict:
    """Estimated arbovirus infection rate per `scale` mosquitoes per interval."""
    client = _get_client()
    raw = await client.get_pools(
        start_date=start_date,
        end_date=end_date,
        target_acronym=target_disease,
        agency_ids=agency_ids,
        page_size=5000,
    )
    rows = raw if isinstance(raw, list) else raw.get("data", raw.get("rows", raw))
    return {
        "infection_rate": calc_infection_rate(
            rows,
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
    species: str | None = None,
    trap: str | None = None,
    agency_ids: list[int] | None = None,
) -> dict:
    """Vector Index = abundance × infection-rate per interval.

    Expected number of infected mosquitoes per trap-night.
    """
    client = _get_client()
    coll_raw = await client.get_collections(
        start_date=start_date,
        end_date=end_date,
        agency_ids=agency_ids,
        page_size=5000,
    )
    pools_raw = await client.get_pools(
        start_date=start_date,
        end_date=end_date,
        target_acronym=target_disease,
        agency_ids=agency_ids,
        page_size=5000,
    )
    collections = (
        coll_raw if isinstance(coll_raw, list) else coll_raw.get("data", coll_raw.get("rows", coll_raw))
    )
    pools = (
        pools_raw if isinstance(pools_raw, list) else pools_raw.get("data", pools_raw.get("rows", pools_raw))
    )
    return {
        "vector_index": calc_vector_index(
            collections,
            pools,
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
        "WNV  = West Nile virus\n"
        "SLEV = St. Louis encephalitis virus\n"
        "WEEV = Western equine encephalitis virus\n"
        "EEEV = Eastern equine encephalitis virus\n"
        "DENV = Dengue virus\n"
        "ZIKV = Zika virus\n"
        "CHIKV = Chikungunya virus\n"
        "BORR = Borrelia (Lyme)\n"
        "ANAP = Anaplasma phagocytophilum\n"
        "BABE = Babesia\n"
    )
