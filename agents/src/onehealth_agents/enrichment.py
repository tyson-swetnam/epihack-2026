"""EnrichmentAgent -- pulls live MCP data based on vertical + triage class.

Idempotent per ``plan/03``: repeated runs hydrate the same edges and
don't duplicate. The stub keys the dedupe by ``(mcp_server, tool)``
on the observation's current bundle.
"""

from __future__ import annotations

from .contracts import (
    EnrichmentBundle,
    EnrichmentRecord,
    Observation,
    TriageClass,
    Vertical,
)
from .mcp_client import MCPClient


class EnrichmentAgent:
    name = "enrichment"

    def __init__(self, mcp: MCPClient) -> None:
        self.mcp = mcp

    async def run(self, observation: Observation) -> EnrichmentBundle:
        bundle = observation.enrichments
        existing = {(r.mcp_server, r.tool) for r in bundle.records}
        triage = observation.triage
        if triage is None:
            return bundle

        async def hydrate(server: str, tool: str, **kwargs: object) -> None:
            if (server, tool) in existing:
                return
            try:
                payload = await self.mcp.call_tool(server, tool, **kwargs)
            except (LookupError, RuntimeError, ConnectionError) as exc:
                bundle.failed_tools.append(f"{server}.{tool}:{type(exc).__name__}")
                return
            bundle.records.append(
                EnrichmentRecord(
                    mcp_server=server,
                    tool=tool,
                    edge_predicate="enrichedWith",
                    payload=payload,
                )
            )
            existing.add((server, tool))

        # --- VBD branch ---------------------------------------------------
        if observation.vertical in {Vertical.VBD, Vertical.BOTH}:
            if triage.triage_class == TriageClass.MAIL_TO_WALKER_LAB:
                await hydrate(
                    "great-az-tick-check-mcp",
                    "create_submission",
                    user=observation.dataset.general.unique_id,
                    tick_meta={
                        "attached_duration_hours": (
                            observation.dataset.exposure.attached_duration_hours
                        ),
                        "bite_location": observation.dataset.exposure.bite_location,
                    },
                )
            # Always check nearby pool positivity for the candidate vectors.
            arthropod = "tick" if observation.dataset.exposure.tick_insect_bite else "mosquito"
            await hydrate(
                "vectorsurv-mcp",
                "get_pools",
                arthropod=arthropod,
                county=observation.geo.county_id if observation.geo else None,
                last_days=90,
            )
            # Active-outbreak check.
            for cand in triage.candidate_pathogens[:1]:
                await hydrate(
                    "knowledge-graph-mcp",
                    "outbreak_check",
                    pathogen=cand.pathogen_id,
                    county=observation.geo.county_id if observation.geo else None,
                )

        # --- Heat branch --------------------------------------------------
        if observation.vertical in {Vertical.HEAT, Vertical.BOTH}:
            if observation.dataset.general.lat and observation.dataset.general.lon:
                await hydrate(
                    "nws-heatrisk-mcp",
                    "heatrisk",
                    lat=observation.dataset.general.lat,
                    lon=observation.dataset.general.lon,
                    date=observation.received_at[:10],
                )
            if triage.triage_class in {
                TriageClass.GO_TO_COOLING_CENTER,
                TriageClass.DISPATCH_CHW,
            }:
                await hydrate(
                    "mag-hrn-mcp",
                    "search_centers",
                    lat=observation.dataset.general.lat,
                    lon=observation.dataset.general.lon,
                    radius_km=2.0,
                    open_now=True,
                    pets_ok=False,
                )
                if "dispatch-CHW-transport" in (triage.secondary_actions or []) or (
                    triage.triage_class == TriageClass.DISPATCH_CHW
                ):
                    await hydrate(
                        "211-az-mcp",
                        "transport_to_cooling_center",
                        zip=observation.dataset.general.postal_code,
                        urgency="high",
                    )

        return bundle


__all__ = ["EnrichmentAgent"]
