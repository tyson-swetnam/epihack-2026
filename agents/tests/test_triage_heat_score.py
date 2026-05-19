"""Exercise the heat-vulnerability score from plan/03 Scenario C."""

from __future__ import annotations

from onehealth_agents import (
    AuxiliaryClass,
    Channel,
    ConsentProfile,
    EnvironmentalClass,
    ExposureClass,
    GeneralClass,
    HeatRisk,
    HeatTriage,
    HumanClass,
    Kind,
    MinimumDataset,
    Observation,
    TriageClass,
    Vertical,
)


def _scenario_c_observation() -> Observation:
    """Materialise the worked Scenario C observation from plan/04."""
    return Observation(
        kind=Kind.REPORT,
        vertical=Vertical.HEAT,
        source=Channel.CHW_TABLET,
        consent_profile=ConsentProfile.ANONYMOUS_HEAT,
        dataset=MinimumDataset(
            general=GeneralClass(
                age=45, sex="M", postal_code="85003", lat=33.45, lon=-112.07
            ),
            human=HumanClass(heavy_sweating=True, headache=True),
            exposure=ExposureClass(
                sheltered_status="unsheltered",
                ac_access="no",
                outdoor_time_24h_hours=8.0,
                transport_access="none",
            ),
            auxiliary=AuxiliaryClass(),
            environmental=EnvironmentalClass(
                nws_heatrisk_level=HeatRisk.MAGENTA, ambient_temp_f=115.0
            ),
        ),
    )


def test_scenario_c_score_breakdown():
    heat = HeatTriage()
    obs = _scenario_c_observation()
    score = heat.score(obs)
    factors = {c.factor: c.points for c in score.components}
    # Per plan/03 Scenario C breakdown.
    assert factors["unsheltered"] == 3
    assert factors["outdoor_exposure"] == 2
    assert factors["no_ac"] == 2
    assert factors["magenta_heatrisk"] == 3
    assert factors["symptomatic_heat_exhaustion"] == 2
    assert score.total == 12
    assert score.max_possible == 15


def test_scenario_c_picks_cooling_center():
    decision = HeatTriage().decide(_scenario_c_observation())
    assert decision.vertical == Vertical.HEAT
    assert decision.triage_class == TriageClass.GO_TO_COOLING_CENTER
    assert "dispatch-CHW-transport" in decision.secondary_actions


def test_heat_stroke_triggers_call_911():
    obs = _scenario_c_observation()
    obs.dataset.human.confusion = True
    obs.dataset.human.hot_dry_skin = True
    obs.dataset.human.core_temp_f = 105.4
    decision = HeatTriage().decide(obs)
    assert decision.triage_class == TriageClass.CALL_911


def test_low_risk_check_in():
    obs = Observation(
        vertical=Vertical.HEAT,
        dataset=MinimumDataset(
            general=GeneralClass(age=30),
            environmental=EnvironmentalClass(nws_heatrisk_level=HeatRisk.GREEN),
        ),
    )
    decision = HeatTriage().decide(obs)
    assert decision.triage_class == TriageClass.CHECK_IN_ONLY
    assert decision.heat_vulnerability.total == 0
