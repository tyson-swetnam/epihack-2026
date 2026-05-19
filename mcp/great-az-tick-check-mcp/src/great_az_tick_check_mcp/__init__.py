"""Great Arizona Tick Check MCP server.

A Model Context Protocol server for the UA Cooperative Extension
Great Arizona Tick Check program (Dr. Kathleen Walker lab,
Department of Entomology, University of Arizona). There is no
public REST API today, so the default backend is an **in-memory
mock** that other team members can swap for a real one once the
Walker lab ships one. Set ``GATTC_BACKEND_URL`` to point at a real
service.

Built for EpiHack Arizona 2026's wildlife and vector-borne diseases
focus group.
"""

__version__ = "0.1.0"
