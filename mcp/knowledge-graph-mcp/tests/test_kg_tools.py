"""Synthetic-data tests for the knowledge-graph MCP query layer.

These tests exercise the pure-SQL ``queries`` module against a minimal
in-memory DuckDB seeded with a handful of nodes/edges/properties. They
do not start the MCP server itself -- the FastMCP layer is a thin
wrapper, so testing the query helpers in isolation is the right unit
boundary.
"""

from __future__ import annotations

import duckdb
import pytest

from knowledge_graph_mcp import queries


@pytest.fixture()
def conn() -> duckdb.DuckDBPyConnection:
    c = duckdb.connect(":memory:")
    c.execute("CREATE SCHEMA kg;")
    c.execute(
        "CREATE TABLE kg.node ("
        "  node_id VARCHAR PRIMARY KEY,"
        "  node_type VARCHAR NOT NULL,"
        "  label VARCHAR NOT NULL,"
        "  description VARCHAR,"
        "  source_fig VARCHAR);"
    )
    c.execute(
        "CREATE TABLE kg.edge ("
        "  edge_id BIGINT PRIMARY KEY,"
        "  subject_id VARCHAR NOT NULL,"
        "  predicate VARCHAR NOT NULL,"
        "  object_id VARCHAR NOT NULL,"
        "  source_fig VARCHAR);"
    )
    c.execute(
        "CREATE TABLE kg.property ("
        "  node_id VARCHAR NOT NULL,"
        "  key VARCHAR NOT NULL,"
        "  value_text VARCHAR,"
        "  value_num DOUBLE,"
        "  PRIMARY KEY (node_id, key));"
    )

    # Five nodes: a county, a pathogen, a vector, an outbreak, a question + resource.
    c.executemany(
        "INSERT INTO kg.node VALUES (?, ?, ?, ?, ?)",
        [
            ("county.maricopa", "county", "Maricopa County", "Phoenix metro.", "test"),
            ("pathogen.wnv", "pathogen", "West Nile virus", "Flavivirus.", "test"),
            ("vector.cx_tarsalis", "vector", "Culex tarsalis", "WNV vector.", "test"),
            ("outbreak.maricopa_wnv_2021", "outbreak", "Maricopa WNV 2021", None, "test"),
            ("wv.q2", "group_question", "WV Q2 zoonotic", None, "test"),
            ("resource.mcdph_mcesd", "resource", "MCDPH / MCESD", None, "test"),
        ],
    )

    c.executemany(
        "INSERT INTO kg.edge VALUES (?, ?, ?, ?, ?)",
        [
            (1, "pathogen.wnv", "transmittedBy", "vector.cx_tarsalis", "test"),
            (2, "outbreak.maricopa_wnv_2021", "causedBy", "pathogen.wnv", "test"),
            (3, "outbreak.maricopa_wnv_2021", "occurredIn", "county.maricopa", "test"),
            (4, "county.maricopa", "hasResource", "resource.mcdph_mcesd", "test"),
            (5, "resource.mcdph_mcesd", "informs", "wv.q2", "test"),
        ],
    )

    c.executemany(
        "INSERT INTO kg.property VALUES (?, ?, ?, ?)",
        [
            ("county.maricopa", "population_approx", None, 4585000.0),
            ("county.maricopa", "fips", "04013", None),
            ("county.maricopa", "lat", None, 33.45),
            ("county.maricopa", "lon", None, -112.07),
            ("pathogen.wnv", "icd10", "A92.3", None),
        ],
    )
    return c


def test_node_lookup_returns_properties(conn):
    node = queries.node_lookup(conn, "county.maricopa")
    assert node["label"] == "Maricopa County"
    assert node["properties"]["fips"] == "04013"
    assert node["properties"]["population_approx"] == 4585000.0


def test_node_lookup_missing_returns_none(conn):
    assert queries.node_lookup(conn, "no.such.node") is None


def test_neighborhood_depth_one(conn):
    nb = queries.neighborhood(conn, "county.maricopa", depth=1)
    ids = {n["node_id"] for n in nb["nodes"]}
    # Directly connected: outbreak (occurredIn), resource (hasResource), plus root.
    assert "county.maricopa" in ids
    assert "outbreak.maricopa_wnv_2021" in ids
    assert "resource.mcdph_mcesd" in ids
    # The pathogen is two hops away and should not appear at depth=1.
    assert "pathogen.wnv" not in ids


def test_neighborhood_predicate_filter(conn):
    nb = queries.neighborhood(conn, "county.maricopa", depth=1, predicate="hasResource")
    edges = nb["edges"]
    assert len(edges) == 1
    assert edges[0]["predicate"] == "hasResource"


def test_neighborhood_depth_two_pulls_pathogen(conn):
    nb = queries.neighborhood(conn, "county.maricopa", depth=2)
    ids = {n["node_id"] for n in nb["nodes"]}
    assert "pathogen.wnv" in ids


