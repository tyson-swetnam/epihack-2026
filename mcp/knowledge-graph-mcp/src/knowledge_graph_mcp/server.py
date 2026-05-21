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

from . import aggregation, cluster_scan, normalize, queries
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


# --------------------------------------------------------- aggregation tools
@mcp.tool()
async def kg_observations_by_window(
    start_date: Annotated[
        str, Field(description="Inclusive start date (YYYY-MM-DD or full ISO timestamp).")
    ],
    end_date: Annotated[
        str, Field(description="Inclusive end date (YYYY-MM-DD or full ISO timestamp).")
    ],
    vertical: Annotated[
        str | None,
        Field(description="Optional filter: 'vbd' / 'heat' / 'both' / 'neither'."),
    ] = None,
    county_id: Annotated[
        str | None,
        Field(description="Optional county.* slug to filter on (colocatedWith)."),
    ] = None,
    pathogen_id: Annotated[
        str | None,
        Field(description="Optional pathogen.* slug to filter on (reportsAbout)."),
    ] = None,
) -> dict:
    """Server-side rollup of observations bucketed by (iso_week, county, pathogen).

    Returns rows ``{iso_week, county_id, pathogen_id, observation_count,
    severity_max, triage_class_breakdown: {tc.x: n, ...}}``. Use this
    instead of crafting a custom ``kg_sql`` GROUP BY when you want a
    weekly heat-map / dashboard view.
    """
    try:
        rows = await _run(
            aggregation.observations_by_window,
            start_date,
            end_date,
            vertical,
            county_id,
            pathogen_id,
        )
    except ValueError as exc:
        return {"error": str(exc), "results": [], "count": 0}
    return {
        "start_date": start_date,
        "end_date": end_date,
        "vertical": vertical,
        "county_id": county_id,
        "pathogen_id": pathogen_id,
        "results": rows,
        "count": len(rows),
    }


@mcp.tool()
async def kg_cluster_scan(
    vertical: Annotated[
        str,
        Field(description="Surveillance vertical: 'vbd' / 'heat' / 'both' / 'neither'."),
    ],
    lookback_days: Annotated[
        int,
        Field(ge=1, le=120, description="Days back from now to load observations."),
    ] = 14,
    county_id: Annotated[
        str | None,
        Field(description="Optional county.* slug; restricts the scan to that county."),
    ] = None,
) -> dict:
    """Run ``ClusterDetectionAgent`` against recent kg observations.

    Reconstructs lightweight ``Observation`` records from
    ``kg.node(node_type='observation')`` plus its ``colocatedWith`` /
    ``reportsAbout`` edges and hands them to the calibrated two-tier
    detector in ``onehealth_agents.cluster``. Returns one row per
    emitted ``ClusterAlert`` with ``zcta, observed, expected,
    tier1_score, tier2_posterior, severity, alert_status, ...``.
    """
    try:
        rows = await _run(
            cluster_scan.cluster_scan,
            vertical,
            lookback_days,
            county_id,
        )
    except ValueError as exc:
        return {"error": str(exc), "results": [], "count": 0}
    except ImportError as exc:
        return {"error": f"onehealth-agents not installed: {exc}", "results": [], "count": 0}
    return {
        "vertical": vertical,
        "lookback_days": lookback_days,
        "county_id": county_id,
        "results": rows,
        "count": len(rows),
    }


@mcp.tool()
async def kg_milestone_intervals(
    start_date: Annotated[
        str, Field(description="Inclusive start date (matches detect_at).")
    ],
    end_date: Annotated[
        str, Field(description="Inclusive end date (matches detect_at).")
    ],
    vertical: Annotated[
        str | None,
        Field(description="Optional vertical filter (vbd / heat / both / neither)."),
    ] = None,
    agency: Annotated[
        str | None,
        Field(description="Optional responsible_vector_control_agency filter."),
    ] = None,
) -> dict:
    """Per-observation timeliness pivot joined with the cost rollup.

    Joins ``kg.v_observation_timeliness`` against ``kg.node`` /
    ``kg.property``, then folds in the per-observation cost summary
    aggregated from ``kg.agent_run``. Returns one row per observation
    with the five Figure-3 milestone timestamps + four interval-in-
    minutes columns + cost + token totals.
    """
    try:
        rows = await _run(
            aggregation.milestone_intervals,
            start_date,
            end_date,
            vertical,
            agency,
        )
    except ValueError as exc:
        return {"error": str(exc), "results": [], "count": 0}
    return {
        "start_date": start_date,
        "end_date": end_date,
        "vertical": vertical,
        "agency": agency,
        "results": rows,
        "count": len(rows),
    }


