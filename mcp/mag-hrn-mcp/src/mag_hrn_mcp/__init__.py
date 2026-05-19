"""MAG Heat Relief Network MCP server.

A Model Context Protocol server wrapping the Maricopa Association of
Governments Heat Relief Network -- ~200+ cooling, hydration, respite,
and donation-drop-off sites across the Phoenix metro that operate
each year from **May 1 through September 30**.

The HRN's public storefront is https://hrn.azmag.gov/ and is backed
by an ArcGIS map service at
``https://geo.azmag.gov/arcgis/rest/services/maps/Heat_Relief_Network``.
That URL has drifted across HRN seasons in the past, so this server
defaults to a small canned dataset and only hits the real service
when ``MAG_HRN_FEATURE_SERVICE_URL`` is set.

Built for EpiHack Arizona 2026's heat focus group; the ``mag-hrn-mcp``
server is the cooling-center lookup half of Heat-Q1 and the
real-time-status-feed gap that Heat-Q2 is trying to close.
"""

__version__ = "0.1.0"
