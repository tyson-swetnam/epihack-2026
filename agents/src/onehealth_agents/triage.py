"""TriageAgent -- vertical-specific rule + LLM judgement.

The agent branches on ``Observation.vertical``:

* :class:`HeatTriage` computes the heat-vulnerability score per
  ``plan/03-agentic-architecture.md`` (line items shown in the
  Scenario C walkthrough: unsheltered +3, outdoor exposure +2,
  no AC +2, Magenta HeatRisk +3, symptomatic heat exhaustion +2 =
  12 of a max 15).
* :class:`VBDTriage` enumerates candidate pathogens from the
  ``transmittedBy`` / ``causes`` edges seeded in
  ``schema/deep/pathogens.sql``.

Both branches emit a :class:`TriageDecision` whose ``triage_class``
is constrained to the appropriate ``tc.*`` subset
(:data:`onehealth_agents.contracts.VBD_TRIAGE_CLASSES`,
:data:`onehealth_agents.contracts.HEAT_TRIAGE_CLASSES`). The LLM
step in production is forced through a structured-output schema
keyed on these enums; the stub picks classes with the same priority
order an LLM should arrive at.
"""

from __future__ import annotations

from typing import Iterable

from .contracts import (
    CandidatePathogen,
    HEAT_TRIAGE_CLASSES,
    HeatRisk,
    HeatVulnerabilityComponent,
    HeatVulnerabilityScore,
    Observation,
    TriageClass,
    TriageDecision,
    VBD_TRIAGE_CLASSES,
    Vertical,
)


# --------------------------------------------------------------------------
# Heat-vertical scoring table (from plan/03 Scenario C breakdown).
# --------------------------------------------------------------------------
HEAT_SCORE_TABLE: dict[str, tuple[int, str | None]] = {
    "unsheltered": (3, "pop.unsheltered"),
    "outdoor_exposure": (2, "pop.outdoor_workers"),
    "no_ac": (2, "pop.no_ac_renters"),
    "older_adult_65_plus": (2, "pop.older_adults"),
    "tribal_rural": (1, "pop.tribal_rural"),
    "thermo_meds": (1, None),
    "magenta_heatrisk": (3, None),
    "red_heatrisk": (2, None),
    "orange_heatrisk": (1, None),
    "symptomatic_heat_exhaustion": (2, None),
    "symptomatic_heat_stroke": (3, None),
    "energy_insecurity": (1, None),
}

# Max possible if every line item fires.
HEAT_MAX_POSSIBLE = 15


