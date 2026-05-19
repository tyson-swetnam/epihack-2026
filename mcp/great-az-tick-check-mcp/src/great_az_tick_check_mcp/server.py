"""FastMCP server for the Great Arizona Tick Check.

Exposes the UA Cooperative Extension's participatory tick-mail-in
program (Dr. Kathleen Walker lab, Department of Entomology,
University of Arizona) as a set of MCP tools the rest of the
EpiHack stack can call.

There is no public REST API today, so the default backend is an
**in-memory mock** (see ``client.GreatAZTickCheckClient``). Set
``GATTC_BACKEND_URL`` in the environment to swap in a real HTTP
backend once one exists.

This server is the right hand of Scenario A in ``plan/04-data-flows.md``:
the Triage Agent calls ``gattc_create_submission`` to give the hiker
a mailing label, and later the Knowledge Update Agent polls
``gattc_submission_status`` for the Walker lab's species + pathogen
results.
"""

from __future__ import annotations

from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .client import (
    AZ_TICK_SPECIES,
    PATHOGENS_SCREENED,
    WALKER_LAB_MAILING_ADDRESS,
    GreatAZTickCheckClient,
)


mcp = FastMCP(
    "great-az-tick-check",
    instructions=(
        "Programmatic interface to the Great Arizona Tick Check, the UA "
        "Cooperative Extension's participatory tick-surveillance program "
        "run by Dr. Kathleen Walker's lab. Use `gattc_create_submission` "
        "to register a public mail-in submission and get a mailing label "
        "+ status URL; use `gattc_submission_status` to poll for the lab's "
        "species ID and pathogen-screen results; use "
        "`gattc_species_identification_from_photo` for a low-confidence "
        "field guess (always followed by a lab confirmation); use "
        "`gattc_pathogens_screened` for the reference list. This server "
        "runs against an in-memory mock by default -- set "
        "GATTC_BACKEND_URL to point at a real backend when one exists."
    ),
)


_client: GreatAZTickCheckClient | None = None


def _get_client() -> GreatAZTickCheckClient:
    global _client
    if _client is None:
        _client = GreatAZTickCheckClient()
    return _client


# ---------------------------------------------------------------- submissions
@mcp.tool()
async def gattc_create_submission(
    submitter_email: Annotated[str, Field(description="Contact email for lab results.")],
    submitter_name: Annotated[str, Field(description="Full name of the submitter.")],
    county: Annotated[str, Field(description="Arizona county where the tick was collected.")],
    zip_code: Annotated[str, Field(description="ZIP code where the tick was collected.")],
    tick_date: Annotated[
        str, Field(description="ISO date the tick was collected / found, e.g. '2026-05-12'.")
    ],
    host: Annotated[
        Literal["human", "pet", "environment"],
        Field(description="Where the tick was found: on a person, on an animal, or off-host."),
    ] = "human",
    attachment_duration_hours: Annotated[
        float | None,
        Field(description="If attached to a host, approximate hours attached before removal."),
    ] = None,
    body_location: Annotated[
        str | None,
        Field(description="If on a person/pet, anatomical location (e.g. 'leg', 'scalp', 'ear')."),
    ] = None,
    photo_url: Annotated[
        str | None, Field(description="Optional URL to a photo of the tick.")
    ] = None,
    consent_to_research_use: Annotated[
        bool,
        Field(
            description=(
                "If true, the submitter agrees the specimen and metadata may be used in "
                "downstream research and aggregated public reporting."
            )
        ),
    ] = False,
) -> dict:
    """Register a new tick submission with the Walker lab.

    Returns the new ``submission_id``, the lab's static mailing address,
    a placeholder mailing-label URL, a status URL, and the estimated
    turnaround in days. The caller should immediately surface the
    mailing address + label to the user (Scenario A, step 9 of
    ``plan/04-data-flows.md``).
    """
    return _get_client().create_submission(
        submitter_email=submitter_email,
        submitter_name=submitter_name,
        county=county,
        zip_code=zip_code,
        tick_date=tick_date,
        host=host,
        attachment_duration_hours=attachment_duration_hours,
        body_location=body_location,
        photo_url=photo_url,
        consent_to_research_use=consent_to_research_use,
    )


@mcp.tool()
async def gattc_submission_status(
    submission_id: Annotated[
        str, Field(description="ID returned by `gattc_create_submission`.")
    ],
) -> dict:
    """Look up the current status of a tick submission.

    Status is one of ``received``, ``identifying``, ``testing``, or
    ``complete``. Once status is ``complete``, the response also
    carries ``species`` (the lab's morphological / molecular ID) and
    ``pathogens_tested`` (per-pathogen PCR results).
    """
    return _get_client().get_status(submission_id)


@mcp.tool()
async def gattc_mailing_label(
    submission_id: Annotated[
        str, Field(description="ID returned by `gattc_create_submission`.")
    ],
    fmt: Annotated[
        Literal["pdf", "png"],
        Field(description="Preferred label format."),
    ] = "pdf",
) -> dict:
    """Get a (placeholder) mailing-label URL plus the lab's mailing address.

    Useful when an LLM client wants to re-render the label without
    re-creating the submission.
    """
    return _get_client().mailing_label(submission_id, fmt=fmt)


# ----------------------------------------------------------------- knowledge
@mcp.tool()
async def gattc_species_identification_from_photo(
    photo_url: Annotated[str, Field(description="URL to the tick photo.")],
    lat: Annotated[
        float | None, Field(description="Latitude of collection (optional).")
    ] = None,
    lon: Annotated[
        float | None, Field(description="Longitude of collection (optional).")
    ] = None,
) -> dict:
    """Mock species guess from a photo.

    Returns a single best-guess species, its confidence (always low!),
    and the full short-list of AZ-relevant ticks for the caller to
    show as alternatives. The response includes ``verify_with_lab:
    true`` and the Walker lab's mailing address; treat the guess as
    a triage aid, not a definitive identification.
    """
    return _get_client().species_guess(photo_url, lat=lat, lon=lon)


@mcp.tool()
async def gattc_pathogens_screened() -> dict:
    """List the pathogens the Walker lab screens submitted ticks for.

    Each row carries ``scientific_name``, ``disease``, ``icd10`` (with
    its short description), and ``primary_vector``. ICD-10 codes are
    sourced from ``schema/deep/standards.sql`` (Rickettsia rickettsii)
    and ``schema/deep/pathogens.sql`` (the others), matching the rest
    of the EpiHack knowledge graph.
    """
    return {
        "lab": "UA Cooperative Extension — Great Arizona Tick Check (Walker lab)",
        "mailing_address": WALKER_LAB_MAILING_ADDRESS,
        "pathogens": PATHOGENS_SCREENED,
    }


# -------------------------------------------------------- reference resources
@mcp.resource("gattc://mailing-address")
def mailing_address_resource() -> str:
    """Static mailing address for tick submissions (from wildlife/resources.md)."""
    return WALKER_LAB_MAILING_ADDRESS


@mcp.resource("gattc://az-tick-species")
def az_tick_species_resource() -> str:
    """Short list of Arizona-relevant tick species + brief notes."""
    return "\n\n".join(
        f"{s['common_name']} ({s['scientific_name']})\n  {s['notes']}"
        for s in AZ_TICK_SPECIES
    )
