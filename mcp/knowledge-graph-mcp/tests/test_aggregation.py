"""Tests for the aggregation tools (extending knowledge-graph-mcp).

Each test seeds a minimal synthetic graph that exercises the surface
area of the four aggregation queries without standing up the full kg
schema.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import duckdb
import pytest

from knowledge_graph_mcp import aggregation, cluster_scan


# ---------------------------------------------------------------------------
# Shared fixture: a tiny kg with observation nodes, county / pathogen edges,
# triage edges, and an agent_run audit table seeded for the timeliness pivot.
# ---------------------------------------------------------------------------
@pytest.fixture()
def kg_conn() -> duckdb.DuckDBPyConnection:
    c = duckdb.connect(":memory:")
    c.execute("CREATE SCHEMA kg;")
    c.execute(
        "CREATE TABLE kg.node ("
        "  node_id VARCHAR PRIMARY KEY,"
        "  node_type VARCHAR NOT NULL,"
        "  label VARCHAR NOT NULL,"
        "  description VARCHAR,"
        "  source_fig VARCHAR,"
        "  created_at TIMESTAMP DEFAULT current_timestamp"
        ");"
    )
    c.execute(
        "CREATE TABLE kg.edge ("
        "  edge_id BIGINT PRIMARY KEY,"
        "  subject_id VARCHAR NOT NULL,"
        "  predicate VARCHAR NOT NULL,"
        "  object_id VARCHAR NOT NULL,"
        "  source_fig VARCHAR"
        ");"
    )
    c.execute(
        "CREATE TABLE kg.property ("
        "  node_id VARCHAR NOT NULL,"
        "  key VARCHAR NOT NULL,"
        "  value_text VARCHAR,"
        "  value_num DOUBLE,"
        "  PRIMARY KEY (node_id, key)"
        ");"
    )

    # Anchor nodes: county, pathogen, triage classes.
    c.executemany(
        "INSERT INTO kg.node VALUES (?, ?, ?, ?, ?, current_timestamp)",
        [
            ("county.maricopa", "county", "Maricopa County", None, "test"),
            ("county.coconino", "county", "Coconino County", None, "test"),
            ("pathogen.wnv", "pathogen", "West Nile virus", None, "test"),
            ("pathogen.yersinia_pestis", "pathogen", "Yersinia pestis", None, "test"),
            ("tc.self_care", "triage_class", "Self-care", None, "test"),
            ("tc.urgent_care", "triage_class", "Urgent care", None, "test"),
            ("tc.call_911", "triage_class", "Call 911", None, "test"),
        ],
    )

    c.executemany(
        "INSERT INTO kg.property VALUES (?, ?, ?, ?)",
        [
            ("tc.self_care", "severity", "low", None),
            ("tc.urgent_care", "severity", "high", None),
            ("tc.call_911", "severity", "critical", None),
        ],
    )

    # Two observations in 2024-W30 + one in 2024-W31, both Maricopa.
    obs_specs = [
        ("observation.a", "2024-07-22T10:00:00+00:00", "vbd", "county.maricopa",
         "pathogen.wnv", "tc.self_care"),
        ("observation.b", "2024-07-23T11:00:00+00:00", "vbd", "county.maricopa",
         "pathogen.wnv", "tc.urgent_care"),
        ("observation.c", "2024-07-29T12:00:00+00:00", "vbd", "county.maricopa",
         "pathogen.wnv", "tc.call_911"),
        # A Coconino plague observation in 2024-W30.
        ("observation.d", "2024-07-25T08:00:00+00:00", "vbd", "county.coconino",
         "pathogen.yersinia_pestis", "tc.urgent_care"),
        # A heat observation with no county/pathogen.
        ("observation.e", "2024-07-22T15:00:00+00:00", "heat", None, None, None),
    ]
    next_edge_id = 1
    for nid, ts, vert, cid, pid, tc in obs_specs:
        c.execute(
            "INSERT INTO kg.node VALUES (?, 'observation', ?, NULL, 'test', current_timestamp)",
            (nid, nid),
        )
        c.execute(
            "INSERT INTO kg.property VALUES (?, 'reported_at', ?, NULL)",
            (nid, ts),
        )
        c.execute(
            "INSERT INTO kg.property VALUES (?, 'vertical', ?, NULL)",
            (nid, vert),
        )
        if cid:
            c.execute(
                "INSERT INTO kg.edge VALUES (?, ?, 'colocatedWith', ?, 'test')",
                (next_edge_id, nid, cid),
            )
            next_edge_id += 1
        if pid:
            c.execute(
                "INSERT INTO kg.edge VALUES (?, ?, 'reportsAbout', ?, 'test')",
                (next_edge_id, nid, pid),
            )
            next_edge_id += 1
        if tc:
            c.execute(
                "INSERT INTO kg.edge VALUES (?, ?, 'gradedAs', ?, 'test')",
                (next_edge_id, nid, tc),
            )
            next_edge_id += 1

    # Seed the audit table + the two views we need.
    c.execute(
        "CREATE TABLE kg.agent_run ("
        "  run_id VARCHAR PRIMARY KEY,"
        "  agent_name VARCHAR NOT NULL,"
        "  observation_id VARCHAR,"
        "  started_at TIMESTAMP NOT NULL,"
        "  ended_at TIMESTAMP,"
        "  duration_ms DOUBLE,"
        "  model_id VARCHAR,"
        "  prompt_tokens INTEGER,"
        "  completion_tokens INTEGER,"
        "  cache_read_tokens INTEGER,"
        "  cache_creation_tokens INTEGER,"
        "  cost_usd DOUBLE,"
        "  outcome VARCHAR,"
        "  input_digest VARCHAR,"
        "  output_digest VARCHAR,"
        "  error_message VARCHAR,"
        "  source_fig VARCHAR DEFAULT 'agent-runtime'"
        ");"
    )
    # Observation A: full Detect -> Respond chain.
    base = datetime(2024, 7, 22, 10, 0, tzinfo=timezone.utc)
    chain = [
        ("intake", base),
        ("validation", base + timedelta(minutes=3)),
        ("triage", base + timedelta(minutes=12)),
        ("enrichment", base + timedelta(minutes=45)),
        ("notification", base + timedelta(minutes=60)),
    ]
    for agent, ts in chain:
        c.execute(
            "INSERT INTO kg.agent_run VALUES "
            "(?, ?, ?, ?, ?, 200.0, 'claude-haiku-4-5', 100, 50, 0, 0, 0.01, "
            "'success', NULL, NULL, NULL, 'test')",
            (str(uuid4()), agent, "observation.a", ts, ts + timedelta(seconds=2)),
        )

    # Observation B: only intake fired.
    c.execute(
        "INSERT INTO kg.agent_run VALUES "
        "(?, 'intake', 'observation.b', ?, ?, 150.0, 'claude-haiku-4-5', 80, 30, 0, 0, "
        "0.005, 'success', NULL, NULL, NULL, 'test')",
        (str(uuid4()), base + timedelta(hours=1), base + timedelta(hours=1, seconds=1)),
    )

    c.execute(
        """
        CREATE OR REPLACE VIEW kg.v_observation_timeliness AS
        WITH per_obs AS (
            SELECT
                observation_id,
                MIN(CASE WHEN agent_name = 'intake'       THEN started_at END) AS detect_at,
                MIN(CASE WHEN agent_name = 'validation'   THEN started_at END) AS notify_at,
                MIN(CASE WHEN agent_name = 'triage'       THEN started_at END) AS verify_at_provisional,
                MIN(CASE WHEN agent_name = 'enrichment'   THEN started_at END) AS lab_at_provisional,
                MIN(CASE WHEN agent_name = 'notification' THEN started_at END) AS respond_at
            FROM kg.agent_run
            WHERE observation_id IS NOT NULL
            GROUP BY observation_id
        )
        SELECT
            observation_id,
            detect_at, notify_at, verify_at_provisional, lab_at_provisional, respond_at,
            date_diff('minute', detect_at,             notify_at)             AS detect_to_notify_min,
            date_diff('minute', notify_at,             verify_at_provisional) AS notify_to_verify_min,
            date_diff('minute', verify_at_provisional, lab_at_provisional)    AS verify_to_lab_min,
            date_diff('minute', lab_at_provisional,    respond_at)            AS lab_to_respond_min,
            date_diff('minute', detect_at,             respond_at)            AS detect_to_respond_min
        FROM per_obs
        """
    )

    c.execute(
        """
        CREATE OR REPLACE VIEW kg.v_agent_run_cost AS
        SELECT
            CAST(started_at AS DATE)               AS day,
            agent_name,
            COUNT(*)                               AS run_count,
            COALESCE(SUM(prompt_tokens), 0)       AS prompt_tokens_total,
            COALESCE(SUM(completion_tokens), 0)   AS completion_tokens_total,
            COALESCE(SUM(cache_read_tokens), 0)   AS cache_read_tokens_total,
            COALESCE(SUM(cache_creation_tokens),0)AS cache_creation_tokens_total,
            COALESCE(SUM(cost_usd), 0.0)          AS cost_usd_total
        FROM kg.agent_run
        GROUP BY day, agent_name
        """
    )
    return c


# ---------------------------------------------------------------------------
# kg_observations_by_window
# ---------------------------------------------------------------------------
def test_observations_by_window_buckets_by_iso_week(kg_conn):
    rows = aggregation.observations_by_window(
        kg_conn, start_date="2024-07-01", end_date="2024-08-31"
    )
    # We expect three buckets:
    #   (2024-W30, county.maricopa, pathogen.wnv) -> 2 observations
    #   (2024-W30, county.coconino, pathogen.yersinia_pestis) -> 1 observation
    #   (2024-W31, county.maricopa, pathogen.wnv) -> 1 observation
    #   (2024-W30, None, None) -> 1 heat observation (no edges)
    key_to_count = {
        (r["iso_week"], r["county_id"], r["pathogen_id"]): r["observation_count"]
        for r in rows
    }
    assert key_to_count[("2024-W30", "county.maricopa", "pathogen.wnv")] == 2
    assert key_to_count[("2024-W30", "county.coconino", "pathogen.yersinia_pestis")] == 1
    assert key_to_count[("2024-W31", "county.maricopa", "pathogen.wnv")] == 1
    assert key_to_count[("2024-W30", None, None)] == 1


def test_observations_by_window_severity_max_and_breakdown(kg_conn):
    rows = aggregation.observations_by_window(
        kg_conn,
        start_date="2024-07-01",
        end_date="2024-07-28",  # captures W30 only
        county_id="county.maricopa",
        pathogen_id="pathogen.wnv",
    )
    assert len(rows) == 1
    cell = rows[0]
    assert cell["iso_week"] == "2024-W30"
    # observation.a -> tc.self_care (low); observation.b -> tc.urgent_care (high)
    assert cell["severity_max"] == "high"
    assert cell["triage_class_breakdown"] == {"tc.self_care": 1, "tc.urgent_care": 1}


def test_observations_by_window_vertical_filter(kg_conn):
    rows = aggregation.observations_by_window(
        kg_conn, start_date="2024-07-01", end_date="2024-08-31", vertical="heat"
    )
    # Only the lone heat observation comes back.
    assert len(rows) == 1
    assert rows[0]["county_id"] is None
    assert rows[0]["pathogen_id"] is None
    assert rows[0]["observation_count"] == 1


# ---------------------------------------------------------------------------
# kg_milestone_intervals
# ---------------------------------------------------------------------------
def test_milestone_intervals_full_chain(kg_conn):
    rows = aggregation.milestone_intervals(
        kg_conn, start_date="2024-07-01", end_date="2024-08-31"
    )
    # observation.a has the full chain; observation.b only intake.
    by_obs = {r["observation_id"]: r for r in rows}
    assert "observation.a" in by_obs
    a = by_obs["observation.a"]
    assert a["detect_to_notify_min"] == 3
    assert a["notify_to_verify_min"] == 9
    assert a["verify_to_lab_min"] == 33
    assert a["lab_to_respond_min"] == 15
    # Five runs x 0.01 USD = 0.05 USD total.
    assert a["cost_usd_total"] == pytest.approx(0.05)
    assert a["run_count"] == 5
    # Notify_at populated.
    assert a["notify_at"] is not None

    # observation.b has only intake -> partial row.
    b = by_obs["observation.b"]
    assert b["detect_to_notify_min"] is None
    assert b["respond_at"] is None
    assert b["run_count"] == 1


def test_milestone_intervals_date_filter(kg_conn):
    # End-of-day boundary on the detect_at side.
    rows = aggregation.milestone_intervals(
        kg_conn, start_date="2024-07-22", end_date="2024-07-22"
    )
    obs_ids = {r["observation_id"] for r in rows}
    # observation.a starts at 10:00 on 22 Jul; observation.b at 11:00.
    assert obs_ids == {"observation.a", "observation.b"}


# ---------------------------------------------------------------------------
# kg_cluster_scan
# ---------------------------------------------------------------------------
def test_cluster_scan_emits_alert_for_synthetic_burst(kg_conn):
    # Seed a synthetic burst: 10 VBD observations in ZCTA 85003 within the
    # last 14 days, vs near-zero baseline elsewhere. The detector should
    # trip on (vbd, 85003, current ISO week).
    now = datetime(2024, 8, 5, 12, 0, tzinfo=timezone.utc)
    burst_ts = now - timedelta(days=2)
    # Add a baseline of 8 other ZCTAs each with 1 observation in the
    # baseline window (35-7 days back) so the state-level denominator
    # exists but is low.
    edge_id = 9000
    for i, zcta in enumerate(["85009", "85033", "85040", "85201", "85301",
                              "85701", "85718", "85364"]):
        nid = f"observation.bg{i}"
        ts = (now - timedelta(days=35 + i)).isoformat()
        kg_conn.execute(
            "INSERT INTO kg.node VALUES (?, 'observation', ?, NULL, 'test', current_timestamp)",
            (nid, nid),
        )
        kg_conn.execute(
            "INSERT INTO kg.property VALUES (?, 'reported_at', ?, NULL)", (nid, ts)
        )
        kg_conn.execute(
            "INSERT INTO kg.property VALUES (?, 'vertical', 'vbd', NULL)", (nid,)
        )
        kg_conn.execute(
            "INSERT INTO kg.property VALUES (?, 'postal_code', ?, NULL)", (nid, zcta)
        )
    # The burst itself.
    for i in range(10):
        nid = f"observation.burst{i}"
        ts = (burst_ts + timedelta(minutes=i * 5)).isoformat()
        kg_conn.execute(
            "INSERT INTO kg.node VALUES (?, 'observation', ?, NULL, 'test', current_timestamp)",
            (nid, nid),
        )
        kg_conn.execute(
            "INSERT INTO kg.property VALUES (?, 'reported_at', ?, NULL)", (nid, ts)
        )
        kg_conn.execute(
            "INSERT INTO kg.property VALUES (?, 'vertical', 'vbd', NULL)", (nid,)
        )
        kg_conn.execute(
            "INSERT INTO kg.property VALUES (?, 'postal_code', '85003', NULL)", (nid,)
        )
        kg_conn.execute(
            "INSERT INTO kg.edge VALUES (?, ?, 'reportsAbout', 'pathogen.wnv', 'test')",
            (edge_id, nid),
        )
        edge_id += 1

    rows = cluster_scan.cluster_scan(
        kg_conn, vertical="vbd", lookback_days=60, now=now
    )
    # We should see at least one alert pointing at ZCTA 85003.
    zctas = {r["zcta"] for r in rows}
    assert "85003" in zctas
    alert = next(r for r in rows if r["zcta"] == "85003")
    assert alert["observed"] >= 5
    assert alert["tier2_posterior"] is not None
    assert alert["alert_status"] == "alert"
    assert alert["pathogen_hint"] == "pathogen.wnv"


def test_cluster_scan_quiet_kg_no_tier1_alerts(kg_conn):
    # The base fixture has only 4 VBD observations; far below the Tier-1
    # k=5 threshold per (zcta, week). The single Y. pestis observation
    # SHOULD trip the detector's single-case high-CFR rule (plague is
    # always alertable) -- so we assert that only the single-case path
    # fired, with no Tier-1 / Tier-2 metrics populated.
    rows = cluster_scan.cluster_scan(
        kg_conn,
        vertical="vbd",
        lookback_days=14,
        now=datetime(2024, 7, 30, 12, 0, tzinfo=timezone.utc),
    )
    for r in rows:
        assert r["tier1_score"] is None
        assert r["tier2_posterior"] is None
