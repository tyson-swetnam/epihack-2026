"""Round-trip every contract model through JSON."""

from __future__ import annotations

import json

import pytest

from onehealth_agents import contracts as C


def _roundtrip(model):
    payload = model.model_dump_json()
    parsed = json.loads(payload)
    rebuilt = type(model).model_validate(parsed)
    assert rebuilt == model


@pytest.mark.parametrize(
    "model",
    [
        C.GeneralClass(age=38, sex="M", postal_code="85003", lat=33.45, lon=-112.07),
        C.HumanClass(fever=True, headache=True, confusion=True, core_temp_f=104.2),
        C.SeverityClass(bleeding_body_openings=False, yellow_skin_eyes=True),
        C.ExposureClass(
            tick_insect_bite=True,
            attached_duration_hours=6.0,
            bite_location="leg",
            sheltered_status="unsheltered",
            ac_access="no",
        ),
        C.AuxiliaryClass(digital_biomarker={"wearable.skin_temp_c": 38.4}),
        C.EnvironmentalClass(nws_heatrisk_level=C.HeatRisk.MAGENTA, ambient_temp_f=115.0),
        C.LivestockClass(livestock_species="cattle", livestock_sick_count=2),
        C.WildlifeClass(wildlife_species="deer", wildlife_dead_count=1),
        C.MinimumDataset(),
        C.GeoEnrichment(
            county_id="county.santa_cruz",
            region_id="region.border_corridor",
            zcta="85624",
            coord_precision="exact",
        ),
        C.ValidationReport(
            status=C.ValidationStatus.ACCEPT,
            consent_profile=C.ConsentProfile.FULL_FOLLOWUP,
        ),
        C.HeatVulnerabilityScore(
            components=[
                C.HeatVulnerabilityComponent(
                    factor="unsheltered", points=3, population_node="pop.unsheltered"
                )
            ],
            total=3,
            max_possible=15,
        ),
        C.CandidatePathogen(
            pathogen_id="pathogen.rickettsia_rickettsii",
            via_vector_id="vector.rhipicephalus_sanguineus",
            score=1.5,
            rationale="symptom:rash",
        ),
        C.TriageDecision(
            vertical=C.Vertical.VBD,
            triage_class=C.TriageClass.MAIL_TO_WALKER_LAB,
            rationale="tick mail-in flow",
        ),
        C.EnrichmentRecord(
            mcp_server="vectorsurv-mcp",
            tool="get_pools",
            payload={"pools": [], "count": 0},
        ),
        C.EnrichmentBundle(),
        C.Notification(
            audience="user",
            channel="app_push",
            headline="hello",
            body="world",
        ),
        C.ClusterAlert(
            vertical=C.Vertical.VBD,
            observation_ids=["observation.abc"],
            window_start="2026-05-09T00:00:00+00:00",
            window_end="2026-05-19T00:00:00+00:00",
            expected=0.5,
            observed=4,
            log_likelihood=3.2,
        ),
        C.AgentRun(
            agent="triage",
            started_at="2026-05-19T00:00:00+00:00",
            finished_at="2026-05-19T00:00:00+00:00",
            duration_ms=12.3,
            status="ok",
        ),
        C.Observation(),
    ],
)
def test_roundtrip(model):
    _roundtrip(model)


def test_triage_class_enum_covers_seed():
    # Every tc.* seeded in schema/deep/application.sql must be a member.
    expected = {
        "tc.self_care",
        "tc.see_clinician",
        "tc.urgent_care",
        "tc.call_911",
        "tc.report_to_azgfd",
        "tc.mail_to_walker_lab",
        "tc.go_to_cooling_center",
        "tc.dispatch_chw",
        "tc.check_in_only",
        "tc.drink_water_advisory",
    }
    assert {tc.value for tc in C.TriageClass} == expected


def test_observation_carries_agent_runs():
    obs = C.Observation()
    obs.agent_runs.append(
        C.AgentRun(
            agent="intake",
            started_at="2026-05-19T00:00:00+00:00",
            finished_at="2026-05-19T00:00:00.001+00:00",
            duration_ms=1.0,
            status="ok",
        )
    )
    rebuilt = C.Observation.model_validate_json(obs.model_dump_json())
    assert rebuilt.agent_runs[0].agent == "intake"
