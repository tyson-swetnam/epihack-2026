"""GET /v1/context.

Surfaces public-health signals from upstream MCP servers
(vectorsurv-mcp, nws-heatrisk-mcp, whispers-mcp, adhs-mcp, …) for
a coarse location.

The hard rule from plan/06: signals must name a public source and
must NOT assert a diagnosis. The output guard at the orchestrator
boundary is the load-bearing check; this module is a thin shim.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from ..models import CitedSource, CoarseLocation, ContextEnvelope, ContextSignal

router = APIRouter(prefix="/context", tags=["context"])


@router.get(
    "",
    response_model=ContextEnvelope,
    summary="Public-health signals for a coarse location",
)
async def get_context(
    zip: Optional[str] = Query(default=None, pattern=r"^[0-9]{5}$"),
    grid_id: Optional[str] = Query(
        default=None, pattern=r"^g1km:-?\d+\.\d{1,2},-?\d+\.\d{1,2}$"
    ),
    types: Optional[list[str]] = Query(default=None),
) -> ContextEnvelope:
    if not zip and not grid_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "validation_failed",
                "message": "One of `zip` or `grid_id` is required.",
            },
        )

    # Stub: real implementation joins the MCP enrichment cache. Until
    # then, the response mirrors app/src/mocks/context.zip.json so the
    # frontend mock and the real backend look the same.
    loc = CoarseLocation(zip=zip, grid_id=grid_id, resolution_m=5000 if zip else 1000)
    signals = [
        ContextSignal.model_validate(
            {
                "class": "vbd",
                "headline": "WNV-positive mosquito pools detected in Maricopa County this week.",
                "severity_tier": "advisory",
                "source": CitedSource(
                    name="VectorSurv (UCD DART)",
                    url="https://vectorsurv.org/",
                    mcp="vectorsurv-mcp",
                ),
            }
        )
    ]
    return ContextEnvelope(coarse_location=loc, signals=signals)
