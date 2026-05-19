"""IntakeAgent -- turns raw input into a Minimum Dataset draft.

Production version: Claude Haiku with a structured-output schema
constrained to the Figure-2 fields.

Stub version (this file): when input is already a dict, the draft is
the dict; when input is free text, a small bank of regexes pulls out
the handful of fields the worked scenarios in ``plan/04`` actually
mention. Enough to wire the orchestrator end-to-end; the LLM call goes
here later.
"""

from __future__ import annotations

import re
from typing import Any

from .contracts import (
    AuxiliaryClass,
    Channel,
    ConsentProfile,
    EnvironmentalClass,
    ExposureClass,
    GeneralClass,
    HumanClass,
    Kind,
    MinimumDataset,
    Observation,
    SeverityClass,
    Vertical,
)


_AGE_RE = re.compile(r"\b(?:age|aged?)\s*[:\-]?\s*(\d{1,3})\b", re.IGNORECASE)
_SEX_RE = re.compile(r"\b(female|male|man|woman|m|f)\b", re.IGNORECASE)
_ZIP_RE = re.compile(r"\b(\d{5})\b")
_GPS_RE = re.compile(r"(-?\d{1,3}\.\d{2,}),\s*(-?\d{1,3}\.\d{2,})")
_HOURS_RE = re.compile(
    r"(\d{1,3})\s*(?:h|hr|hrs|hour|hours)\s*(?:attached|attached for)?", re.IGNORECASE
)
_TEMP_RE = re.compile(r"(\d{2,3}(?:\.\d+)?)\s*(?:°|deg|degrees)?\s*F\b", re.IGNORECASE)

_VBD_KEYWORDS = re.compile(
    r"\b(tick|mosquito|bite|attached|rash|chills|west nile|wnv|rmsf|dengue|"
    r"plague|hantavirus|leptospirosis|tularemia)\b",
    re.IGNORECASE,
)
_HEAT_KEYWORDS = re.compile(
    r"\b(heat|hot|sweat|dehydrat|cooling center|unsheltered|magenta|orange|"
    r"red heatrisk|heatrisk|ac|air conditioning|fan)\b",
    re.IGNORECASE,
)

_SYMPTOM_MAP = {
    "fever": "fever",
    "headache": "headache",
    "muscle ach": "muscle_body_aches",
    "body ach": "muscle_body_aches",
    "rash": "rash",
    "nausea": "nausea_vomiting",
    "vomit": "nausea_vomiting",
    "diarrhea": "diarrhea",
    "confus": "confusion",
    "altered mental": "confusion",
    "hot dry skin": "hot_dry_skin",
    "stopped sweating": "hot_dry_skin",
    "heavy sweat": "heavy_sweating",
    "sweating profusely": "heavy_sweating",
    "sweating heavily": "heavy_sweating",
    "dizz": "dizziness",
    "faint": "dizziness",
    "cramp": "muscle_cramps",
    "difficulty breathing": "difficulty_breathing",
    "sore throat": "sore_throat",
    "cough": "cough_congestion",
    "congestion": "cough_congestion",
    "chills": "chills",
}


