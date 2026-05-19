"""KnowledgeUpdateAgent -- nightly + on-demand MCP pull.

Given a list of MCP server names, fetch each server's "recent
records" tool and shape the rows as :class:`Observation`
``kind=mcp_pull`` entries. The stub knows about three servers:

* ``vectorsurv-mcp`` -> ``get_pools`` (treated as one observation per pool).
* ``nws-heatrisk-mcp`` -> ``heatrisk`` for a fixed AZ anchor.
* ``knowledge-graph-mcp`` -> ``outbreak_check`` for active outbreaks.

Real production code extends this dispatch table per MCP server.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .contracts import (
    Channel,
    EnvironmentalClass,
    GeneralClass,
    HeatRisk,
    Kind,
    MinimumDataset,
    Observation,
    Vertical,
)
from .mcp_client import MCPClient


class KnowledgeUpdateAgent:
    name = "knowledge_update"

    def __init__(self, mcp: MCPClient) -> None:
        self.mcp = mcp

    async def run(self, servers: list[str]) -> list[Observation]:
        out: list[Observation] = []
        for server in servers:
            try:
                if server == "vectorsurv-mcp":
                    out.extend(await self._pull_vectorsurv())
                elif server == "nws-heatrisk-mcp":
                    out.extend(await self._pull_heatrisk())
                elif server == "knowledge-graph-mcp":
                    out.extend(await self._pull_outbreaks())
                # Unknown server -> silently skip; real code logs.
            except (LookupError, RuntimeError, ConnectionError):
                continue
        return out

    async def _pull_vectorsurv(self) -> list[Observation]:
        payload = await self.mcp.call_tool(
            "vectorsurv-mcp",
            "get_pools",
            arthropod="mosquito",
            last_days=7,
        )
        obs = []
        for pool in payload.get("pools", []):
            obs.append(
                Observation(
                    kind=Kind.MCP_PULL,
                    vertical=Vertical.VBD,
                    source=Channel.WEB,
                    dataset=MinimumDataset(
                        general=GeneralClass(
                            reported_at=pool.get(
                                "collected_at",
                                datetime.now(timezone.utc).isoformat(),
                            ),
                            lat=pool.get("lat"),
                            lon=pool.get("lon"),
                        ),
                        environmental=EnvironmentalClass(
                            vector_density=pool.get("count"),
                        ),
                    ),
                )
            )
        return obs

    async def _pull_heatrisk(self) -> list[Observation]:
        # Phoenix anchor for the daily pull.
        payload = await self.mcp.call_tool(
            "nws-heatrisk-mcp",
            "heatrisk",
            lat=33.45,
            lon=-112.07,
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        )
        level_str = payload.get("level")
        try:
            level = HeatRisk(level_str) if level_str else None
        except ValueError:
            level = None
        return [
            Observation(
                kind=Kind.MCP_PULL,
                vertical=Vertical.HEAT,
                source=Channel.WEB,
                dataset=MinimumDataset(
                    general=GeneralClass(
                        lat=33.45,
                        lon=-112.07,
                        postal_code="85003",
                    ),
                    environmental=EnvironmentalClass(
                        nws_heatrisk_level=level,
                        ambient_temp_f=payload.get("ambient_temp_f"),
                    ),
                ),
            )
        ]

    async def _pull_outbreaks(self) -> list[Observation]:
        payload: dict[str, Any] = await self.mcp.call_tool(
            "knowledge-graph-mcp", "outbreak_check"
        )
        obs = []
        for outbreak in payload.get("active_outbreaks", []):
            obs.append(
                Observation(
                    kind=Kind.MCP_PULL,
                    vertical=Vertical(outbreak.get("vertical", "vbd")),
                    source=Channel.WEB,
                    dataset=MinimumDataset(
                        general=GeneralClass(
                            reported_at=outbreak.get("declared_at"),
                            postal_code=outbreak.get("zcta"),
                        ),
                    ),
                )
            )
        return obs


__all__ = ["KnowledgeUpdateAgent"]
