"""FastMCP server for the Arizona Department of Health Services (ADHS).

Wraps the ADHS public-data corpus -- weekly arbovirus surveillance
summaries, the annual heat-mortality report series, and zoonotic case
counts (hantavirus, plague, rabies, RMSF, tularemia) -- as a set of
MCP tools and resources the rest of the EpiHack stack can call.

ADHS does not publish a clean REST API today. Data lives in PDFs and
ArcGIS Experience dashboards, so the default backend is the
:class:`adhs_mcp.client.ADHSClient` running in **canned mode** against
the constants in :mod:`adhs_mcp.canned_data`. Set
``ADHS_BACKEND_URL`` in the environment to point the client at a real
HTTP backend once one ships.

The numbers in :mod:`adhs_mcp.canned_data` are sourced from:

- ``heat/04-vulnerable-populations.md`` -- ADHS heat-mortality
  headline figures (>4,320 deaths 2013-2024; 990 in 2023; 602 in 2024;
  ~4,298 ER visits / year).
- ``schema/heat.sql`` -- same totals encoded as knowledge-graph
  properties; URL for the Heat Preparedness Network ArcGIS map
  (``tool.adhs_heat_map``) and the heat-mortality report portal
  (``tool.adhs_heat_mortality_dash``).
- ``schema/deep/standards.sql`` -- ICD-10-CM, SNOMED CT, and CDC
  NNDSS codes for every reportable condition this server surfaces.
- ``wildlife/resources.md`` -- the Maricopa MCESD 800+ trap network
  footprint that feeds the weekly arbovirus summary.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from . import canned_data as CD
from .client import ADHSClient


# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "adhs",
    instructions=(
        "Programmatic interface to Arizona Department of Health Services "
        "public surveillance data: weekly arbovirus summaries, the annual "
        "heat-mortality report series, zoonotic case counts (hantavirus, "
        "plague, rabies, RMSF, tularemia), and structured pointers to the "
        "ADHS Vector-Borne & Zoonotic Diseases program + Heat "
        "Preparedness Network ArcGIS map. ADHS does not publish a clean "
        "REST API today, so this server defaults to canned data sourced "
        "from the ADHS report series and the EpiHack knowledge graph. "
        "Set ADHS_BACKEND_URL to point at a real backend when one ships. "
        "Use `adhs_recent_cases` for weekly case counts; "
        "`adhs_heat_mortality_summary` for annual mortality; "
        "`adhs_arbovirus_surveillance_summary` for mosquito pool / "
        "sentinel-chicken / human + equine activity; "
        "`adhs_vector_borne_zoonotic_program` and "
        "`adhs_heat_preparedness_network` for program metadata; "
        "`adhs_reportable_conditions` for the ICD-10 / SNOMED / NNDSS "
        "code list. Resources `adhs://pathogen-acronyms` and "
        "`adhs://heat-mortality-summary-text` carry static reference text."
    ),
)


_client: ADHSClient | None = None


def _get_client() -> ADHSClient:
    global _client
    if _client is None:
        _client = ADHSClient()
    return _client


# ---------------------------------------------------------------------------
# Pydantic row models
#
# Tools return lists of `.model_dump()` dicts (per the spec) rather than
# raw model instances; that keeps the MCP wire payload to plain JSON
# while still letting tests round-trip the response through a model to
# catch shape regressions.
# ---------------------------------------------------------------------------
class RecentCaseRow(BaseModel):
    """One weekly case-count row for a single county + pathogen."""

    week_of: str = Field(
        description="ISO date for the Monday of the surveillance week."
    )
    county: str = Field(description="Arizona county.")
    confirmed: int = Field(ge=0, description="Confirmed cases reported for the week.")
    probable: int = Field(ge=0, description="Probable cases reported for the week.")
    source_report_url: str = Field(
        description="Link back to the originating ADHS report or program page."
    )


class HeatMortalityRow(BaseModel):
    """One year of statewide + per-county heat-mortality totals."""

    year: int = Field(ge=2000, le=2100)
    statewide_deaths: int = Field(ge=0)
    maricopa_deaths: int = Field(ge=0)
    pima_deaths: int = Field(ge=0)
    yuma_deaths: int = Field(ge=0)
    other_counties_deaths: int = Field(ge=0)
    estimated_er_visits: int = Field(ge=0)
    source_report_url: str


class ArbovirusSurveillanceRow(BaseModel):
    """Weekly arbovirus surveillance row.

    Sentinel-chicken seroconversion is ``None`` for jurisdictions that
    don't run a sentinel flock for the pathogen in question (most
    counties; Maricopa + Pima are the most active flocks historically).
    """

    week_of: str
    surv_year: int = Field(ge=2000, le=2100)
    county: str
    pathogen: str
    positive_pools: int = Field(ge=0)
    pools_tested: int = Field(ge=0)
    sentinel_chicken_seroconversions: int | None = Field(
        default=None, ge=0,
        description="None for jurisdictions without a sentinel flock.",
    )
    human_cases: int = Field(ge=0)
    equine_cases: int = Field(ge=0)
    trap_network_size: int | None = Field(
        default=None, ge=0,
        description="Approximate vector-trap count for the county that week.",
    )
    note: str
    source_report_url: str


class ReportableConditionRow(BaseModel):
    """One reportable condition with its standards-coded mappings.

    Every row carries at least one of ``icd10`` / ``snomed_ct`` per the
    spec; the ``test_reportable_conditions`` test enforces that.
    """

    condition: str
    category: str
    icd10: str | None = None
    icd10_description: str | None = None
    snomed_ct: str | None = None
    snomed_description: str | None = None
    nndss_condition: str | None = None
    az_reporting_rule: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
PathogenLiteral = Literal[
    "WNV", "SLEV", "DENV", "ZIKV",
    "HANTAVIRUS", "PLAGUE", "RABIES",
    "RMSF", "TULAREMIA",
]


def _dump_rows(model: type[BaseModel], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate every row through ``model`` and return ``.model_dump()`` dicts.

    Doing the round-trip on the way out catches drift between
    ``canned_data`` and the documented row shapes without requiring a
    pydantic instance to cross the MCP wire.
    """
    return [model.model_validate(r).model_dump() for r in rows]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
