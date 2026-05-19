"""ValidationAgent -- dedupe, spatial sanity, consent enforcement.

Deterministic Python rules per ``plan/03``. The LLM-driven fuzzy
checks (photo quality, species-range sanity) are left as TODOs; the
stub returns ``accept`` for sane inputs and ``flag-for-review`` when
something obvious is missing.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .contracts import (
    ConsentProfile,
    Observation,
    ValidationReport,
    ValidationStatus,
)


# consent.* -> set of param.* slugs that should be suppressed.
# Mirrors the suppressesField edges in schema/deep/application.sql.
_SUPPRESS_RULES: dict[ConsentProfile, set[str]] = {
    ConsentProfile.ANONYMOUS_HEAT: {
        "param.email",
        "param.occupation",
        "param.household_member_id",
        "param.absent_work",
        "param.absent_school",
        "param.phone_number",
    },
    ConsentProfile.TICK_MAILIN: {
        "param.no_symptoms",
        "param.symptoms",
        "param.date_of_illness",
        "param.cough_congestion",
        "param.nausea_vomiting",
        "param.difficulty_breathing",
        "param.sore_throat",
        "param.rash",
        "param.fever",
        "param.chills",
        "param.diarrhea",
        "param.bleeding_body_openings",
        "param.red_eyes",
        "param.muscle_body_aches",
        "param.discolored_bloody_urine",
        "param.loss_smell_taste",
        "param.yellow_skin_eyes",
        "param.sought_health_care",
    },
    ConsentProfile.WEARABLE_ONLY: {
        "param.email",
        "param.phone_number",
        "param.occupation",
        "param.household_member_id",
        "param.geographical_coordinates",
        "param.symptoms",
        "param.no_symptoms",
        "param.date_of_illness",
        "param.absent_work",
        "param.absent_school",
        "param.sought_health_care",
        "param.mass_gathering",
        "param.tick_insect_bite",
        "param.animal_bite",
        "param.history_of_travel",
        "param.contact_live_animals",
        "param.contact_dead_sick_animals",
        "param.contact_sick_case",
    },
    ConsentProfile.FULL_FOLLOWUP: set(),
}


class ValidationAgent:
    name = "validation"

    def __init__(self, dedupe_window_minutes: int = 5) -> None:
        self.dedupe_window = timedelta(minutes=dedupe_window_minutes)
        # In-process dedupe memory; production swaps this for a SQL lookup.
        self._recent: list[tuple[datetime, str]] = []

    def run(self, observation: Observation) -> ValidationReport:
        reasons: list[str] = []
        flags: list[str] = []
        suppressed: list[str] = []

        # 1. Dedupe.
        try:
            now = datetime.fromisoformat(observation.received_at)
        except ValueError:
            now = datetime.now(timezone.utc)
        duplicate_of: str | None = None
        if observation.dataset.general.unique_id:
            for ts, prev_id in self._recent:
                if (
                    prev_id == observation.dataset.general.unique_id
                    and abs((now - ts).total_seconds())
                    <= self.dedupe_window.total_seconds()
                ):
                    duplicate_of = prev_id
                    reasons.append(f"duplicate of {prev_id}")
                    break
            self._recent.append((now, observation.dataset.general.unique_id))

        # 2. Spatial sanity: coords inside the AZ bounding box.
        lat = observation.dataset.general.lat
        lon = observation.dataset.general.lon
        if lat is not None and lon is not None:
            if not (30.5 <= lat <= 37.5 and -115.5 <= lon <= -108.5):
                flags.append("coordinates_outside_arizona_bbox")

        # 3. Consent suppression: any field that should have been
        #    suppressed but came through is a flag (not a reject -- the
        #    Intake Agent is supposed to drop them, but if it didn't we
        #    just note it and continue).
        for slug in _SUPPRESS_RULES.get(observation.consent_profile, set()):
            if self._field_present(observation, slug):
                suppressed.append(slug)
                flags.append(f"consent_violation:{slug}")

        # 4. Tribal-data MOU check (placeholder).
        if observation.geo and observation.geo.tribe_id:
            flags.append(f"tribal_mou_check_required:{observation.geo.tribe_id}")

        # Decide final status.
        if duplicate_of:
            status = ValidationStatus.REJECT
        elif flags or reasons:
            status = ValidationStatus.FLAG_FOR_REVIEW
        else:
            status = ValidationStatus.ACCEPT

        return ValidationReport(
            status=status,
            reasons=reasons,
            duplicate_of=duplicate_of,
            flags=flags,
            consent_profile=observation.consent_profile,
            suppressed_fields=suppressed,
        )

    @staticmethod
    def _field_present(observation: Observation, slug: str) -> bool:
        """Check whether a ``param.*`` slug currently has a non-None value."""
        local = slug.removeprefix("param.")
        local = {
            "email": "contact_email",
            "phone_number": "contact_phone",
            "geographical_coordinates": "lat",
        }.get(local, local)
        for sub in (
            observation.dataset.general,
            observation.dataset.human,
            observation.dataset.severity,
            observation.dataset.exposure,
            observation.dataset.auxiliary,
            observation.dataset.environmental,
        ):
            value: Any = getattr(sub, local, None)
            if value is not None and value != []:
                return True
        return False


__all__ = ["ValidationAgent"]