class HeatTriage:
    """Compute heat-vulnerability score and pick a tc.* class."""

    name = "triage.heat"

    def score(self, observation: Observation) -> HeatVulnerabilityScore:
        ds = observation.dataset
        comps: list[HeatVulnerabilityComponent] = []

        # Sheltered status
        if ds.exposure.sheltered_status == "unsheltered":
            pts, node = HEAT_SCORE_TABLE["unsheltered"]
            comps.append(
                HeatVulnerabilityComponent(
                    factor="unsheltered", points=pts, population_node=node
                )
            )

        # Outdoor time -> outdoor_exposure
        if (ds.exposure.outdoor_time_24h_hours or 0) >= 4:
            pts, node = HEAT_SCORE_TABLE["outdoor_exposure"]
            comps.append(
                HeatVulnerabilityComponent(
                    factor="outdoor_exposure", points=pts, population_node=node
                )
            )

        # AC access
        if ds.exposure.ac_access in {"no", "yes_broken"}:
            pts, node = HEAT_SCORE_TABLE["no_ac"]
            comps.append(
                HeatVulnerabilityComponent(
                    factor="no_ac", points=pts, population_node=node
                )
            )

        # Age 65+
        if (ds.general.age or 0) >= 65:
            pts, node = HEAT_SCORE_TABLE["older_adult_65_plus"]
            comps.append(
                HeatVulnerabilityComponent(
                    factor="older_adult_65_plus", points=pts, population_node=node
                )
            )

        # Thermoregulation-affecting medications
        if ds.exposure.thermo_meds:
            pts, node = HEAT_SCORE_TABLE["thermo_meds"]
            comps.append(
                HeatVulnerabilityComponent(
                    factor="thermo_meds", points=pts, population_node=node
                )
            )

        # Energy insecurity
        if ds.exposure.energy_insecurity:
            pts, node = HEAT_SCORE_TABLE["energy_insecurity"]
            comps.append(
                HeatVulnerabilityComponent(
                    factor="energy_insecurity", points=pts, population_node=node
                )
            )

        # NWS HeatRisk
        risk = ds.environmental.nws_heatrisk_level
        if risk == HeatRisk.MAGENTA:
            pts, node = HEAT_SCORE_TABLE["magenta_heatrisk"]
            comps.append(
                HeatVulnerabilityComponent(
                    factor="magenta_heatrisk", points=pts, population_node=node
                )
            )
        elif risk == HeatRisk.RED:
            pts, node = HEAT_SCORE_TABLE["red_heatrisk"]
            comps.append(
                HeatVulnerabilityComponent(
                    factor="red_heatrisk", points=pts, population_node=node
                )
            )
        elif risk == HeatRisk.ORANGE:
            pts, node = HEAT_SCORE_TABLE["orange_heatrisk"]
            comps.append(
                HeatVulnerabilityComponent(
                    factor="orange_heatrisk", points=pts, population_node=node
                )
            )

        # Symptoms -> heat exhaustion / heat stroke
        if ds.human.confusion or ds.human.hot_dry_skin or (
            (ds.human.core_temp_f or 0) >= 104
        ):
            pts, _ = HEAT_SCORE_TABLE["symptomatic_heat_stroke"]
            comps.append(
                HeatVulnerabilityComponent(
                    factor="symptomatic_heat_stroke", points=pts
                )
            )
        elif ds.human.heavy_sweating or ds.human.headache or ds.human.dizziness:
            pts, _ = HEAT_SCORE_TABLE["symptomatic_heat_exhaustion"]
            comps.append(
                HeatVulnerabilityComponent(
                    factor="symptomatic_heat_exhaustion", points=pts
                )
            )

        total = sum(c.points for c in comps)
        return HeatVulnerabilityScore(
            components=comps,
            total=total,
            max_possible=HEAT_MAX_POSSIBLE,
        )

    def decide(self, observation: Observation) -> TriageDecision:
        score = self.score(observation)
        tc = self._pick_class(observation, score)
        assert tc in HEAT_TRIAGE_CLASSES, "Heat branch escaped its enumeration"
        secondary: list[str] = []
        if tc == TriageClass.GO_TO_COOLING_CENTER and (
            observation.dataset.exposure.transport_access in {None, "none", "transit"}
        ):
            secondary.append("dispatch-CHW-transport")
        rationale = (
            f"Heat vulnerability score {score.total}/{score.max_possible} "
            f"({', '.join(c.factor for c in score.components) or 'baseline'}); "
            f"HeatRisk={observation.dataset.environmental.nws_heatrisk_level}"
        )
        return TriageDecision(
            vertical=Vertical.HEAT,
            triage_class=tc,
            rationale=rationale,
            heat_vulnerability=score,
            secondary_actions=secondary,
        )

    @staticmethod
    def _pick_class(
        observation: Observation, score: HeatVulnerabilityScore
    ) -> TriageClass:
        ds = observation.dataset
        # Life-threatening: classic heat-stroke triad -> 911.
        if ds.human.confusion or ds.human.hot_dry_skin or (
            (ds.human.core_temp_f or 0) >= 104
        ):
            return TriageClass.CALL_911
        if score.total >= 10:
            return TriageClass.GO_TO_COOLING_CENTER
        if score.total >= 6:
            return TriageClass.DISPATCH_CHW
        if score.total >= 3:
            return TriageClass.DRINK_WATER_ADVISORY
        return TriageClass.CHECK_IN_ONLY


# --------------------------------------------------------------------------
# VBD branch
# --------------------------------------------------------------------------
# Symptom -> candidate pathogen mapping. Small but the worked scenarios in
# plan/04 (RMSF tick mail-in, WNV symptomatic, leptospirosis differential)
# all hit this table.
SYMPTOM_TO_PATHOGEN: dict[str, list[str]] = {
    "fever": ["pathogen.wnv", "pathogen.rickettsia_rickettsii", "pathogen.denv"],
    "rash": ["pathogen.rickettsia_rickettsii", "pathogen.denv"],
    "muscle_body_aches": ["pathogen.wnv", "pathogen.denv", "pathogen.leptospira"],
    "headache": ["pathogen.wnv", "pathogen.denv"],
    "red_eyes": ["pathogen.leptospira", "pathogen.denv"],
    "yellow_skin_eyes": ["pathogen.leptospira"],
    "discolored_bloody_urine": ["pathogen.leptospira", "pathogen.rickettsia_rickettsii"],
    "bleeding_body_openings": ["pathogen.denv", "pathogen.rickettsia_rickettsii"],
    "difficulty_breathing": ["pathogen.snv", "pathogen.wnv"],
}

VECTOR_TO_PATHOGEN: dict[str, list[str]] = {
    "tick": [
        "pathogen.rickettsia_rickettsii",
        "pathogen.francisella_tularensis",
        "pathogen.borrelia_burgdorferi",
        "pathogen.anaplasma_phagocytophilum",
        "pathogen.babesia_microti",
    ],
    "mosquito": ["pathogen.wnv", "pathogen.slev", "pathogen.denv", "pathogen.zikv"],
    "flea": ["pathogen.yersinia_pestis"],
}


