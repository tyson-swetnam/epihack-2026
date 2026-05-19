"""GeoEnrichmentAgent -- coords -> county/tribe/region edges.

Production version calls ``knowledge-graph-mcp.regions_at_point``.

Stub version: also calls that tool through the supplied
:class:`MCPClient`. When the supplied client is the
:class:`FakeMCPClient` shipped in this package it returns canned
matches for the Scenario A (Patagonia) and Scenario C (Phoenix)
worked examples. A hand-rolled AZ fallback table covers a few more
corners so the agent can answer offline if the MCP is missing.
"""

from __future__ import annotations

from typing import Optional

from .contracts import GeoEnrichment, Observation
from .mcp_client import MCPClient


# Hardcoded fallback table -- ZCTA -> (county, region) for a few AZ
# anchors. Kept tiny on purpose; the real lookup lives in the kg.
_AZ_FALLBACK: dict[str, tuple[str, Optional[str], Optional[str]]] = {
    # zcta: (county_id, tribe_id, region_id)
    "85003": ("county.maricopa", None, "region.maricopa_metro"),
    "85007": ("county.maricopa", None, "region.maricopa_metro"),
    "85004": ("county.maricopa", None, "region.maricopa_metro"),
    "85624": ("county.santa_cruz", None, "region.border_corridor"),
    "85621": ("county.santa_cruz", None, "region.border_corridor"),
    "86001": ("county.coconino", None, "region.colorado_plateau"),
    "86503": ("county.apache", "tribe.navajo", "region.colorado_plateau"),
}


class GeoEnrichmentAgent:
    name = "geo_enrichment"

    def __init__(self, mcp: MCPClient | None = None) -> None:
        self.mcp = mcp

    async def run(self, observation: Observation) -> GeoEnrichment:
        general = observation.dataset.general
        precision: str = general.coord_precision or (
            "exact" if general.lat is not None and general.lon is not None else "unknown"
        )

        # Prefer the MCP if we have one.
        if self.mcp is not None and general.lat is not None and general.lon is not None:
            try:
                resp = await self.mcp.call_tool(
                    "knowledge-graph-mcp",
                    "regions_at_point",
                    lat=general.lat,
                    lon=general.lon,
                )
                geo = GeoEnrichment(
                    county_id=resp.get("county_id"),
                    tribe_id=resp.get("tribe_id"),
                    region_id=resp.get("region_id"),
                    zcta=resp.get("zcta") or general.postal_code,
                    coord_precision=precision,  # type: ignore[arg-type]
                )
                # Optional second hop: responsible vector-control agency.
                if geo.county_id and observation.vertical.value in {"vbd", "both"}:
                    try:
                        intersect = await self.mcp.call_tool(
                            "vectorsurv-mcp", "agency_region_intersect"
                        )
                        for hit in intersect.get("intersections", []):
                            if hit.get("region") == geo.county_id:
                                geo.responsible_vector_control_agency = hit.get(
                                    "agency"
                                )
                                break
                    except (LookupError, RuntimeError):
                        pass
                return geo
            except LookupError:
                pass  # fall through to local table

        # Fallback: lookup by ZIP.
        zcta = general.postal_code
        if zcta and zcta in _AZ_FALLBACK:
            county, tribe, region = _AZ_FALLBACK[zcta]
            return GeoEnrichment(
                county_id=county,
                tribe_id=tribe,
                region_id=region,
                zcta=zcta,
                coord_precision="zip",
            )

        return GeoEnrichment(
            county_id=None,
            tribe_id=None,
            region_id="region.statewide",
            zcta=zcta,
            coord_precision="unknown",
        )


__all__ = ["GeoEnrichmentAgent"]
