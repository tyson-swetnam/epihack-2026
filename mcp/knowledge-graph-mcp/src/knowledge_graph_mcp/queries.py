"""SQL query helpers against the ``kg.node`` / ``kg.edge`` / ``kg.property`` schema.

The functions here either return ``(sql, params)`` tuples for the
server to execute, or they execute on a passed-in DuckDB connection
and return Python dictionaries. They are intentionally synchronous --
DuckDB's API is sync, so the MCP layer wraps these calls in
``asyncio.to_thread``.

All queries are read-only. The ``run_select`` helper enforces a
single ``SELECT`` / ``WITH`` statement and caps the result row count
so the SQL escape hatch can't be used to scan unbounded data.
"""

from __future__ import annotations

import re
from collections import deque
from typing import Any

import duckdb

MAX_DEPTH = 3
PATH_MAX_DEPTH = 4
SQL_ROW_CAP = 5000


# ---------------------------------------------------------------- helpers
def _fetch_dicts(conn: duckdb.DuckDBPyConnection, sql: str, params: tuple = ()) -> list[dict]:
    cur = conn.execute(sql, params)
    cols = [c[0] for c in cur.description] if cur.description else []
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _node_row(conn: duckdb.DuckDBPyConnection, node_id: str) -> dict | None:
    rows = _fetch_dicts(
        conn,
        "SELECT node_id, node_type, label, description, source_fig "
        "FROM kg.node WHERE node_id = ?",
        (node_id,),
    )
    return rows[0] if rows else None


def _node_properties(conn: duckdb.DuckDBPyConnection, node_id: str) -> dict[str, Any]:
    rows = _fetch_dicts(
        conn,
        "SELECT key, value_text, value_num FROM kg.property WHERE node_id = ? ORDER BY key",
        (node_id,),
    )
    props: dict[str, Any] = {}
    for r in rows:
        if r["value_text"] is not None:
            props[r["key"]] = r["value_text"]
        elif r["value_num"] is not None:
            props[r["key"]] = r["value_num"]
        else:
            props[r["key"]] = None
    return props


# ------------------------------------------------------------------ node lookup
def node_lookup(conn: duckdb.DuckDBPyConnection, node_id: str) -> dict | None:
    node = _node_row(conn, node_id)
    if not node:
        return None
    node["properties"] = _node_properties(conn, node_id)
    return node


# ----------------------------------------------------------------- neighborhood
def neighborhood(
    conn: duckdb.DuckDBPyConnection,
    node_id: str,
    depth: int = 1,
    predicate: str | None = None,
) -> dict:
    depth = max(1, min(int(depth), MAX_DEPTH))

    visited: set[str] = {node_id}
    frontier: set[str] = {node_id}
    edges: list[dict] = []
    edge_ids_seen: set[int] = set()

    for _ in range(depth):
        if not frontier:
            break
        # parameterise the IN-list explicitly; DuckDB doesn't bind a list directly here.
        placeholders = ", ".join(["?"] * len(frontier))
        sql = (
            "SELECT edge_id, subject_id, predicate, object_id, source_fig "
            "FROM kg.edge "
            f"WHERE (subject_id IN ({placeholders}) OR object_id IN ({placeholders}))"
        )
        params: list[Any] = list(frontier) + list(frontier)
        if predicate:
            sql += " AND predicate = ?"
            params.append(predicate)
        rows = _fetch_dicts(conn, sql, tuple(params))
        next_frontier: set[str] = set()
        for r in rows:
            if r["edge_id"] in edge_ids_seen:
                continue
            edge_ids_seen.add(r["edge_id"])
            edges.append(r)
            for nid in (r["subject_id"], r["object_id"]):
                if nid not in visited:
                    next_frontier.add(nid)
                    visited.add(nid)
        frontier = next_frontier

    # Pull node detail for everything we touched.
    nodes: list[dict] = []
    if visited:
        placeholders = ", ".join(["?"] * len(visited))
        node_rows = _fetch_dicts(
            conn,
            "SELECT node_id, node_type, label, description, source_fig "
            f"FROM kg.node WHERE node_id IN ({placeholders})",
            tuple(visited),
        )
        for n in node_rows:
            n["properties"] = _node_properties(conn, n["node_id"])
            nodes.append(n)
    return {"root": node_id, "depth": depth, "nodes": nodes, "edges": edges}


