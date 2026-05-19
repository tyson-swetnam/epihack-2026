"""FastMCP server for the MAG Heat Relief Network.

Exposes the Maricopa Association of Governments Heat Relief Network
-- ~200+ cooling, hydration, respite, and donation sites operating
across the Phoenix metro from May 1 -- September 30 each year -- as
a set of tools an LLM can call.

Real-mode data comes from the MAG-hosted ArcGIS service at
``https://geo.azmag.gov/arcgis/rest/services/maps/Heat_Relief_Network``;
that URL is set via ``MAG_HRN_FEATURE_SERVICE_URL`` because the precise
path drifts between seasons. Without that env var the server runs in
**mock mode** against a small canned dataset, which is plenty for the
multi-MCP join in Scenario C of ``plan/04-data-flows.md``.

The ``mag_supply_status`` tool is **mock-only** -- MAG does not yet
publish a real-time occupancy/supply feed. Heat-Q2 in
``plan/01-parameter-mapping.html`` is the gap this tool is shaped to
close once that feed exists.
"""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .client import (
    MAGHRNClient,
    SERVICE_TYPE_DESCRIPTIONS,
    SERVICE_TYPES,
)


mcp = FastMCP(
    "mag-hrn",
    instructions=(
        "Programmatic access to the MAG Heat Relief Network (cooling, "
        "hydration, respite, and donation-drop-off sites across the "
        "Phoenix metro, May 1 - September 30). Start with "
        "`mag_search_centers(lat, lon, radius_km)` to find nearby "
        "options (filter by open-now, pets_ok, and service type); use "
        "`mag_center_detail(center_id)` for full hours / supply notes; "
        "use `mag_list_open_now` for a fast snapshot of currently-open "
        "centers; use `mag_supply_status` for an occupancy/supply "
        "heads-up (currently MOCK - MAG does not yet publish a real "
        "feed); and `mag_search_by_text` for free-text lookup. "
        "Real-mode data needs MAG_HRN_FEATURE_SERVICE_URL in env."
    ),
)


_client: MAGHRNClient | None = None


def _get_client() -> MAGHRNClient:
    global _client
    if _client is None:
        _client = MAGHRNClient()
    return _client


# ---------------------------------------------------------------- search
@mcp.tool()
async def mag_search_centers(
    lat: Annotated[float, Field(description="Latitude, decimal degrees.")],
    lon: Annotated[float, Field(description="Longitude, decimal degrees.")],
    radius_km: Annotated[
        float,
        Field(gt=0, le=50, description="Search radius in kilometers (max 50)."),
    ] = 5.0,
    open_now: Annotated[
        bool,
        Field(
            description=(
                "If true (default), drop centers whose hours-of-operation "
                "say they are not currently open."
            )
        ),
    ] = True,
    pets_ok: Annotated[
        bool | None,
        Field(
            description=(
                "If set, only return centers whose pet-friendliness flag "
                "matches. Leave null to include all."
            )
        ),
    ] = None,
    services: Annotated[
        list[str] | None,
        Field(
            description=(
                'Optional service-type filter. Allowed values: "cooling", '
                '"hydration", "respite", "donation". A center matches if any '
                "of its services intersects the requested set."
            )
        ),
    ] = None,
    limit: Annotated[
        int,
        Field(ge=1, le=500, description="Maximum number of rows to return."),
    ] = 50,
    now_iso: Annotated[
        str | None,
        Field(
            description=(
                "Optional ISO timestamp to use as 'now' for the open-now "
                "filter (useful for previewing). Defaults to current time."
            )
        ),
    ] = None,
) -> dict:
    """Geo + filter search for cooling / hydration / respite / donation sites.

    Returns ``{mode, as_of, query, total, centers}`` where each center
    carries ``{id, name, address, city, postal_code, lat, lon,
    services, hours_today, pets_ok, distance_km, kg_node_id}``.
    Distance is in kilometers, sorted nearest first. Outside the
    HRN's May 1 -- September 30 operating window the centers list is
    empty and ``off_season: true`` is returned.
    """
    return await _get_client().search_centers(
        lat=lat,
        lon=lon,
        radius_km=radius_km,
        open_now=open_now,
        pets_ok=pets_ok,
        services=services,
        limit=limit,
        now_iso=now_iso,
    )


@mcp.tool()
async def mag_center_detail(
    center_id: Annotated[
        str, Field(description="Center ID returned by mag_search_centers.")
    ],
) -> dict:
    """Full record for a single center, incl. hours-by-day and notes.

    The ``kg_node_id`` field is reserved for the downstream knowledge-graph
    integration; it is null until a center has been edged into the graph.
    """
    return await _get_client().center_detail(center_id)


