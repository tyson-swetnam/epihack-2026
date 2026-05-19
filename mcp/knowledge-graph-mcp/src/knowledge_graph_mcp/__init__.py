"""Knowledge-graph MCP server.

A Model Context Protocol server that gives an LLM read-only access to
the EpiHack Arizona 2026 DuckLake knowledge graph (the property-graph
encoding of `kg.node`, `kg.edge`, `kg.property` defined under
`schema/`). Built for the EpiHack agentic architecture so triage,
enrichment, and notification agents can query nodes / edges / paths
without writing SQL.
"""

__version__ = "0.1.0"
