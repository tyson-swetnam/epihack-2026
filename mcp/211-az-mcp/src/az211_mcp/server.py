"""FastMCP server exposing 211 Arizona heat-relief, transport, utility-
assistance, and crisis-referral services as MCP tools.

Mock-by-default. 211 Arizona (operated by Solari Crisis & Human
Services) does not publish a public REST API; this server ships a
canned mock backend (see :mod:`az211_mcp.mock_data`) that is
sufficient to drive Scenario C in ``plan/04-data-flows.md`` end-to-
end without network. Set ``AZ211_BACKEND_URL`` to point at a real
backend when one becomes available.

Designed for EpiHack Arizona 2026's heat focus group. An LLM client
can answer questions like:

    "I'm at ZIP 85003, my client needs a ride to the nearest cooling
    center and they use a wheelchair — what can 211 dispatch and how
    long is the ETA?"

by calling:

  1. az211_transport_to_cooling_center(postal_code, urgency, needs_wheelchair=True)
  2. az211_cooling_center_referral_nearby(lat, lon, urgency)   (optional join)
  3. az211_lines()                                              (callback numbers)
"""

from __future__ import annotations

import json
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .client import Az211Client
from .mock_data import LANGUAGES_SUPPORTED, OPERATOR_HOURS


mcp = FastMCP(
    "az211",
    instructions=(
        "211 Arizona (Solari Crisis & Human Services) heat-relief, "
        "transport-to-cooling-center, utility-assistance, and crisis "
        "referrals. Mock-by-default; set AZ211_BACKEND_URL to swap to a "
        "real backend. Live 211 operators speak English and Spanish "
        "year-round, with expanded summer hours during heat season. "
        "Indigenous-language access is routed through partner "
        "organisations (ITCA-TEC, NEC, IHS). Start with az211_lines() "
        "for the phone directory, az211_crisis_referrals(...) for "
        "topic-based phone numbers, or az211_transport_to_cooling_center("
        "...) for a heat-emergency dispatch."
    ),
)


_client: Az211Client | None = None


def _get_client() -> Az211Client:
    global _client
    if _client is None:
        _client = Az211Client()
    return _client


# ---------------------------------------------------------------- transport
@mcp.tool()
def az211_transport_to_cooling_center(
    postal_code: Annotated[
        str, Field(description="5-digit U.S. ZIP / postal code of the caller's location.")
    ],
    urgency: Annotated[
        Literal["standard", "high", "emergency"],
        Field(
            description=(
                "Dispatch urgency. 'emergency' targets ~8 min ETA, "
                "'high' ~18 min, 'standard' ~45 min."
            )
        ),
    ] = "standard",
    needs_wheelchair: Annotated[
        bool, Field(description="True if caller needs a wheelchair-accessible vehicle.")
    ] = False,
    has_pet: Annotated[
        bool, Field(description="True if caller is bringing a pet.")
    ] = False,
) -> dict:
    """Request transport to the nearest cooling center via 211 Arizona.

    Returns a dispatch confirmation with a stable ``dispatch_id`` that
    can be re-queried later in the same session (the mock backend
    holds dispatches in memory). The ``source`` field is ``"mock"``
    when running against the in-memory backend.
    """
    record = _get_client().create_transport(
        postal_code=postal_code,
        urgency=urgency,
        needs_wheelchair=needs_wheelchair,
        has_pet=has_pet,
    )
    return record


@mcp.tool()
def az211_get_dispatch(
    dispatch_id: Annotated[
        str, Field(description="Dispatch ID returned by az211_transport_to_cooling_center.")
    ],
) -> dict:
    """Look up a previously-created transport dispatch.

    Returns ``{"found": false, "dispatch_id": ...}`` if the ID isn't
    known (typically because the server restarted or the call is in a
    different session).
    """
    record = _get_client().get_dispatch(dispatch_id)
    if record is None:
        return {"found": False, "dispatch_id": dispatch_id}
    return {"found": True, **record}


# ------------------------------------------------------ utility assistance
@mcp.tool()
def az211_utility_assistance_nearby(
    postal_code: Annotated[
        str, Field(description="5-digit U.S. ZIP / postal code of the caller's location.")
    ],
    kind: Annotated[
        Literal[
            "any",
            "electric",
            "gas",
            "water",
            "weatherization",
            "emergency_ac_repair",
        ],
        Field(description="Type of utility assistance to filter on."),
    ] = "any",
) -> dict:
    """Community-action agencies + LIHEAP providers near the caller.

    The canned list covers Maricopa, Pima, Coconino, Yuma, and
    Navajo / Apache county providers. Same-county providers are
    returned first; the list never empties so the agent always has
    a fallback to suggest.
    """
    providers = _get_client().list_utility_assistance(postal_code, kind)
    return {
        "postal_code": postal_code,
        "kind": kind,
        "count": len(providers),
        "providers": providers,
    }


# ------------------------------------------------------ crisis referrals
@mcp.tool()
def az211_crisis_referrals(
    postal_code: Annotated[
        str, Field(description="5-digit U.S. ZIP / postal code of the caller's location.")
    ],
    topic: Annotated[
        Literal["heat", "housing", "food", "behavioral_health", "all"],
        Field(description="Referral topic; 'all' returns every topic in one call."),
    ] = "all",
) -> dict:
    """Referral list (phone / hours / languages) for a given topic."""
    rows = _get_client().list_crisis_referrals(postal_code, topic)
    return {
        "postal_code": postal_code,
        "topic": topic,
        "count": len(rows),
        "referrals": rows,
    }


# ------------------------------------------ cooling-center convenience wrap
@mcp.tool()
def az211_cooling_center_referral_nearby(
    lat: Annotated[float, Field(description="Latitude, decimal degrees.")],
    lon: Annotated[float, Field(description="Longitude, decimal degrees.")],
    urgency: Annotated[
        Literal["standard", "high", "emergency"],
        Field(description="Dispatch urgency; tightens the search radius for high/emergency."),
    ] = "standard",
) -> dict:
    """Cooling centers near a point (canned).

    Convenience wrapper. In a production deployment this should
    cross-call ``mag-hrn-mcp.search_centers`` for the authoritative
    metro-Phoenix dataset (and a future ``pima-cooling-mcp`` for
    Pima County); the local mock list is only meant to keep the
    Heat scenarios runnable offline.
    """
    centers = _get_client().nearby_cooling_centers(lat, lon, urgency)
    return {
        "lat": lat,
        "lon": lon,
        "urgency": urgency,
        "count": len(centers),
        "centers": centers,
        "note": (
            "Mock data; production should cross-call mag-hrn-mcp for "
            "the authoritative Maricopa County registry."
        ),
    }


# ------------------------------------------------------ phone-line directory
@mcp.tool()
def az211_lines() -> dict:
    """Structured directory of 211 Arizona phone lines and partner numbers.

    Includes the main 2-1-1 / 1-877-211-8661 line (operator hours and
    seasonal expansion), the 988 Suicide & Crisis Lifeline, the
    Solari Crisis Response Network statewide line, the Veterans
    Crisis Line, and the ASL video-relay pathway.
    """
    return _get_client().operator_directory()


# ----------------------------------------------------------- MCP resources
@mcp.resource("az211://hours")
def hours_resource() -> str:
    """Full operator hours by season (English / Spanish)."""
    return json.dumps(OPERATOR_HOURS, indent=2, ensure_ascii=False)


@mcp.resource("az211://languages")
def languages_resource() -> str:
    """Full languages-supported list, including indigenous-language pathways."""
    return json.dumps(LANGUAGES_SUPPORTED, indent=2, ensure_ascii=False)