# ----------------------------------------------------------------- shortest path
def shortest_path(
    conn: duckdb.DuckDBPyConnection,
    from_id: str,
    to_id: str,
    max_depth: int = PATH_MAX_DEPTH,
) -> dict:
    """BFS over the undirected projection of kg.edge."""
    max_depth = max(1, min(int(max_depth), 8))
    if from_id == to_id:
        node = node_lookup(conn, from_id)
        return {"found": True, "length": 0, "nodes": [node] if node else [], "edges": []}

    # Pull all edges once -- the graph is small (low thousands at most).
    all_edges = _fetch_dicts(
        conn,
        "SELECT edge_id, subject_id, predicate, object_id, source_fig FROM kg.edge",
    )
    adj: dict[str, list[dict]] = {}
    for e in all_edges:
        adj.setdefault(e["subject_id"], []).append(e)
        adj.setdefault(e["object_id"], []).append(e)

    parents: dict[str, tuple[str, dict]] = {}
    queue = deque([(from_id, 0)])
    visited: set[str] = {from_id}
    found = False
    while queue:
        current, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for edge in adj.get(current, []):
            neighbor = edge["object_id"] if edge["subject_id"] == current else edge["subject_id"]
            if neighbor in visited:
                continue
            visited.add(neighbor)
            parents[neighbor] = (current, edge)
            if neighbor == to_id:
                found = True
                queue.clear()
                break
            queue.append((neighbor, depth + 1))

    if not found:
        return {"found": False, "length": 0, "nodes": [], "edges": []}

    # Reconstruct path.
    path_nodes_ids: list[str] = [to_id]
    path_edges: list[dict] = []
    cur = to_id
    while cur != from_id:
        prev, edge = parents[cur]
        path_edges.append(edge)
        path_nodes_ids.append(prev)
        cur = prev
    path_nodes_ids.reverse()
    path_edges.reverse()

    nodes = [node_lookup(conn, nid) for nid in path_nodes_ids]
    return {
        "found": True,
        "length": len(path_edges),
        "nodes": [n for n in nodes if n],
        "edges": path_edges,
    }


# ----------------------------------------------------------------- text search
def search(
    conn: duckdb.DuckDBPyConnection,
    query: str,
    node_type: str | None = None,
    limit: int = 50,
) -> list[dict]:
    like = f"%{query.lower()}%"
    sql = (
        "SELECT node_id, node_type, label, description, source_fig "
        "FROM kg.node "
        "WHERE (lower(label) LIKE ? OR lower(coalesce(description, '')) LIKE ? "
        "       OR lower(node_id) LIKE ?)"
    )
    params: list[Any] = [like, like, like]
    if node_type:
        sql += " AND node_type = ?"
        params.append(node_type)
    sql += " ORDER BY node_type, node_id LIMIT ?"
    params.append(int(limit))
    return _fetch_dicts(conn, sql, tuple(params))


def nodes_by_type(
    conn: duckdb.DuckDBPyConnection, node_type: str, limit: int = 100
) -> list[dict]:
    return _fetch_dicts(
        conn,
        "SELECT node_id, node_type, label, description, source_fig "
        "FROM kg.node WHERE node_type = ? ORDER BY node_id LIMIT ?",
        (node_type, int(limit)),
    )


def edges_by_predicate(
    conn: duckdb.DuckDBPyConnection, predicate: str, limit: int = 100
) -> list[dict]:
    return _fetch_dicts(
        conn,
        "SELECT edge_id, subject_id, predicate, object_id, source_fig "
        "FROM kg.edge WHERE predicate = ? ORDER BY edge_id LIMIT ?",
        (predicate, int(limit)),
    )


# --------------------------------------------------------- domain conveniences
def pathogens_by_vector(conn: duckdb.DuckDBPyConnection, vector_id: str) -> list[dict]:
    return _fetch_dicts(
        conn,
        "SELECT n.node_id, n.node_type, n.label, n.description, n.source_fig "
        "FROM kg.edge e "
        "JOIN kg.node n ON n.node_id = e.subject_id "
        "WHERE e.predicate = 'transmittedBy' AND e.object_id = ? "
        "ORDER BY n.node_id",
        (vector_id,),
    )


def pathogens_by_focus(conn: duckdb.DuckDBPyConnection, focus_id: str) -> list[dict]:
    return _fetch_dicts(
        conn,
        "SELECT n.node_id, n.node_type, n.label, n.description, n.source_fig "
        "FROM kg.edge e "
        "JOIN kg.node n ON n.node_id = e.subject_id "
        "WHERE e.predicate = 'targetsFocusArea' AND e.object_id = ? "
        "  AND n.node_type = 'pathogen' "
        "ORDER BY n.node_id",
        (focus_id,),
    )


def outbreak_check(
    conn: duckdb.DuckDBPyConnection, pathogen_id: str, county_id: str | None = None
) -> list[dict]:
    sql = (
        "SELECT DISTINCT n.node_id, n.node_type, n.label, n.description, n.source_fig "
        "FROM kg.edge e "
        "JOIN kg.node n ON n.node_id = e.subject_id "
        "WHERE e.predicate = 'causedBy' AND e.object_id = ?"
    )
    params: list[Any] = [pathogen_id]
    if county_id:
        sql += (
            " AND EXISTS ("
            "  SELECT 1 FROM kg.edge e2 "
            "  WHERE e2.subject_id = n.node_id "
            "    AND e2.predicate = 'occurredIn' "
            "    AND e2.object_id = ?"
            ")"
        )
        params.append(county_id)
    sql += " ORDER BY n.node_id"
    return _fetch_dicts(conn, sql, tuple(params))