@mcp.tool()
async def kg_normalize_diagnosis(
    diagnosis_text: Annotated[
        str, Field(description="Free-text diagnosis, e.g. 'plague', 'Y. pestis', 'A20.0'.")
    ],
    vocabulary_hint: Annotated[
        str | None,
        Field(description="Optional hint: 'icd10' or 'snomed' to narrow the resolver."),
    ] = None,
) -> dict:
    """Fuzzy + alias normalisation of a diagnosis string to a pathogen.* slug.

    Resolution order: exact ICD-10 -> exact SNOMED CT -> curated alias
    -> substring -> fuzzy similarity. Returns ``{pathogen_id,
    snomed_code, icd10_code, confidence, match_reason}`` with
    ``pathogen_id=None`` when nothing crosses the confidence floor.
    """
    return await _run(
        normalize.normalize_diagnosis,
        diagnosis_text,
        vocabulary_hint,
    )


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


@mcp.resource("kg://aggregation-tools")
def aggregation_tools_resource() -> str:
    """Guidance for the four aggregation-MCP tools the dashboard surfaces.

    Lists each tool, its input contract, and when to reach for it vs
    the lower-level ``kg_sql`` escape hatch.
    """
    return (
        "Aggregation tools (extending kg-mcp; flagged by the agency-dashboard sub-agent)\n"
        "===============================================================================\n"
        "\n"
        "kg_observations_by_window\n"
        "  Args: start_date, end_date, vertical?, county_id?, pathogen_id?\n"
        "  Returns: [{iso_week, county_id, pathogen_id, observation_count,\n"
        "            severity_max, triage_class_breakdown}]\n"
        "  Use when: building a weekly heat-map or per-county dashboard;\n"
        "  prefer this over a custom kg_sql GROUP BY because it correctly\n"
        "  de-dupes observations that have multiple county or pathogen edges.\n"
        "\n"
        "kg_cluster_scan\n"
        "  Args: vertical, lookback_days=14, county_id?\n"
        "  Returns: [{zcta, observed, expected, tier1_score, tier2_posterior,\n"
        "            severity, alert_status, pathogen_hint, historical_match, ...}]\n"
        "  Use when: surfacing live calibrated cluster alerts on the agency\n"
        "  dashboard. Wraps ClusterDetectionAgent (Tier-1 deterministic + Tier-2\n"
        "  Gamma-Poisson posterior). Pure-Python call; does not write back to\n"
        "  the kg.\n"
        "\n"
        "kg_milestone_intervals\n"
        "  Args: start_date, end_date, vertical?, agency?\n"
        "  Returns: [{observation_id, detect_at, notify_at, verify_at_provisional,\n"
        "            lab_at_provisional, respond_at, detect_to_notify_min, ...,\n"
        "            cost_usd_total, run_count, prompt_tokens_total, ...}]\n"
        "  Use when: rendering the Figure-3 timeliness clock or the cost panel.\n"
        "  Joins kg.v_observation_timeliness + kg.v_agent_run_cost so the caller\n"
        "  doesn't have to know the underlying view shape.\n"
        "\n"
        "kg_normalize_diagnosis\n"
        "  Args: diagnosis_text, vocabulary_hint? ('icd10' | 'snomed')\n"
        "  Returns: {pathogen_id, snomed_code, icd10_code, confidence, match_reason}\n"
        "  Use when: an inbound report (SMS, voice, agency case) carries a free-\n"
        "  text diagnosis that needs canonicalising before reportsAbout edges or\n"
        "  cluster scans can fire. Resolution order: exact ICD-10 -> exact\n"
        "  SNOMED CT -> curated alias -> substring -> fuzzy similarity.\n"
        "\n"
        "When NOT to use these vs kg_sql:\n"
        "  - kg_sql is the right tool when you need a single ad-hoc query that\n"
        "    isn't a rollup, isn't a cluster scan, and isn't a normalisation.\n"
        "    The aggregation tools cap the surface area so dashboards can't\n"
        "    silently start scanning unbounded data on every render.\n"
    )


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