class VBDTriage:
    """Enumerate candidate pathogens, then pick a tc.* class."""

    name = "triage.vbd"

    def candidates(self, observation: Observation) -> list[CandidatePathogen]:
        ds = observation.dataset
        scores: dict[str, float] = {}
        rationales: dict[str, list[str]] = {}

        for field, pathogens in SYMPTOM_TO_PATHOGEN.items():
            if getattr(ds.human, field, None) or getattr(ds.severity, field, None):
                for pid in pathogens:
                    scores[pid] = scores.get(pid, 0.0) + 1.0
                    rationales.setdefault(pid, []).append(f"symptom:{field}")

        if ds.exposure.tick_insect_bite:
            for pid in VECTOR_TO_PATHOGEN["tick"]:
                scores[pid] = scores.get(pid, 0.0) + 0.5
                rationales.setdefault(pid, []).append("vector:tick")

        if ds.exposure.animal_bite:
            scores["pathogen.rabies_lyssavirus"] = (
                scores.get("pathogen.rabies_lyssavirus", 0.0) + 2.0
            )
            rationales.setdefault("pathogen.rabies_lyssavirus", []).append(
                "exposure:animal_bite"
            )

        if (ds.exposure.attached_duration_hours or 0) >= 6 and any(
            "tick" in r for rs in rationales.values() for r in rs
        ):
            for pid in VECTOR_TO_PATHOGEN["tick"]:
                if pid in scores:
                    scores[pid] += 0.5
                    rationales[pid].append("attached_duration>=6h")

        return [
            CandidatePathogen(
                pathogen_id=pid,
                score=score,
                rationale="; ".join(rationales.get(pid, [])),
            )
            for pid, score in sorted(scores.items(), key=lambda x: -x[1])
        ]

    def decide(self, observation: Observation) -> TriageDecision:
        cands = self.candidates(observation)
        tc = self._pick_class(observation, cands)
        assert tc in VBD_TRIAGE_CLASSES, "VBD branch escaped its enumeration"
        secondary: list[str] = []
        if tc == TriageClass.MAIL_TO_WALKER_LAB:
            secondary.append("self-monitor-for-14-days")
        rationale = (
            f"VBD candidates: "
            f"{', '.join(c.pathogen_id for c in cands[:3]) or 'none matched'}"
        )
        return TriageDecision(
            vertical=Vertical.VBD,
            triage_class=tc,
            rationale=rationale,
            candidate_pathogens=cands,
            secondary_actions=secondary,
        )

    @staticmethod
    def _pick_class(
        observation: Observation, candidates: Iterable[CandidatePathogen]
    ) -> TriageClass:
        ds = observation.dataset
        # Severity markers -> 911.
        if (
            ds.severity.bleeding_body_openings
            or ds.human.difficulty_breathing
            or ds.severity.yellow_skin_eyes
        ):
            return TriageClass.CALL_911

        symptomatic = any(
            getattr(ds.human, f, None)
            for f in (
                "fever",
                "rash",
                "muscle_body_aches",
                "headache",
                "nausea_vomiting",
                "chills",
            )
        )
        has_tick = ds.exposure.tick_insect_bite

        # Tick mail-in flow (no symptoms).
        if has_tick and not symptomatic:
            return TriageClass.MAIL_TO_WALKER_LAB

        if ds.severity.discolored_bloody_urine or (
            symptomatic and any(c.score >= 2.0 for c in candidates)
        ):
            return TriageClass.URGENT_CARE

        if symptomatic:
            return TriageClass.SEE_CLINICIAN

        return TriageClass.CHECK_IN_ONLY


class TriageAgent:
    """Vertical-aware dispatcher.

    Picks the heat branch for ``Vertical.HEAT`` (or ``BOTH`` when no VBD
    candidates surface), the VBD branch otherwise. Always returns a
    :class:`TriageDecision` whose ``triage_class`` lives in the right
    enumeration subset.
    """

    name = "triage"

    def __init__(self) -> None:
        self.heat = HeatTriage()
        self.vbd = VBDTriage()

    def run(self, observation: Observation) -> TriageDecision:
        vertical = observation.vertical
        if vertical == Vertical.HEAT:
            return self.heat.decide(observation)
        if vertical == Vertical.VBD:
            return self.vbd.decide(observation)
        if vertical == Vertical.BOTH:
            # Prefer VBD if a candidate pathogen surfaces, else heat.
            vbd_decision = self.vbd.decide(observation)
            if vbd_decision.candidate_pathogens:
                return vbd_decision
            return self.heat.decide(observation)
        # Neither -- nothing to do.
        return TriageDecision(
            vertical=Vertical.NEITHER,
            triage_class=TriageClass.CHECK_IN_ONLY,
            rationale="No vertical matched -- logging observation only.",
        )


__all__ = ["TriageAgent", "HeatTriage", "VBDTriage", "HEAT_SCORE_TABLE"]