class IntakeAgent:
    """Free-text / structured intake -> :class:`Observation` draft.

    The stub is deterministic. It picks a vertical from keywords and
    routes consent-profile selection from the channel hint when one is
    provided in the input dict.
    """

    name = "intake"

    def __init__(self, default_channel: Channel = Channel.MOBILE) -> None:
        self.default_channel = default_channel

    def run(self, raw: str | dict[str, Any]) -> Observation:
        if isinstance(raw, dict):
            return self._from_structured(raw)
        return self._from_text(raw)

    # ------------------------------------------------------------------
    def _from_structured(self, raw: dict[str, Any]) -> Observation:
        """Accept a dict shaped like {'general': {...}, 'channel': ...}."""
        channel = Channel(raw.get("channel", self.default_channel.value))
        vertical = Vertical(raw.get("vertical", Vertical.NEITHER.value))
        consent = ConsentProfile(
            raw.get("consent_profile", self._default_consent(vertical, channel).value)
        )
        kind = Kind(raw.get("kind", Kind.REPORT.value))

        dataset = MinimumDataset(
            general=GeneralClass.model_validate(raw.get("general", {})),
            human=HumanClass.model_validate(raw.get("human", {})),
            severity=SeverityClass.model_validate(raw.get("severity", {})),
            exposure=ExposureClass.model_validate(raw.get("exposure", {})),
            auxiliary=AuxiliaryClass.model_validate(raw.get("auxiliary", {})),
            environmental=EnvironmentalClass.model_validate(
                raw.get("environmental", {})
            ),
        )
        dataset = self._apply_consent_suppression(dataset, consent)

        return Observation(
            kind=kind,
            vertical=vertical,
            source=channel,
            consent_profile=consent,
            dataset=dataset,
        )

    def _from_text(self, text: str) -> Observation:
        general = GeneralClass()
        human = HumanClass()
        exposure = ExposureClass()
        severity = SeverityClass()

        m = _AGE_RE.search(text)
        if m:
            general.age = float(m.group(1))
        m = _SEX_RE.search(text)
        if m:
            tok = m.group(1).lower()
            general.sex = "F" if tok in {"f", "female", "woman"} else "M"
        m = _ZIP_RE.search(text)
        if m:
            general.postal_code = m.group(1)
        m = _GPS_RE.search(text)
        if m:
            general.lat = float(m.group(1))
            general.lon = float(m.group(2))

        # Symptoms
        seen: set[str] = set()
        for fragment, field in _SYMPTOM_MAP.items():
            if fragment in text.lower():
                seen.add(field)
        for field in seen:
            setattr(human, field, True)

        # Temperature
        m = _TEMP_RE.search(text)
        if m:
            human.core_temp_f = float(m.group(1))

        # Bite metadata
        if "tick" in text.lower() or "bite" in text.lower():
            exposure.tick_insect_bite = True
            m = _HOURS_RE.search(text)
            if m:
                exposure.attached_duration_hours = float(m.group(1))
            for location in ("scalp", "behind ear", "neck", "arm", "leg", "torso", "beltline"):
                if location in text.lower():
                    exposure.bite_location = location.replace(" ", "_")  # type: ignore[assignment]
                    break

        # Vertical detection
        is_vbd = bool(_VBD_KEYWORDS.search(text))
        is_heat = bool(_HEAT_KEYWORDS.search(text))
        if is_vbd and is_heat:
            vertical = Vertical.BOTH
        elif is_vbd:
            vertical = Vertical.VBD
        elif is_heat:
            vertical = Vertical.HEAT
        else:
            vertical = Vertical.NEITHER

        channel = self.default_channel
        consent = self._default_consent(vertical, channel)
        dataset = MinimumDataset(
            general=general,
            human=human,
            severity=severity,
            exposure=exposure,
            auxiliary=AuxiliaryClass(),
            environmental=EnvironmentalClass(),
        )
        dataset = self._apply_consent_suppression(dataset, consent)
        return Observation(
            kind=Kind.REPORT,
            vertical=vertical,
            source=channel,
            consent_profile=consent,
            dataset=dataset,
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _default_consent(
        vertical: Vertical, channel: Channel
    ) -> ConsentProfile:
        if channel == Channel.WEARABLE:
            return ConsentProfile.WEARABLE_ONLY
        if vertical == Vertical.HEAT and channel == Channel.CHW_TABLET:
            return ConsentProfile.ANONYMOUS_HEAT
        if vertical == Vertical.VBD:
            return ConsentProfile.TICK_MAILIN
        return ConsentProfile.FULL_FOLLOWUP

    @staticmethod
    def _apply_consent_suppression(
        dataset: MinimumDataset, consent: ConsentProfile
    ) -> MinimumDataset:
        """Mirror the ``suppressesField`` edges from application.sql."""
        if consent == ConsentProfile.ANONYMOUS_HEAT:
            dataset.general.contact_email = None
            dataset.general.contact_phone = None
            dataset.general.occupation = None
            dataset.general.household_member_id = None
            dataset.human.absent_work = None
            dataset.human.absent_school = None
        elif consent == ConsentProfile.TICK_MAILIN:
            # Suppress Human-class symptom set unless the bite branch wants them.
            # For mail-in with no symptoms we zero out the bag.
            if not any(
                getattr(dataset.human, f) for f in HumanClass.model_fields
            ):
                dataset.human = HumanClass()
        elif consent == ConsentProfile.WEARABLE_ONLY:
            dataset.general.contact_email = None
            dataset.general.contact_phone = None
            dataset.general.occupation = None
            dataset.general.household_member_id = None
            dataset.general.lat = None
            dataset.general.lon = None
            dataset.human = HumanClass()
            dataset.exposure = ExposureClass()
        return dataset


__all__ = ["IntakeAgent"]
