"""FastMCP server exposing the EpiHack DuckLake knowledge graph as MCP tools.

The graph itself is the property-graph encoding seeded under
``schema/`` (``kg.node`` / ``kg.edge`` / ``kg.property``). This server
gives LLM clients (Claude Desktop, Claude Code, the agentic
architecture documented under ``plan/``, ...) read-only access to it
through a set of typed tools so the agents can ask things like:

    "Which pathogens are transmitted by Ixodes scapularis, and is
     there an active outbreak record for any of them in Coconino
     County?"

without having to write SQL. The escape-hatch ``kg_sql`` tool exists
for the rare case where an agent really does need to run a SELECT
that no convenience tool covers.

All DuckDB calls are synchronous; the tools wrap them with
``asyncio.to_thread`` so a slow query never blocks the MCP event loop.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Any

import duckdb
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from . import queries
from .loader import bootstrap

log = logging.getLogger(__name__)

mcp = FastMCP(
    "knowledge-graph",
    instructions=(
        "Read-only access to the EpiHack Arizona 2026 DuckLake "
        "knowledge graph (kg.node / kg.edge / kg.property). Start with "
        "`kg_search` or `kg_nodes_by_type` to find node IDs, then "
        "use `kg_node_lookup` for properties, `kg_neighborhood` for "
        "directly-connected nodes, and `kg_path` to trace relationships. "
        "Domain shortcuts (`kg_pathogens_by_vector`, "
        "`kg_outbreak_check`, `kg_regions_at_point`, ...) cover the "
        "common Heat + Wildlife/Vector-Borne agent queries. Use "
        "`kg_sql` only as an escape hatch -- it accepts SELECT-only "
        "statements and caps results at 5000 rows."
    ),
)


_conn: duckdb.DuckDBPyConnection | None = None
_conn_lock = asyncio.Lock()


async def _get_conn() -> duckdb.DuckDBPyConnection:
    global _conn
    if _conn is None:
        async with _conn_lock:
            if _conn is None:
                _conn = await asyncio.to_thread(bootstrap)
    return _conn


async def _run(fn, *args, **kwargs):
    conn = await _get_conn()
    return await asyncio.to_thread(fn, conn, *args, **kwargs)


# ----------------------------------------------------------------- core tools
@mcp.tool()
async def kg_node_lookup(
    node_id: Annotated[str, Field(description="Stable node slug, e.g. 'pathogen.wnv'.")],
) -> dict:
    """Return a single node plus its full property bag.

    Output: ``{node_id, node_type, label, description, source_fig,
    properties: {key: value, ...}}``. If no such node exists,
    returns ``{"found": false, "node_id": ...}``.
    """
    node = await _run(queries.node_lookup, node_id)
    if not node:
        return {"found": False, "node_id": node_id}
    return {"found": True, **node}


@mcp.tool()
async def kg_neighborhood(
    node_id: Annotated[str, Field(description="Centre of the neighbourhood, e.g. 'county.maricopa'.")],
    depth: Annotated[int, Field(ge=1, le=3, description="Hops to expand outward (max 3).")] = 1,
    predicate: Annotated[
        str | None,
        Field(description="Restrict to a single edge predicate, e.g. 'hasResource'."),
    ] = None,
) -> dict:
    """Return the node together with everything reachable within ``depth`` hops.

    Output: ``{root, depth, nodes: [...], edges: [...]}``. Edges are
    returned in both directions; nodes carry their property bags so
    the caller usually does not need a follow-up lookup.
    """
    return await _run(queries.neighborhood, node_id, depth, predicate)


@mcp.tool()
async def kg_path(
    from_id: Annotated[str, Field(description="Source node ID.")],
    to_id: Annotated[str, Field(description="Destination node ID.")],
    max_depth: Annotated[int, Field(ge=1, le=8, description="Maximum BFS depth.")] = 4,
) -> dict:
    """Shortest path between two nodes (BFS over the undirected edge projection).

    Output: ``{found, length, nodes: [n0, n1, ...], edges: [e0, ...]}``;
    ``found=False`` and an empty path when nothing is reachable within
    ``max_depth``.
    """
    return await _run(queries.shortest_path, from_id, to_id, max_depth)


@mcp.tool()
async def kg_search(
    query: Annotated[str, Field(description="Substring to match against label / description / id.")],
    node_type: Annotated[
        str | None,
        Field(description="Optional node_type filter, e.g. 'pathogen'."),
    ] = None,
    limit: Annotated[int, Field(ge=1, le=500)] = 50,
) -> dict:
    """Case-insensitive substring search over node labels, descriptions, and IDs."""
    rows = await _run(queries.search, query, node_type, limit)
    return {"query": query, "node_type": node_type, "results": rows, "count": len(rows)}


@mcp.tool()
async def kg_nodes_by_type(
    node_type: Annotated[str, Field(description="Node type, e.g. 'milestone', 'pathogen', 'county'.")],
    limit: Annotated[int, Field(ge=1, le=2000)] = 100,
) -> dict:
    """List nodes of a given type (alphabetical by ``node_id``)."""
    rows = await _run(queries.nodes_by_type, node_type, limit)
    return {"node_type": node_type, "results": rows, "count": len(rows)}


@mcp.tool()
async def kg_edges_by_predicate(
    predicate: Annotated[str, Field(description="Edge predicate, e.g. 'transmittedBy'.")],
    limit: Annotated[int, Field(ge=1, le=2000)] = 100,
) -> dict:
    """List edges with a given predicate."""
    rows = await _run(queries.edges_by_predicate, predicate, limit)
    return {"predicate": predicate, "results": rows, "count": len(rows)}


# --------------------------------------------------------- domain conveniences
@mcp.tool()
async def kg_regions_at_point(
    lat: Annotated[float, Field(ge=-90, le=90)],
    lon: Annotated[float, Field(ge=-180, le=180)],
    half_box_degrees: Annotated[
        float, Field(gt=0, le=5, description="Bounding-box half-size in degrees.")
    ] = 0.5,
) -> dict:
    """County / tribe / region nodes whose centroid brackets a coordinate.

    Returns an empty list when the loaded schema doesn't carry
    ``lat``/``lon`` properties on county or tribe nodes (the default
    seed under ``schema/deep/`` currently doesn't, so this is the
    expected fallback unless callers have loaded a centroids seed).
    """
    rows = await _run(queries.regions_at_point, lat, lon, half_box_degrees)
    return {"lat": lat, "lon": lon, "results": rows, "count": len(rows)}


@mcp.tool()
async def kg_pathogens_by_vector(
    vector_id: Annotated[str, Field(description="Vector node ID, e.g. 'vector.ixodes_scapularis'.")],
) -> dict:
    """Pathogens with ``transmittedBy --> vector_id`` edges."""
    rows = await _run(queries.pathogens_by_vector, vector_id)
    return {"vector_id": vector_id, "results": rows, "count": len(rows)}


@mcp.tool()
async def kg_pathogens_by_focus(
    focus_id: Annotated[str, Field(description="Focus-area node ID, e.g. 'focus.wildlife_vbd'.")],
) -> dict:
    """Pathogens with ``targetsFocusArea --> focus_id`` edges."""
    rows = await _run(queries.pathogens_by_focus, focus_id)
    return {"focus_id": focus_id, "results": rows, "count": len(rows)}


@mcp.tool()
async def kg_outbreak_check(
    pathogen_id: Annotated[str, Field(description="Pathogen node ID, e.g. 'pathogen.wnv'.")],
    county_id: Annotated[
        str | None,
        Field(description="Optional county node ID to filter ``occurredIn``."),
    ] = None,
) -> dict:
    """Outbreak nodes ``causedBy`` the pathogen, optionally ``occurredIn`` a county."""
    rows = await _run(queries.outbreak_check, pathogen_id, county_id)
    return {
        "pathogen_id": pathogen_id,
        "county_id": county_id,
        "results": rows,
        "count": len(rows),
    }


@mcp.tool()
async def kg_resource_lookup(
    question_id: Annotated[
        str,
        Field(description="World-cafe question ID, e.g. 'wv.q2' or 'heat.q4'."),
    ],
) -> dict:
    """Resources / datasets / APIs that ``informs`` a given question."""
    rows = await _run(queries.resources_for_question, question_id)
    return {"question_id": question_id, "results": rows, "count": len(rows)}


# ---------------------------------------------------------------- escape hatch
@mcp.tool()
async def kg_sql(
    sql: Annotated[
        str,
        Field(description="A single SELECT or WITH ... SELECT statement against the kg schema."),
    ],
    params: Annotated[
        list[Any] | None,
        Field(description="Positional parameters for the query (DuckDB '?' placeholders)."),
    ] = None,
) -> dict:
    """Escape hatch: run an arbitrary read-only SELECT against the kg schema.

    Rejects anything that isn't a single SELECT / WITH statement, and
    transparently wraps the query in ``LIMIT 5000`` so a runaway scan
    can't blow up the agent's context. Use the dedicated tools
    (`kg_neighborhood`, `kg_path`, etc.) whenever they cover your
    query; this is here for the long tail.
    """
    try:
        return await _run(queries.run_select, sql, params)
    except queries.UnsafeSQLError as exc:
        return {"error": str(exc), "rows": [], "row_count": 0}


# ----------------------------------------------------------------- resources
@mcp.resource("kg://node-types")
async def node_types_resource() -> str:
    types = await _run(queries.distinct_node_types)
    return "\n".join(types) if types else "(no node types loaded)"


@mcp.resource("kg://predicates")
async def predicates_resource() -> str:
    predicates = await _run(queries.distinct_predicates)
    return "\n".join(predicates) if predicates else "(no edges loaded)"


@mcp.resource("kg://schema")
def schema_resource() -> str:
    """Static rendering of the kg.node / kg.edge / kg.property column shapes."""
    return (
        "kg.node\n"
        "  node_id     VARCHAR  PRIMARY KEY\n"
        "  node_type   VARCHAR  NOT NULL    -- 'parameter', 'milestone', 'pathogen', ...\n"
        "  label       VARCHAR  NOT NULL\n"
        "  description VARCHAR\n"
        "  source_fig  VARCHAR\n"
        "  created_at  TIMESTAMP DEFAULT current_timestamp\n"
        "\n"
        "kg.edge\n"
        "  edge_id     BIGINT   PRIMARY KEY\n"
        "  subject_id  VARCHAR  NOT NULL  REFERENCES kg.node(node_id)\n"
        "  predicate   VARCHAR  NOT NULL  -- 'belongsTo', 'transmittedBy', ...\n"
        "  object_id   VARCHAR  NOT NULL  REFERENCES kg.node(node_id)\n"
        "  source_fig  VARCHAR\n"
        "\n"
        "kg.property\n"
        "  node_id    VARCHAR REFERENCES kg.node(node_id)\n"
        "  key        VARCHAR\n"
        "  value_text VARCHAR\n"
        "  value_num  DOUBLE\n"
        "  PRIMARY KEY (node_id, key)\n"
        "\n"
        "Each property bag is keyed (node_id, key); a value lives in\n"
        "either value_text or value_num depending on type. The MCP\n"
        "tools collapse this back into a single dict per node.\n"
    )