@mcp.tool()
async def adhs_recent_cases(
    pathogen: Annotated[
        PathogenLiteral,
        Field(description=(
            "Pathogen acronym (ADHS terminology). One of: "
            "WNV, SLEV, DENV, ZIKV, HANTAVIRUS, PLAGUE, RABIES, RMSF, "
            "TULAREMIA. See the `adhs://pathogen-acronyms` resource."
        )),
    ],
    county: Annotated[
        str | None,
        Field(description="Optional Arizona county filter (case-insensitive)."),
    ] = None,
    surv_year: Annotated[
        int | None,
        Field(description="Optional surveillance year filter, e.g. 2024."),
    ] = None,
) -> list[dict[str, Any]]:
    """Return weekly case counts for a single pathogen.

    Each row carries ``week_of`` (ISO date for Monday of the
    surveillance week), ``county``, ``confirmed`` count, ``probable``
    count, and a ``source_report_url`` pointing back at the originating
    ADHS program page. Defaults to the canned 2024 dataset; set
    ``ADHS_BACKEND_URL`` for a real backend.
    """
    rows = _get_client().recent_cases(
        pathogen=pathogen, county=county, surv_year=surv_year,
    )
    return _dump_rows(RecentCaseRow, rows)


@mcp.tool()
async def adhs_heat_mortality_summary(
    year: Annotated[
        int | None,
        Field(description=(
            "Optional year filter. Without it the tool returns every "
            "year 2013-2024."
        )),
    ] = None,
) -> list[dict[str, Any]]:
    """Annual ADHS heat-mortality counts (statewide + per-county).

    Returns 2013-2024 rows by default, sourced from the ADHS heat-
    mortality report series and ``heat/04-vulnerable-populations.md``
    (>4,320 cumulative deaths 2013-2024; 990 in 2023; 602 in 2024; ~
    4,298 ER visits / year). Maricopa County carries the overwhelming
    majority of the statewide burden.
    """
    rows = _get_client().heat_mortality_summary(year=year)
    return _dump_rows(HeatMortalityRow, rows)


