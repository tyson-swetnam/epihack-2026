"""ADHS MCP server.

A Model Context Protocol server wrapping the Arizona Department of
Health Services' public surveillance data: weekly arbovirus reports,
the annual heat-mortality surveillance series, and reportable zoonotic
case counts (hantavirus, plague, rabies, RMSF, tularemia).

ADHS does not publish a clean REST API today -- most data is
distributed as PDFs (heat mortality, vector-borne reports) or hosted
on ArcGIS Experience dashboards (Heat Preparedness Network). This
server ships with **canned data** sourced from the report series and
the EpiHack knowledge graph so the rest of the stack can develop
against a stable shape. Set ``ADHS_BACKEND_URL`` in the environment to
swap the canned data for a real HTTP backend once one ships.

Built for EpiHack Arizona 2026's Heat and Wildlife / Vector-Borne
Diseases focus groups.
"""

__version__ = "0.1.0"