def test_neighborhood_caps_depth(conn):
    # depth > MAX_DEPTH is silently clamped; should not raise.
    nb = queries.neighborhood(conn, "county.maricopa", depth=99)
    assert nb["depth"] == queries.MAX_DEPTH


def test_shortest_path_finds_county_to_vector(conn):
    p = queries.shortest_path(conn, "county.maricopa", "vector.cx_tarsalis", max_depth=4)
    assert p["found"]
    ids = [n["node_id"] for n in p["nodes"]]
    assert ids[0] == "county.maricopa"
    assert ids[-1] == "vector.cx_tarsalis"
    # Length is the number of edges, not nodes.
    assert p["length"] == len(p["edges"]) == len(ids) - 1


def test_shortest_path_returns_empty_when_no_path(conn):
    # Add an isolated island node.
    conn.execute(
        "INSERT INTO kg.node VALUES ('island.lonely', 'misc', 'Lonely', NULL, 'test')"
    )
    p = queries.shortest_path(conn, "county.maricopa", "island.lonely", max_depth=4)
    assert not p["found"]
    assert p["nodes"] == [] and p["edges"] == []


def test_shortest_path_self_loop(conn):
    p = queries.shortest_path(conn, "pathogen.wnv", "pathogen.wnv", max_depth=4)
    assert p["found"]
    assert p["length"] == 0
    assert len(p["nodes"]) == 1
    assert p["nodes"][0]["node_id"] == "pathogen.wnv"


def test_pathogens_by_vector(conn):
    rows = queries.pathogens_by_vector(conn, "vector.cx_tarsalis")
    assert [r["node_id"] for r in rows] == ["pathogen.wnv"]


def test_outbreak_check_with_and_without_county(conn):
    all_rows = queries.outbreak_check(conn, "pathogen.wnv")
    assert any(r["node_id"] == "outbreak.maricopa_wnv_2021" for r in all_rows)

    filtered = queries.outbreak_check(
        conn, "pathogen.wnv", county_id="county.maricopa"
    )
    assert {r["node_id"] for r in filtered} == {"outbreak.maricopa_wnv_2021"}

    none = queries.outbreak_check(conn, "pathogen.wnv", county_id="county.pima")
    assert none == []


def test_resource_lookup(conn):
    rows = queries.resources_for_question(conn, "wv.q2")
    assert [r["node_id"] for r in rows] == ["resource.mcdph_mcesd"]


def test_regions_at_point_uses_lat_lon_properties(conn):
    rows = queries.regions_at_point(conn, lat=33.5, lon=-112.0, half_box=0.5)
    assert any(r["node_id"] == "county.maricopa" for r in rows)


def test_regions_at_point_returns_empty_when_far(conn):
    rows = queries.regions_at_point(conn, lat=10.0, lon=10.0, half_box=0.5)
    assert rows == []


# ------------------------------------------------------ SQL escape-hatch tests
def test_run_select_basic(conn):
    out = queries.run_select(
        conn, "SELECT node_id FROM kg.node WHERE node_type = ?", ["pathogen"]
    )
    assert out["row_count"] == 1
    assert out["rows"][0]["node_id"] == "pathogen.wnv"


def test_run_select_supports_with(conn):
    out = queries.run_select(
        conn,
        "WITH cnt AS (SELECT node_type, COUNT(*) AS n FROM kg.node GROUP BY 1) "
        "SELECT * FROM cnt ORDER BY node_type",
    )
    assert out["row_count"] >= 1


def test_run_select_rejects_insert(conn):
    with pytest.raises(queries.UnsafeSQLError):
        queries.run_select(
            conn, "INSERT INTO kg.node VALUES ('x','x','x',NULL,NULL)"
        )


def test_run_select_rejects_update(conn):
    with pytest.raises(queries.UnsafeSQLError):
        queries.run_select(conn, "UPDATE kg.node SET label = 'x'")


def test_run_select_rejects_drop(conn):
    with pytest.raises(queries.UnsafeSQLError):
        queries.run_select(conn, "DROP TABLE kg.node")


def test_run_select_rejects_multistatement(conn):
    with pytest.raises(queries.UnsafeSQLError):
        queries.run_select(
            conn, "SELECT 1; DROP TABLE kg.node"
        )


def test_run_select_rejects_attach(conn):
    with pytest.raises(queries.UnsafeSQLError):
        queries.run_select(conn, "ATTACH 'foo.db' AS foo")


def test_run_select_caps_results(conn):
    # 10 rows, cap at 3.
    conn.execute("CREATE TABLE big AS SELECT range AS i FROM range(10)")
    out = queries.run_select(conn, "SELECT i FROM big ORDER BY i", row_cap=3)
    assert out["row_count"] == 3