@mcp.tool()
async def adhs_arbovirus_surveillance_summary(
    surv_year: Annotated[
        int | None,
        Field(description="Optional surveillance year filter."),
    ] = None,
    county: Annotated[
        str | None,
        Field(description="Optional Arizona county filter (case-insensitive)."),
    ] = None,
) -> list[dict[str, Any]]:
    """Weekly arbovirus surveillance summary.

    Rows include mosquito-pool positivity (``positive_pools`` /
    ``pools_tested``), sentinel-chicken seroconversions (where a flock
    is active; ``None`` otherwise), human and equine case counts, and
    the approximate vector-trap network size for context. The Maricopa
    rows use the 800+ trap MCESD footprint from
    ``wildlife/resources.md``; Pima rows use ~120 traps for the
    May-November season.
    """
    rows = _get_client().arbovirus_surveillance(
        surv_year=surv_year, county=county,
    )
    return _dump_rows(ArbovirusSurveillanceRow, rows)


@mcp.tool()
async def adhs_vector_borne_zoonotic_program() -> dict[str, Any]:
    """Structured description of the ADHS Vector-Borne & Zoonotic Diseases program.

    Returns the program name + URL
    (https://www.azdhs.gov/preparedness/epidemiology-disease-control/
    vector-borne-zoonotic-diseases/), the list of pathogens it
    monitors, the primary labs it works with (ASPHL, CDC Fort Collins,
    CDC Bacterial Special Pathogens, MCESD), and the reporting cadence
    per pathogen family.
    """
    return _get_client().vbzd_program()


@mcp.tool()
async def adhs_heat_preparedness_network() -> dict[str, Any]:
    """Structured pointer to the ADHS Heat Preparedness Network ArcGIS map.

    Returns the ArcGIS Experience URL
    (https://experience.arcgis.com/experience/c5bdf9ab90894e1baa5860c450dedb3b),
    the May 1 - September 30 season window (aligned with the Governor's
    Extreme Heat Preparedness Plan and the MAG HRN), and a pointer to
    `mag-hrn-mcp` for detailed cooling-center records (hours, services,
    pet-friendly, real-time capacity).
    """
    return _get_client().heat_preparedness_network()


@mcp.tool()
async def adhs_reportable_conditions() -> list[dict[str, Any]]:
    """Reportable conditions relevant to wildlife / vector / heat surveillance.

    Each row carries an ICD-10-CM code and / or a SNOMED CT concept
    (every row has at least one), the matching CDC NNDSS condition
    where one exists, and the Arizona-specific reporting cadence.
    Codes are sourced from ``schema/deep/standards.sql``.
    """
    rows = _get_client().reportable_conditions()
    return _dump_rows(ReportableConditionRow, rows)


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------
@mcp.resource("adhs://pathogen-acronyms")
def pathogen_acronyms_resource() -> str:
    """Pathogen acronyms pinned to ADHS terminology.

    Mirrors `vectorsurv://disease-acronyms` but covers the zoonotic +
    tick-borne reportable conditions VectorSurv itself doesn't carry
    (hantavirus, plague, rabies, RMSF, tularemia).
    """
    return CD.render_pathogen_acronyms_text()


@mcp.resource("adhs://heat-mortality-summary-text")
def heat_mortality_summary_text_resource() -> str:
    """Human-readable heat-mortality summary text.

    The headline numbers + vulnerable-population list from
    ``heat/04-vulnerable-populations.md``, with links back to the ADHS
    heat-mortality report portal. Intended as static LLM context so an
    agent can answer "what does ADHS say about Arizona heat deaths?"
    without first calling a tool.
    """
    return CD.HEAT_MORTALITY_SUMMARY_TEXT
