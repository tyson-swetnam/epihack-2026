"""End-to-end orchestrator runs for Scenarios A and C from plan/04."""

from __future__ import annotations

import pytest

from onehealth_agents import (
    Channel,
    ConsentProfile,
    FakeMCPClient,
    Kind,
    Orchestrator,
    TriageClass,
    ValidationStatus,
    Vertical,
)


# --------------------------------------------------------------------------
# Scenario A -- Hiker mails in a tick
# --------------------------------------------------------------------------
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


@pytest.mark.asyncio
async def test_scenario_a_tick_mailin():
    fake_mcp = FakeMCPClient.with_default_handlers()
    orch = Orchestrator(mcp=fake_mcp)
    obs = await orch.process(SCENARIO_A_INPUT)

    # Triage -- VBD branch, mail-to-walker-lab.
    assert obs.triage is not None
    assert obs.triage.vertical == Vertical.VBD
    assert obs.triage.triage_class == TriageClass.MAIL_TO_WALKER_LAB
    assert "self-monitor-for-14-days" in obs.triage.secondary_actions

    # Geo enrichment landed Santa Cruz County (canned response).
    assert obs.geo is not None
    assert obs.geo.county_id == "county.santa_cruz"

    # Validation accepted (no flags from the canned input).
    assert obs.validation_status in {
        ValidationStatus.ACCEPT,
        ValidationStatus.FLAG_FOR_REVIEW,
    }

    # Enrichment hydrated the tick-mail-in submission AND queried pools.
    tools_called = {(r.mcp_server, r.tool) for r in obs.enrichments.records}
    assert ("great-az-tick-check-mcp", "gattc_create_submission") in tools_called
    assert ("vectorsurv-mcp", "vectorsurv_get_pools") in tools_called

    # Notification surfaced a user-facing card with a mailing label.
    user_notes = [n for n in obs.notifications if n.audience == "user"]
    assert user_notes, "expected at least one user-facing notification"
    headline = user_notes[0].headline.lower()
    assert "tick" in headline or "mail" in headline

    # Per-agent audit trace populated.
    agents_seen = {run.agent for run in obs.agent_runs}
    assert {"geo_enrichment", "validation", "triage", "enrichment", "notification"} <= agents_seen
    assert all(run.status in {"ok", "degraded"} for run in obs.agent_runs)


# --------------------------------------------------------------------------
# Scenario C -- CHW heat check-in
# --------------------------------------------------------------------------
SCENARIO_C_INPUT = {
    "channel": Channel.CHW_TABLET.value,
    "vertical": Vertical.HEAT.value,
    "kind": Kind.REPORT.value,
    "consent_profile": ConsentProfile.ANONYMOUS_HEAT.value,
    "general": {
        "age": 47,
        "sex": "M",
        "postal_code": "85003",
        "lat": 33.451,
        "lon": -112.073,
        "unique_id": "outreach-c-1",
        # The intake agent should suppress these; we pass them to prove it.
        "email": "x@y.z",
        "occupation": "construction",
    },
    "human": {
        "heavy_sweating": True,
        "headache": True,
    },
    "exposure": {
        "sheltered_status": "unsheltered",
        "ac_access": "no",
        "outdoor_time_24h_hours": 8.0,
        "transport_access": "none",
    },
    "environmental": {
        "nws_heatrisk_level": "Magenta",
        "ambient_temp_f": 115.0,
    },
}


@pytest.mark.asyncio
async def test_scenario_c_heat_checkin():
    fake_mcp = FakeMCPClient.with_default_handlers()
    orch = Orchestrator(mcp=fake_mcp)
    obs = await orch.process(SCENARIO_C_INPUT)

    # Triage -- Heat branch, vulnerability total 12, go-to-cooling-center.
    assert obs.triage is not None
    assert obs.triage.vertical == Vertical.HEAT
    assert obs.triage.triage_class == TriageClass.GO_TO_COOLING_CENTER
    assert obs.triage.heat_vulnerability is not None
    assert obs.triage.heat_vulnerability.total == 12
    assert "dispatch-CHW-transport" in obs.triage.secondary_actions

    # Intake suppression cleared the consent-protected fields.
    assert obs.dataset.general.contact_email is None
    assert obs.dataset.general.occupation is None

    # Geo enrichment landed Maricopa County / Phoenix metro.
    assert obs.geo is not None
    assert obs.geo.county_id == "county.maricopa"
    assert obs.geo.region_id == "region.maricopa_metro"

    # Enrichment hit HeatRisk + cooling-centers + 211 transport dispatch.
    tools_called = {(r.mcp_server, r.tool) for r in obs.enrichments.records}
    assert ("nws-heatrisk-mcp", "nws_heatrisk") in tools_called
    assert ("mag-hrn-mcp", "mag_search_centers") in tools_called
    assert ("211-az-mcp", "az211_transport_to_cooling_center") in tools_called

    # CHW + user notifications present, agency dashboard pin too.
    audiences = {n.audience for n in obs.notifications}
    assert "user" in audiences
    assert "chw" in audiences
    assert "agency_analyst" in audiences

    # Audit trail.
    agents_seen = {run.agent for run in obs.agent_runs}
    assert {"geo_enrichment", "validation", "triage", "enrichment", "notification"} <= agents_seen


@pytest.mark.asyncio
async def test_failing_agent_degrades_gracefully():
    """If an MCP tool blows up, the pipeline still produces an observation."""

    class BrokenClient:
        async def call_tool(self, server, tool, **kwargs):
            raise ConnectionError(f"{server}.{tool} unreachable")

        async def list_tools(self, server):
            return []

    orch = Orchestrator(mcp=BrokenClient())
    obs = await orch.process(SCENARIO_A_INPUT)
    # Triage still ran -- doesn't depend on MCP.
    assert obs.triage is not None
    # Enrichment recorded its failures.
    assert obs.enrichments.failed_tools, "expected failed_tools to be populated"
    # Per-agent trace flags the geo/enrichment hops at minimum.
    assert any(run.agent == "enrichment" for run in obs.agent_runs)
