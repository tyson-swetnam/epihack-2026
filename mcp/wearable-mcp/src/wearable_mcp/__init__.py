"""Wearable MCP server.

A Model Context Protocol server that exposes user-consented wearable
readings (heart rate, skin temperature, HRV, steps) to LLM clients
for the AZ One Health Sentinel Heat vertical. Mock-by-default; the
real backend is the on-device store that ``app/shared/wearable.js``
populates from HealthKit / Health Connect.

Built for EpiHack Arizona 2026 (Phase 4 of the roadmap).
"""

__version__ = "0.1.0"
