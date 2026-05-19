"""Tests for the agent-runtime audit sink (``onehealth_agents.audit``).

Covers:

* :class:`InMemoryAuditSink` -- the default sink the orchestrator uses
  when no audit_sink is wired. We round-trip Scenario A and assert that
  every agent step landed in the sink with the right fields populated.
* :class:`DuckLakeAuditSink` -- the production sink. Boots an in-memory
  DuckDB, loads ``schema/knowledge_graph.sql`` + ``schema/deep/audit.sql``,
  runs Scenario A through the orchestrator with the sink attached, then
  asserts the ``kg.agent_run`` table + ``kg.v_observation_timeliness``
  view both return the expected shape.
* :func:`hash_for_audit` -- stable across object orderings.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from onehealth_agents import (
    Channel,
    ConsentProfile,
    DuckLakeAuditSink,
    FakeMCPClient,
    InMemoryAuditSink,
    Kind,
    Orchestrator,
    Vertical,
    hash_for_audit,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_KG = REPO_ROOT / "schema" / "knowledge_graph.sql"
SCHEMA_AUDIT = REPO_ROOT / "schema" / "deep" / "audit.sql"


SCENARIO_A_INPUT = {
    "channel": Channel.MOBILE.value,
    "vertical": Vertical.VBD.value,
    "kind": Kind.REPORT.value,
    "consent_profile": ConsentProfile.TICK_MAILIN.value,
    "general": {
        "age": 38,
        "sex": "M",
        "postal_code": "85624",
        "lat": 31.541,
        "lon": -110.755,
        "unique_id": "hiker-001",
    },
    "exposure": {
        "tick_insect_bite": True,
        "attached_duration_hours": 6.0,
        "bite_location": "leg",
    },
    "auxiliary": {
        "photo_url": "https://example.com/tick.jpg",
        "photo_quality_score": 0.85,
    },
}


EXPECTED_AGENTS = {
    "intake",
    "geo_enrichment",
    "validation",
    "triage",
    "enrichment",
    "notification",
}


# --------------------------------------------------------------------------
# hash_for_audit
# --------------------------------------------------------------------------
def test_hash_for_audit_is_stable_across_key_order():
    a = {"alpha": 1, "beta": 2, "nested": {"x": [1, 2, 3], "y": "z"}}
    b = {"nested": {"y": "z", "x": [1, 2, 3]}, "beta": 2, "alpha": 1}
    assert hash_for_audit(a) == hash_for_audit(b)


def test_hash_for_audit_changes_with_payload():
    a = {"foo": 1}
    b = {"foo": 2}
    assert hash_for_audit(a) != hash_for_audit(b)


# --------------------------------------------------------------------------
# InMemoryAuditSink
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_in_memory_sink_collects_every_step():
    sink = InMemoryAuditSink()
    orch = Orchestrator(mcp=FakeMCPClient.with_default_handlers(), audit_sink=sink)
    obs = await orch.process(SCENARIO_A_INPUT)

    # Every expected agent appears at least once in the sink.
    seen = {run.agent for run in sink}
    assert EXPECTED_AGENTS <= seen

    # Every run carries the observation_id, digests, and a model_id.
    for run in sink:
        assert run.observation_id == obs.observation_id
        assert run.input_digest, f"missing input_digest for {run.agent}"
        if run.status == "ok":
            assert run.output_digest, f"missing output_digest for {run.agent}"
        assert run.model, f"missing model_id for {run.agent}"
        assert run.duration_ms >= 0
        # Cost defaults to zero when no token counts are reported (the path
        # the deterministic stub agents take). The point is just that it is
        # always computed, never None.
        assert run.cost_usd == 0.0


@pytest.mark.asyncio
async def test_default_sink_is_in_memory():
    orch = Orchestrator(mcp=FakeMCPClient.with_default_handlers())
    assert isinstance(orch.audit_sink, InMemoryAuditSink)
    obs = await orch.process(SCENARIO_A_INPUT)
    assert len(orch.audit_sink) >= len(EXPECTED_AGENTS)
    # And the observation still carries the run trace -- the sink does not
    # replace the in-observation field.
    assert {r.agent for r in obs.agent_runs} >= EXPECTED_AGENTS


# --------------------------------------------------------------------------
# DuckLakeAuditSink (in-memory DuckDB)
# --------------------------------------------------------------------------
def _load_schemas(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(SCHEMA_KG.read_text())
    con.execute(SCHEMA_AUDIT.read_text())


@pytest.mark.asyncio
async def test_ducklake_sink_writes_rows_and_powers_timeliness_view():
    con = duckdb.connect(":memory:")
    _load_schemas(con)

    sink = DuckLakeAuditSink(connection=con)
    orch = Orchestrator(mcp=FakeMCPClient.with_default_handlers(), audit_sink=sink)
    obs = await orch.process(SCENARIO_A_INPUT)

    # 1. Every expected agent has at least one row.
    rows = con.execute(
        "SELECT agent_name, observation_id, outcome, model_id, input_digest, "
        "       output_digest, source_fig "
        "FROM kg.agent_run "
        "ORDER BY started_at"
    ).fetchall()
    seen_agents = {row[0] for row in rows}
    assert EXPECTED_AGENTS <= seen_agents

    # 2. All rows reference the same observation_id and stamp source_fig.
    assert {row[1] for row in rows} == {obs.observation_id}
    assert {row[6] for row in rows} == {"agent-runtime"}

    # 3. Outcome enum maps the pydantic 'ok' status to SQL 'success'.
    assert {row[2] for row in rows} <= {"success", "degraded", "error"}
    assert "success" in {row[2] for row in rows}

    # 4. Digests are populated.
    assert all(row[4] for row in rows), "every row should have an input_digest"

    # 5. Timeliness view returns exactly one row per observation.
    view_rows = con.execute(
        "SELECT observation_id, detect_at, notify_at, verify_at_provisional, "
        "       lab_at_provisional, respond_at, detect_to_respond_min "
        "FROM kg.v_observation_timeliness"
    ).fetchall()
    assert len(view_rows) == 1
    (
        obs_id,
        detect_at,
        notify_at,
        verify_at,
        lab_at,
        respond_at,
        detect_to_respond_min,
    ) = view_rows[0]
    assert obs_id == obs.observation_id
    # All five milestones fired for Scenario A.
    assert detect_at is not None
    assert notify_at is not None
    assert verify_at is not None
    assert lab_at is not None
    assert respond_at is not None
    # Detect happens before (or at the same moment as) Respond.
    assert detect_to_respond_min is not None
    assert detect_to_respond_min >= 0


@pytest.mark.asyncio
async def test_ducklake_sink_idempotent_on_duplicate_run_id():
    con = duckdb.connect(":memory:")
    _load_schemas(con)

    sink = DuckLakeAuditSink(connection=con)
    orch = Orchestrator(mcp=FakeMCPClient.with_default_handlers(), audit_sink=sink)
    obs = await orch.process(SCENARIO_A_INPUT)

    before = con.execute("SELECT COUNT(*) FROM kg.agent_run").fetchone()[0]
    # Re-insert each run -- ON CONFLICT DO NOTHING should keep the count flat.
    for run in obs.agent_runs:
        sink.record(run)
    after = con.execute("SELECT COUNT(*) FROM kg.agent_run").fetchone()[0]
    assert before == after


@pytest.mark.asyncio
async def test_ducklake_sink_records_per_day_cost_rollup():
    con = duckdb.connect(":memory:")
    _load_schemas(con)
    sink = DuckLakeAuditSink(connection=con)
    orch = Orchestrator(mcp=FakeMCPClient.with_default_handlers(), audit_sink=sink)
    await orch.process(SCENARIO_A_INPUT)

    rollup_rows = con.execute(
        "SELECT agent_name, run_count, cost_usd_total FROM kg.v_agent_run_cost"
    ).fetchall()
    rollup = {row[0]: (row[1], row[2]) for row in rollup_rows}
    assert EXPECTED_AGENTS <= set(rollup.keys())
    # Cost rolls up to zero with the stub agents (no token counts reported);
    # the point is that the view is queryable end-to-end.
    for _agent, (count, cost) in rollup.items():
        assert count >= 1
        assert cost == 0.0


@pytest.mark.asyncio
async def test_failures_view_lists_only_non_success_rows():
    con = duckdb.connect(":memory:")
    _load_schemas(con)
    sink = DuckLakeAuditSink(connection=con)

    class BrokenClient:
        async def call_tool(self, server, tool, **kwargs):
            raise ConnectionError(f"{server}.{tool} unreachable")

        async def list_tools(self, server):
            return []

    orch = Orchestrator(mcp=BrokenClient(), audit_sink=sink)
    await orch.process(SCENARIO_A_INPUT)

    rows = con.execute(
        "SELECT agent_name, outcome FROM kg.v_agent_run_failures"
    ).fetchall()
    # Geo enrichment + enrichment both depend on MCP and should surface.
    failed_agents = {row[0] for row in rows}
    # At least one of the MCP-dependent agents shows up.
    assert failed_agents, "expected at least one non-success row in the failures view"
    # No row in the failures view is marked 'success'.
    assert all(row[1] != "success" for row in rows)