@mcp.tool()
async def mag_list_open_now(
    now_iso: Annotated[
        str | None,
        Field(
            description=(
                "Optional ISO timestamp to use as 'now'. Useful for "
                "previewing 'what will be open at 3 p.m. today?'."
            )
        ),
    ] = None,
) -> dict:
    """Snapshot of every HRN center that's currently open.

    Off-season this list is empty regardless of the time of day.
    """
    return await _get_client().list_open_now(now_iso=now_iso)


@mcp.tool()
async def mag_supply_status(
    center_id: Annotated[
        str,
        Field(description="Center ID returned by mag_search_centers."),
    ],
) -> dict:
    """Supply / occupancy heads-up for a center. **MOCK feed today.**

    Returns ``{center_id, water_status, seats_available, last_updated_iso,
    source}`` where ``water_status`` is one of ``ok | low | out``,
    ``seats_available`` is an integer or null (null for respite-style
    overflow capacity), and ``source`` is ``"mock"`` until MAG ships a
    real feed. This is the Heat-Q2 gap in
    ``plan/01-parameter-mapping.html``.
    """
    return await _get_client().supply_status(center_id)


@mcp.tool()
async def mag_search_by_text(
    query: Annotated[
        str,
        Field(
            description=(
                'Free-text query, e.g. "library", "church", or "donation". '
                "Tokens are AND-matched against name, address, city, ZIP, "
                "operator, notes, and service types."
            )
        ),
    ],
    near: Annotated[
        tuple[float, float] | None,
        Field(
            description=(
                "Optional [lat, lon] hint. If set, results are sorted by "
                "distance instead of alphabetically."
            )
        ),
    ] = None,
    limit: Annotated[
        int,
        Field(ge=1, le=500, description="Maximum number of rows to return."),
    ] = 50,
    now_iso: Annotated[
        str | None,
        Field(description="Optional ISO timestamp for the as-of clock."),
    ] = None,
) -> dict:
    """Free-text search across the HRN registry.

    Empty queries return every in-season center.
    """
    near_t: tuple[float, float] | None = None
    if near is not None:
        # Pydantic gives us a tuple when typed as one, but JSON-RPC may
        # ship a list; coerce defensively.
        try:
            lat, lon = float(near[0]), float(near[1])
            near_t = (lat, lon)
        except (TypeError, IndexError, ValueError):
            near_t = None
    return await _get_client().search_by_text(
        query=query, near=near_t, limit=limit, now_iso=now_iso
    )


# ---------------------------------------------------- reference resources
@mcp.resource("mag://service-types")
def service_types_resource() -> str:
    """Reference for the four HRN service categories.

    Values are taken from the MAG storefront at https://hrn.azmag.gov/
    and standardized to a tight 4-value vocabulary the rest of the
    EpiHack stack can filter by.
    """
    lines = ["HRN service-type vocabulary (use in mag_search_centers `services` filter):", ""]
    for s in SERVICE_TYPES:
        lines.append(f"- {s}: {SERVICE_TYPE_DESCRIPTIONS[s]}")
    lines += [
        "",
        "Real MAG ArcGIS rows arrive with various labels (LocationType,",
        "Type, CenterType, etc.); the client normalizes them onto these",
        "four values. See client.py:_normalize_services for the mapping.",
    ]
    return "\n".join(lines)


@mcp.resource("mag://operating-window")
def operating_window_resource() -> str:
    """The HRN's May 1 - September 30 operating season.

    Off-season requests return an empty `centers` list with
    `off_season: true`. The season window is overridable in
    `client.py` (`SEASON_START_MONTH_DAY` / `SEASON_END_MONTH_DAY`)
    for testing, but the public storefront and the MAG annual launch
    cycle are the authoritative reference: see
    https://azmag.gov/Programs/Heat-Relief-Network .
    """
    return (
        "MAG Heat Relief Network operating season:\n"
        "  start: May 1 (inclusive)\n"
        "  end:   September 30 (inclusive)\n"
        "\n"
        "Outside this window every tool returns an empty centers list\n"
        "and `off_season: true`. Phoenix does not observe DST, so all\n"
        "open-now math is done in MST (UTC-7).\n"
        "\n"
        "Reference: https://azmag.gov/Programs/Heat-Relief-Network\n"
        "Public map: https://hrn.azmag.gov/\n"
    )
