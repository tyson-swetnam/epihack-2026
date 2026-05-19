"""Thin async wrapper around the ``mcp`` Python package.

The pipeline calls MCP servers (vectorsurv-mcp, nws-heatrisk-mcp,
knowledge-graph-mcp, great-az-tick-check-mcp, ...) through this
client. The default :class:`MCPClient` is a Protocol; production code
will use :class:`StdioMCPClient` which spawns each MCP server over
stdio per the ``mcp`` package's reference client.

For tests and offline runs we ship :class:`FakeMCPClient`, an
in-memory dict-of-tool-name -> async callable. Every Scenario A / C
tool call from ``plan/04-data-flows.md`` has a canned response
registered out of the box.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, Protocol


ToolHandler = Callable[..., Awaitable[dict[str, Any]]]


class MCPClient(Protocol):
    """Minimum surface area the agents call.

    Implementations may be real (stdio / streamable-http against an
    actual ``mcp`` server) or fake (canned responses for tests).
    """

    async def call_tool(
        self, server: str, tool: str, **kwargs: Any
    ) -> dict[str, Any]:
        ...

    async def list_tools(self, server: str) -> list[str]:
        ...


class FakeMCPClient:
    """In-memory MCP client backed by a handler registry.

    Every Scenario A / C tool call referenced in ``plan/04-data-flows.md``
    is registered by :meth:`with_default_handlers` so the worked
    end-to-end tests pass without any network.
    """

    def __init__(self) -> None:
        self._handlers: dict[tuple[str, str], ToolHandler] = {}
        self.calls: list[dict[str, Any]] = []

    def register(self, server: str, tool: str, handler: ToolHandler) -> None:
        self._handlers[(server, tool)] = handler

    async def call_tool(
        self, server: str, tool: str, **kwargs: Any
    ) -> dict[str, Any]:
        self.calls.append({"server": server, "tool": tool, "args": dict(kwargs)})
        handler = self._handlers.get((server, tool))
        if handler is None:
            raise LookupError(
                f"FakeMCPClient has no handler for {server}.{tool}; "
                f"registered: {sorted(self._handlers)}"
            )
        return await handler(**kwargs)

    async def list_tools(self, server: str) -> list[str]:
        return [t for (s, t) in self._handlers if s == server]

    # ------------------------------------------------------------------
    # Default canned responses
    # ------------------------------------------------------------------
    @classmethod
    def with_default_handlers(cls) -> "FakeMCPClient":
        client = cls()

        # knowledge-graph-mcp.regions_at_point ----------------------------
        async def regions_at_point(lat: float, lon: float) -> dict[str, Any]:
            # Scenario A: Patagonia, Santa Cruz County (~31.54, -110.75).
            # Scenario C: downtown Phoenix (~33.45, -112.07).
            if -111.5 < lon < -110.0 and 31.0 < lat < 32.0:
                return {
                    "county_id": "county.santa_cruz",
                    "tribe_id": None,
                    "region_id": "region.border_corridor",
                    "zcta": "85624",
                }
            if -112.5 < lon < -111.5 and 33.0 < lat < 34.0:
                return {
                    "county_id": "county.maricopa",
                    "tribe_id": None,
                    "region_id": "region.maricopa_metro",
                    "zcta": "85003",
                }
            return {
                "county_id": None,
                "tribe_id": None,
                "region_id": "region.statewide",
                "zcta": None,
            }

        client.register(
            "knowledge-graph-mcp", "kg_regions_at_point", regions_at_point
        )

        # knowledge-graph-mcp.outbreak_check ------------------------------
        async def outbreak_check(
            pathogen_id: str | None = None,
            county_id: str | None = None,
            # Tolerate legacy callers that still pass the un-suffixed names.
            **_: Any,
        ) -> dict[str, Any]:
            return {"active_outbreaks": []}

        client.register(
            "knowledge-graph-mcp", "kg_outbreak_check", outbreak_check
        )

        # vectorsurv-mcp.agency_region_intersect --------------------------
        async def agency_region_intersect(**_: Any) -> dict[str, Any]:
            return {
                "intersections": [
                    {
                        "agency": "Santa Cruz County Vector Control",
                        "region": "county.santa_cruz",
                    }
                ]
            }

        client.register(
            "vectorsurv-mcp", "vectorsurv_agency_region_intersect", agency_region_intersect
        )

        # vectorsurv-mcp.get_pools ----------------------------------------
        async def get_pools(**kwargs: Any) -> dict[str, Any]:
            # No nearby WNV / tick pools in the worked scenarios.
            return {"pools": [], "count": 0, "query": kwargs}

        client.register("vectorsurv-mcp", "vectorsurv_get_pools", get_pools)

        # great-az-tick-check-mcp.create_submission -----------------------
        async def create_submission(**kwargs: Any) -> dict[str, Any]:
            return {
                "submission_id": "gatc-2026-000123",
                "mailing_label_pdf": "https://gatickcheck.example/labels/000123.pdf",
                "icd10_reference": "A77.0",
                "watchlist_days": 14,
            }

        client.register(
            "great-az-tick-check-mcp", "gattc_create_submission", create_submission
        )

        # nws-heatrisk-mcp.heatrisk ---------------------------------------
        async def heatrisk(
            lat: float, lon: float, date: str | None = None
        ) -> dict[str, Any]:
            # Scenario C: Magenta day in Phoenix.
            level = "Magenta" if -112.5 < lon < -111.5 and 33.0 < lat < 34.0 else "Yellow"
            return {
                "level": level,
                "lat": lat,
                "lon": lon,
                "date": date,
                "ambient_temp_f": 115.0 if level == "Magenta" else 92.0,
            }

        client.register("nws-heatrisk-mcp", "nws_heatrisk", heatrisk)

        # mag-hrn-mcp.search_centers (cooling centers) --------------------
        async def search_centers(**kwargs: Any) -> dict[str, Any]:
            return {
                "centers": [
                    {
                        "id": "center.phx_central_library",
                        "name": "Burton Barr Central Library cooling center",
                        "address": "1221 N Central Ave, Phoenix, AZ 85004",
                        "open_now": True,
                        "pets_ok": False,
                        "distance_km": 0.6,
                    },
                    {
                        "id": "center.phx_human_services",
                        "name": "Human Services Campus respite center",
                        "address": "204 S 12th Ave, Phoenix, AZ 85007",
                        "open_now": True,
                        "pets_ok": True,
                        "distance_km": 1.2,
                    },
                ]
            }

        client.register("mag-hrn-mcp", "mag_search_centers", search_centers)

        # 211-az-mcp.transport_to_cooling_center --------------------------
        async def transport_to_cooling_center(**kwargs: Any) -> dict[str, Any]:
            return {
                "dispatched": True,
                "eta_minutes": 18,
                "provider": "211 Arizona heat-relief rideshare",
            }

        client.register(
            "211-az-mcp",
            "az211_transport_to_cooling_center",
            transport_to_cooling_center,
        )

        return client


class StdioMCPClient:
    """Real client over the official ``mcp`` python package (stdio).

    Each :meth:`call_tool` opens a fresh subprocess session per server
    name; for production you'll want a connection pool. This is the
    minimum needed for hand-testing against a real MCP server.
    """

    def __init__(self, server_commands: dict[str, list[str]]):
        self.server_commands = server_commands
        self._lock = asyncio.Lock()

    async def call_tool(
        self, server: str, tool: str, **kwargs: Any
    ) -> dict[str, Any]:
        # Lazy import keeps tests offline-friendly.
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        cmd = self.server_commands.get(server)
        if cmd is None:
            raise LookupError(f"No stdio command registered for server '{server}'.")
        params = StdioServerParameters(command=cmd[0], args=cmd[1:])
        async with self._lock:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool, arguments=kwargs)
                    payload: dict[str, Any] = {}
                    for content in result.content:
                        if getattr(content, "type", None) == "text":
                            payload.setdefault("text", []).append(content.text)
                    return payload or {"raw": str(result)}

    async def list_tools(self, server: str) -> list[str]:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        cmd = self.server_commands.get(server)
        if cmd is None:
            raise LookupError(f"No stdio command registered for server '{server}'.")
        params = StdioServerParameters(command=cmd[0], args=cmd[1:])
        async with self._lock:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    listed = await session.list_tools()
                    return [t.name for t in listed.tools]


__all__ = ["MCPClient", "FakeMCPClient", "StdioMCPClient", "ToolHandler"]
