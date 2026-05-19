"""211 Arizona MCP server.

A Model Context Protocol server that exposes 211 Arizona's heat-relief,
transport-to-cooling-center, utility-assistance, and crisis-referral
services as a set of tools an LLM can call.

Mock-by-default: 211 Arizona / Solari Crisis & Human Services does
not publish a public REST API, so the server ships a canned mock
backend with a clean swap-in path for a real backend via the
``AZ211_BACKEND_URL`` env var. Built for EpiHack Arizona 2026's heat
focus group; powers Scenario C in plan/04-data-flows.md.
"""

__version__ = "0.1.0"
