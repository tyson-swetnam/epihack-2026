"""Pydantic models for the Intake API.

These are hand-written to match ``api/openapi.yaml``. In a later
commit they'll be **generated** from the spec via::

    uvx datamodel-code-generator \\
        --input ../api/openapi.yaml \\
        --output src/onehealth_agents/api/models.py \\
        --output-model-type pydantic_v2.BaseModel

Until then, the spec is normative and this file MUST track it.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# --- Common ----------------------------------------------------------------


ReportType = Literal["human", "animal", "environmental"]

EventClass = Literal[
    # human
    "human.fever_chills",
    "human.heat_distress",
    "human.respiratory",
    "human.gastrointestinal",
    "human.rash_or_bite",
    "human.exposure_water",
    "human.exposure_animal",
    "human.animal_bite_scratch",
    # animal
    "animal.dead_wildlife",
    "animal.dead_livestock",
    "animal.sick_unusual_behaviour",
    "animal.mass_die_off",
    "animal.unusual_species_sighting",
    "animal.pet_sick",
    "animal.malnourishment",
    # env
    "env.sewage",
    "env.smoke_or_burn",
    "env.standing_water",
    "env.water_quality",
    "env.air_quality",
    "env.illegal_dumping",
    "env.food_safety",
]

SymptomCategory = Literal[
    "fever",
    "chills",
    "headache",
    "muscle_aches",
    "cough",
    "shortness_of_breath",
    "nausea_vomiting",
    "diarrhea",
    "rash",
    "dizziness",
    "confusion",
    "heat_cramps",
]

NextAction = Literal[
    "self_care",
    "see_clinician_routine",
    "see_clinician_urgent",
    "call_211",
    "report_to_agency",
    "mail_in_specimen",
]


class CoarseLocation(BaseModel):
    """ZIP or 1 km grid cell. Precise lat/lon is never on the wire."""

    model_config = ConfigDict(extra="forbid")

    zip: Optional[str] = Field(default=None, pattern=r"^[0-9]{5}$")
    grid_id: Optional[str] = Field(
        default=None,
        pattern=r"^g1km:-?\d+\.\d{1,2},-?\d+\.\d{1,2}$",
    )
    resolution_m: Optional[int] = Field(default=None, ge=1000)


class CitedSource(BaseModel):
    name: str
    url: str
    mcp: Optional[str] = None


# --- Reports ---------------------------------------------------------------


class ReportPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_type: ReportType
    event_class: EventClass
    coarse_location: CoarseLocation
    event_date: Optional[date] = None
    severity: Optional[Literal["grin", "neutral", "frown", "alarm"]] = None
    count: Optional[int] = Field(default=None, ge=1, le=10_000)
    species: Optional[str] = Field(default=None, max_length=80)
    symptoms: Optional[list[SymptomCategory]] = Field(default=None, max_length=12)
    notes: Optional[str] = Field(default=None, max_length=500)
    # Authenticated submit only — link this report to the caller's
    # user_id. Always defaults to False even for signed-in users; this
    # preserves the "signed in but anonymous report" path
    # (plan/07 § Anonymous → authenticated transitions, case 3).
    attach: bool = False


class TriageOutcome(BaseModel):
    next_action: NextAction
    urgency: Optional[Literal["none", "routine", "urgent", "emergent"]] = None
    copy: Optional[str] = Field(default=None, max_length=600)
    sources: list[CitedSource]


class ContextSignal(BaseModel):
    class_: Literal["vbd", "heat", "wildlife", "environment"] = Field(alias="class")
    headline: str = Field(max_length=200)
    severity_tier: Optional[Literal["info", "advisory", "watch", "warning"]] = None
    valid_through: Optional[datetime] = None
    source: CitedSource


class ContextEnvelope(BaseModel):
    coarse_location: CoarseLocation
    signals: list[ContextSignal]


class ReportAck(BaseModel):
    observation_id: str
    claim_token: str
    status_url: str
    queued: bool = False
    triage: Optional[TriageOutcome] = None
    context: Optional[ContextEnvelope] = None


class ReportStatus(BaseModel):
    observation_id: str
    state: Literal["received", "triaged", "notified", "archived", "withdrawn"]
    triage: Optional[TriageOutcome] = None
    context: Optional[ContextEnvelope] = None
    profile_attached: bool = False


# --- Profile (per-report, anonymous) --------------------------------------


class ContactChannel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: Optional[EmailStr] = None
    sms_phone: Optional[str] = Field(default=None, pattern=r"^\+?[0-9]{10,15}$")


class ProfilePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    home_zip: Optional[str] = Field(default=None, pattern=r"^[0-9]{5}$")
    precise_location_consent: Optional[bool] = None
    contact_about_my_reports: Optional[ContactChannel] = None
    contact_about_nearby_events: Optional[ContactChannel] = None
    share_photo_gps_animal_env: Optional[bool] = None
    share_photo_gps_human: Optional[bool] = None
    age_band: Optional[Literal["<18", "18-29", "30-44", "45-64", "65+"]] = None
    sex_at_birth: Optional[
        Literal["female", "male", "intersex", "prefer_not_to_say"]
    ] = None
    gender_identity: Optional[str] = Field(default=None, max_length=60)
    race_ethnicity: Optional[list[str]] = None
    primary_language: Optional[str] = Field(default=None, max_length=32)
    accessibility_needs: Optional[list[str]] = None
    household_size: Optional[int] = Field(default=None, ge=1, le=20)
    has_pets: Optional[bool] = None
    works_outdoors: Optional[bool] = None


# --- Auth -----------------------------------------------------------------


class AccountProfile(BaseModel):
    """Persistent profile attached to an authenticated account.

    Distinct from ``ProfilePatch`` (per-report). This profile applies
    to every future report from the same account; sees and respects
    the same consent-toggle defaults.
    """

    model_config = ConfigDict(extra="forbid")

    display_name: Optional[str] = Field(default=None, max_length=80)
    home_zip: Optional[str] = Field(default=None, pattern=r"^[0-9]{5}$")
    primary_language: Optional[str] = Field(default=None, max_length=32)
    accessibility_needs: Optional[list[str]] = None
    contact_email_opt_in: bool = False
    contact_sms_phone: Optional[str] = Field(default=None, pattern=r"^\+?[0-9]{10,15}$")
    contact_sms_opt_in: bool = False
    precise_location_consent: bool = False
    share_photo_gps_animal_env: bool = False
    share_photo_gps_human: bool = False
    age_band: Optional[Literal["<18", "18-29", "30-44", "45-64", "65+"]] = None
    sex_at_birth: Optional[
        Literal["female", "male", "intersex", "prefer_not_to_say"]
    ] = None
    gender_identity: Optional[str] = Field(default=None, max_length=60)
    race_ethnicity: Optional[list[str]] = None


class CurrentUser(BaseModel):
    user_id: str
    email: Optional[EmailStr] = None
    email_verified: bool = False
    provider: Optional[Literal["email", "google", "facebook", "apple"]] = None
    created_at: datetime
    last_sign_in_at: Optional[datetime] = None
    profile: Optional[AccountProfile] = None


class ClaimAttachRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_token: str = Field(pattern=r"^[A-Za-z0-9_-]{16,}$")


# --- Dashboard (owner-scoped reports + community aggregates) ---------------


ReportState = Literal["received", "triaged", "notified", "archived", "withdrawn"]


class ReportSummary(BaseModel):
    """Coarse, owner-scoped view of one report for the personal dashboard."""

    observation_id: str
    report_type: ReportType
    event_class: EventClass
    coarse_location: CoarseLocation
    event_date: Optional[date] = None
    severity: Optional[Literal["grin", "neutral", "frown", "alarm"]] = None
    state: ReportState = "received"
    next_action: Optional[NextAction] = None
    has_photo: bool = False
    photo_url: Optional[str] = None
    created_at: Optional[datetime] = None


class ReportList(BaseModel):
    reports: list[ReportSummary]


class ZctaAggregate(BaseModel):
    """ZCTA-bucketed counts. Small cells are suppressed before this point."""

    zcta: str = Field(pattern=r"^[0-9]{5}$")
    report_type: ReportType
    count: int = Field(ge=1)
    window: Optional[str] = None


class CommunityEnvelope(BaseModel):
    coarse_location: CoarseLocation
    signals: list[ContextSignal]
    local: list[ZctaAggregate]
    regional: list[ZctaAggregate]


class ApiError(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None