def resources_for_question(
    conn: duckdb.DuckDBPyConnection, question_id: str
) -> list[dict]:
    return _fetch_dicts(
        conn,
        "SELECT DISTINCT n.node_id, n.node_type, n.label, n.description, n.source_fig "
        "FROM kg.edge e "
        "JOIN kg.node n ON n.node_id = e.subject_id "
        "WHERE e.predicate = 'informs' AND e.object_id = ? "
        "ORDER BY n.node_id",
        (question_id,),
    )


def regions_at_point(
    conn: duckdb.DuckDBPyConnection, lat: float, lon: float, half_box: float = 0.5
) -> list[dict]:
    """Return county.* / tribe.* nodes whose lat/lon properties bracket a point.

    The kg schema doesn't (yet) carry centroid or bbox properties for
    counties or tribes, so this is intentionally permissive: it only
    matches when both ``lat`` and ``lon`` numeric properties exist on
    a county or tribe node and the point is within ``half_box``
    degrees of that centroid. If no such properties are loaded the
    function returns an empty list rather than raising.
    """
    sql = (
        "WITH coords AS ( "
        "  SELECT n.node_id, n.node_type, n.label, n.description, n.source_fig, "
        "         lat.value_num AS centroid_lat, "
        "         lon.value_num AS centroid_lon "
        "  FROM kg.node n "
        "  JOIN kg.property lat ON lat.node_id = n.node_id AND lat.key IN ('lat','latitude','centroid_lat') "
        "  JOIN kg.property lon ON lon.node_id = n.node_id AND lon.key IN ('lon','longitude','centroid_lon') "
        "  WHERE n.node_type IN ('county','tribe','region') "
        ") "
        "SELECT node_id, node_type, label, description, source_fig, centroid_lat, centroid_lon "
        "FROM coords "
        "WHERE abs(centroid_lat - ?) <= ? AND abs(centroid_lon - ?) <= ? "
        "ORDER BY (abs(centroid_lat - ?) + abs(centroid_lon - ?))"
    )
    try:
        return _fetch_dicts(
            conn,
            sql,
            (lat, half_box, lon, half_box, lat, lon),
        )
    except duckdb.Error:
        # Property table or required columns aren't present; return empty.
        return []


# ----------------------------------------------------------------- SQL escape hatch
_SELECT_RE = re.compile(r"^\s*(?:select|with)\b", re.IGNORECASE)
_FORBIDDEN_RE = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|copy|"
    r"truncate|grant|revoke|pragma|export|import|call|use|set|reset|"
    r"vacuum|analyze|begin|commit|rollback|checkpoint|install|load)\b",
    re.IGNORECASE,
)


class UnsafeSQLError(ValueError):
    """Raised when the SQL escape hatch is asked to run a non-SELECT statement."""


def assert_select_only(sql: str) -> str:
    """Reject anything that isn't a single SELECT / WITH statement."""
    stripped = sql.strip().rstrip(";")
    if ";" in stripped:
        raise UnsafeSQLError("Only one SQL statement at a time is permitted.")
    if not _SELECT_RE.match(stripped):
        raise UnsafeSQLError("Only SELECT or WITH ... SELECT statements are permitted.")
    if _FORBIDDEN_RE.search(stripped):
        raise UnsafeSQLError(
            "Query contains a forbidden keyword (mutations + DDL are blocked)."
        )
    return stripped


def run_select(
    conn: duckdb.DuckDBPyConnection,
    sql: str,
    params: list[Any] | None = None,
    row_cap: int = SQL_ROW_CAP,
) -> dict:
    """Execute a SELECT-only query and cap the row count."""
    safe = assert_select_only(sql)
    wrapped = f"SELECT * FROM ({safe}) _kg_inner LIMIT {int(row_cap)}"
    rows = _fetch_dicts(conn, wrapped, tuple(params or ()))
    return {"rows": rows, "row_count": len(rows), "row_cap": row_cap}


# ------------------------------------------------------------------- discovery
def distinct_node_types(conn: duckdb.DuckDBPyConnection) -> list[str]:
    rows = _fetch_dicts(
        conn,
        "SELECT DISTINCT node_type FROM kg.node ORDER BY node_type",
    )
    return [r["node_type"] for r in rows]


def distinct_predicates(conn: duckdb.DuckDBPyConnection) -> list[str]:
    rows = _fetch_dicts(
        conn,
        "SELECT DISTINCT predicate FROM kg.edge ORDER BY predicate",
    )
    return [r["predicate"] for r in rows]
