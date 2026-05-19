"""Typed pydantic contracts shared by every agent in the pipeline.

The models here are the on-the-wire shapes the eight agents pass to each
other. They mirror Figure 2 (Minimum Set of Key Data Parameters) one
sub-model per parameter class, plus the application-runtime extensions
seeded in ``schema/deep/application.sql`` (heat symptoms, VBD exposure
factors, consent profiles, triage classes, wearable metrics).

Field names use the ``param.*`` slug suffix from
``schema/knowledge_graph.sql`` so that an ``Observation`` round-trips
through the knowledge graph property bag with no renaming.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enumerations  (mirror schema/deep/application.sql triage_class + verticals)
# ---------------------------------------------------------------------------
class Vertical(str, Enum):
    """Which surveillance vertical the observation falls under."""

    VBD = "vbd"
    HEAT = "heat"
    BOTH = "both"
    NEITHER = "neither"


class Kind(str, Enum):
    REPORT = "report"
    MCP_PULL = "mcp_pull"
    AGENCY_CASE = "agency_case"


class Channel(str, Enum):
    """Intake / notification channel surfaces."""

    MOBILE = "mobile"
    SMS = "sms"
    VOICE = "voice"
    WEB = "web"
    CHW_TABLET = "chw_tablet"
    AGENCY_DASHBOARD = "agency_dashboard"
    WEARABLE = "wearable"


class ConsentProfile(str, Enum):
    """Slugs of ``consent.*`` nodes from schema/deep/application.sql."""

    ANONYMOUS_HEAT = "consent.anonymous_heat"
    TICK_MAILIN = "consent.tick_mailin"
    WEARABLE_ONLY = "consent.wearable_only"
    FULL_FOLLOWUP = "consent.full_followup"


class TriageClass(str, Enum):
    """Closed enumeration of ``tc.*`` nodes; the Triage Agent MUST emit one."""

    SELF_CARE = "tc.self_care"
    SEE_CLINICIAN = "tc.see_clinician"
    URGENT_CARE = "tc.urgent_care"
    CALL_911 = "tc.call_911"
    REPORT_TO_AZGFD = "tc.report_to_azgfd"
    MAIL_TO_WALKER_LAB = "tc.mail_to_walker_lab"
    GO_TO_COOLING_CENTER = "tc.go_to_cooling_center"
    DISPATCH_CHW = "tc.dispatch_chw"
    CHECK_IN_ONLY = "tc.check_in_only"
    DRINK_WATER_ADVISORY = "tc.drink_water_advisory"


# Vertical-scoped subsets the TriageAgent rule layer uses to gate LLM output.
VBD_TRIAGE_CLASSES: frozenset[TriageClass] = frozenset(
    {
        TriageClass.SELF_CARE,
        TriageClass.SEE_CLINICIAN,
        TriageClass.URGENT_CARE,
        TriageClass.CALL_911,
        TriageClass.REPORT_TO_AZGFD,
        TriageClass.MAIL_TO_WALKER_LAB,
        TriageClass.CHECK_IN_ONLY,
    }
)
HEAT_TRIAGE_CLASSES: frozenset[TriageClass] = frozenset(
    {
        TriageClass.SELF_CARE,
        TriageClass.SEE_CLINICIAN,
        TriageClass.URGENT_CARE,
        TriageClass.CALL_911,
        TriageClass.GO_TO_COOLING_CENTER,
        TriageClass.DISPATCH_CHW,
        TriageClass.CHECK_IN_ONLY,
        TriageClass.DRINK_WATER_ADVISORY,
    }
)


class ValidationStatus(str, Enum):
    ACCEPT = "accept"
    FLAG_FOR_REVIEW = "flag-for-review"
    REJECT = "reject"


class HeatRisk(str, Enum):
    GREEN = "Green"
    YELLOW = "Yellow"
    ORANGE = "Orange"
    RED = "Red"
    MAGENTA = "Magenta"


# ---------------------------------------------------------------------------
# Parameter classes (Figure 2 + application extensions)
#
# Each sub-model maps 1:1 to one of the ``category.*`` nodes in
# schema/knowledge_graph.sql. Field names use the ``param.*`` slug suffix.
# Every field is Optional because real intake is messy -- the Validation
# Agent decides whether the populated subset is enough.
# ---------------------------------------------------------------------------
class GeneralClass(BaseModel):
    """``category.general`` -- demographics, contact, geo (Figure 2)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    age: Optional[float] = None
    sex: Optional[Literal["F", "M", "X", "unknown"]] = None
    contact_email: Optional[str] = Field(default=None, alias="email")
    unique_id: Optional[str] = None
    occupation: Optional[str] = None
    reported_at: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp the report entered the system.",
    )
    postal_code: Optional[str] = None
    contact_phone: Optional[str] = Field(default=None, alias="phone_number")
    household_member_id: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    coord_precision: Optional[Literal["exact", "approximate", "zip", "unknown"]] = None


class HumanClass(BaseModel):
    """``category.human`` -- Figure 2 symptom checklist (VBD + Heat overlap)."""

    model_config = ConfigDict(extra="forbid")

    no_symptoms: Optional[bool] = None
    symptoms: Optional[list[str]] = None
    date_of_illness: Optional[str] = None
    cough_congestion: Optional[bool] = None
    nausea_vomiting: Optional[bool] = None
    difficulty_breathing: Optional[bool] = None
    sore_throat: Optional[bool] = None
    rash: Optional[bool] = None
    fever: Optional[bool] = None
    chills: Optional[bool] = None
    diarrhea: Optional[bool] = None
    red_eyes: Optional[bool] = None
    muscle_body_aches: Optional[bool] = None
    loss_smell_taste: Optional[bool] = None
    absent_work: Optional[bool] = None
    absent_school: Optional[bool] = None
    sought_health_care: Optional[bool] = None

    # Application-runtime additions (schema/deep/application.sql symptom.*)
    confusion: Optional[bool] = None
    hot_dry_skin: Optional[bool] = None
    heavy_sweating: Optional[bool] = None
    headache: Optional[bool] = None
    dizziness: Optional[bool] = None
    muscle_cramps: Optional[bool] = None
    core_temp_f: Optional[float] = None


class SeverityClass(BaseModel):
    """``category.severity_marker`` -- the three Figure 2 markers nested
    under Human in the SQL seed but called out separately on the figure."""

    model_config = ConfigDict(extra="forbid")

    bleeding_body_openings: Optional[bool] = None
    discolored_bloody_urine: Optional[bool] = None
    yellow_skin_eyes: Optional[bool] = None


class ExposureClass(BaseModel):
    """``category.exposure`` -- Figure 2 + VBD + Heat extensions."""

    model_config = ConfigDict(extra="forbid")

    mass_gathering: Optional[bool] = None
    tick_insect_bite: Optional[bool] = None
    animal_bite: Optional[bool] = None
    history_of_travel: Optional[bool] = None
    contact_live_animals: Optional[bool] = None
    contact_dead_sick_animals: Optional[bool] = None
    contact_sick_case: Optional[bool] = None

    # VBD-specific (schema/deep/application.sql exposure.bite_*)
    bite_location: Optional[
        Literal["scalp", "behind_ear", "neck", "arm", "leg", "torso", "beltline", "other"]
    ] = None
    attached_duration_hours: Optional[float] = None
    standing_water_meters: Optional[float] = None
    rainfall_last7_mm: Optional[float] = None

    # Heat-specific (schema/deep/application.sql exposure.*)
    outdoor_time_24h_hours: Optional[float] = None
    ac_access: Optional[Literal["yes", "yes_broken", "no", "unknown"]] = None
    energy_insecurity: Optional[bool] = None
    sheltered_status: Optional[
        Literal["sheltered", "unsheltered", "precariously_housed"]
    ] = None
    thermo_meds: Optional[bool] = None
    transport_access: Optional[
        Literal["own_vehicle", "rideshare", "transit", "none"]
    ] = None


class AuxiliaryClass(BaseModel):
    """``category.auxiliary`` -- biomarker, photo, lab confirmation."""

    model_config = ConfigDict(extra="forbid")

    digital_biomarker: Optional[dict[str, float]] = Field(
        default=None,
        description="Wearable-metric slug -> numeric reading "
        "(e.g. {'wearable.skin_temp_c': 38.4}).",
    )
    photo_url: Optional[str] = None
    photo_quality_score: Optional[float] = None
    diagnostic_lab: Optional[str] = Field(
        default=None,
        description="Free-text or LOINC/ICD-10 reference for lab confirmation.",
    )


class EnvironmentalClass(BaseModel):
    """``category.environmental`` -- Figure 2 + heat & VBD extensions."""

    model_config = ConfigDict(extra="forbid")

    date_env_incident: Optional[str] = None
    location_vector_spotting: Optional[str] = None
    unusual_vectors: Optional[bool] = None
    vector_density: Optional[float] = None
    flooding: Optional[bool] = None
    water_contamination: Optional[bool] = None

    # Heat-vertical
    ambient_temp_f: Optional[float] = None
    humidity_pct: Optional[float] = None
    heat_index_f: Optional[float] = None
    nws_heatrisk_level: Optional[HeatRisk] = None
    urban_heat_island_intensity: Optional[float] = None
    active_heat_watch_warning: Optional[bool] = None


class LivestockClass(BaseModel):
    """``category.livestock`` -- VBD-only Figure 2 fields."""

    model_config = ConfigDict(extra="forbid")

    date_livestock_incident: Optional[str] = None
    location_livestock_incident: Optional[str] = None
    livestock_sick_count: Optional[int] = None
    livestock_dead_count: Optional[int] = None
    livestock_species: Optional[str] = None


class WildlifeClass(BaseModel):
    """``category.wildlife`` -- VBD-only Figure 2 fields."""

    model_config = ConfigDict(extra="forbid")

    date_wildlife_incident: Optional[str] = None
    location_wildlife_incident: Optional[str] = None
    wildlife_species: Optional[str] = None
    wildlife_dead_count: Optional[int] = None


# ---------------------------------------------------------------------------
# Aggregate dataset
# ---------------------------------------------------------------------------
class MinimumDataset(BaseModel):
    """Composite of every Figure-2 + extension class.

    This is the contract Intake produces, Geo-Enrichment and Validation
    annotate, and Triage consumes.
    """

    model_config = ConfigDict(extra="forbid")

    general: GeneralClass = Field(default_factory=GeneralClass)
    human: HumanClass = Field(default_factory=HumanClass)
    severity: SeverityClass = Field(default_factory=SeverityClass)
    exposure: ExposureClass = Field(default_factory=ExposureClass)
    auxiliary: AuxiliaryClass = Field(default_factory=AuxiliaryClass)
    environmental: EnvironmentalClass = Field(default_factory=EnvironmentalClass)
    livestock: Optional[LivestockClass] = None
    wildlife: Optional[WildlifeClass] = None


# ---------------------------------------------------------------------------
# Geo enrichment output  (Geo-Enrichment Agent)
# ---------------------------------------------------------------------------
class GeoEnrichment(BaseModel):
    """Edges from an observation to county / tribe / region nodes."""

    model_config = ConfigDict(extra="forbid")

    county_id: Optional[str] = Field(
        default=None, description="kg slug, e.g. 'county.santa_cruz'."
    )
    tribe_id: Optional[str] = None
    region_id: Optional[str] = Field(
        default=None, description="e.g. 'region.maricopa_metro'."
    )
    zcta: Optional[str] = None
    responsible_vector_control_agency: Optional[str] = None
    coord_precision: Literal["exact", "approximate", "zip", "unknown"] = "unknown"


# ---------------------------------------------------------------------------
# Validation output  (Validation Agent)
# ---------------------------------------------------------------------------
class ValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ValidationStatus
    reasons: list[str] = Field(default_factory=list)
    duplicate_of: Optional[str] = None
    flags: list[str] = Field(default_factory=list)
    consent_profile: ConsentProfile = ConsentProfile.FULL_FOLLOWUP
    suppressed_fields: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Triage output  (Triage Agent, both branches)
# ---------------------------------------------------------------------------
class HeatVulnerabilityComponent(BaseModel):
    """Single line-item in the heat-vulnerability score breakdown."""

    model_config = ConfigDict(extra="forbid")

    factor: str = Field(description="Human-readable label, e.g. 'unsheltered'.")
    points: int
    population_node: Optional[str] = Field(
        default=None, description="kg slug, e.g. 'pop.unsheltered'."
    )


class HeatVulnerabilityScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    components: list[HeatVulnerabilityComponent] = Field(default_factory=list)
    total: int = 0
    max_possible: int = 15

    @property
    def normalized(self) -> float:
        return 0.0 if self.max_possible == 0 else self.total / self.max_possible


class CandidatePathogen(BaseModel):
    """VBD-branch candidate emitted before final triage class is chosen."""

    model_config = ConfigDict(extra="forbid")

    pathogen_id: str
    via_vector_id: Optional[str] = None
    score: float = 0.0
    rationale: Optional[str] = None


class TriageDecision(BaseModel):
    """Output of the Triage Agent.

    The ``triage_class`` field is constrained to the ``tc.*`` enumeration
    seeded in ``schema/deep/application.sql`` -- even the LLM-driven
    branch is gated by this set so stray strings can never escape.
    """

    model_config = ConfigDict(extra="forbid")

    vertical: Vertical
    triage_class: TriageClass
    rationale: str
    candidate_pathogens: list[CandidatePathogen] = Field(default_factory=list)
    heat_vulnerability: Optional[HeatVulnerabilityScore] = None
    secondary_actions: list[str] = Field(
        default_factory=list,
        description="Optional ancillary actions (e.g. 'self-monitor-for-14-days').",
    )


# ---------------------------------------------------------------------------
# Enrichment output  (Enrichment Agent)
# ---------------------------------------------------------------------------
class EnrichmentRecord(BaseModel):
    """One live-data edge attached to the observation."""

    model_config = ConfigDict(extra="forbid")

    mcp_server: str = Field(description="e.g. 'vectorsurv-mcp'.")
    tool: str = Field(description="MCP tool name that produced the record.")
    edge_predicate: str = Field(
        default="enrichedWith",
        description="Predicate to use when persisting back to the kg.",
    )
    target_id: Optional[str] = Field(
        default=None,
        description="kg node id of the thing this record refers to, if any.",
    )
    payload: dict[str, Any] = Field(default_factory=dict)


class EnrichmentBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    records: list[EnrichmentRecord] = Field(default_factory=list)
    failed_tools: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Notification output  (Notification Agent)
# ---------------------------------------------------------------------------
class Notification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audience: Literal[
        "user", "chw", "agency_analyst", "211_operator", "center_operator", "clinician"
    ]
    channel: Literal["app_push", "sms", "voice", "dashboard_pin", "peer_message"]
    priority: Literal["low", "normal", "high", "critical"] = "normal"
    locale: Literal["en", "es", "nv", "ood"] = "en"
    headline: str
    body: str
    cta_links: list[dict[str, str]] = Field(default_factory=list)

    # SMS-shaped notifications (channel='sms') should be ≤160 chars body
    # to fit a single segment. The Notification Agent sets this flag to
    # True after verifying; the gateway double-checks before sending.
    sms_segment_safe: Optional[bool] = None


SMS_MAX_CHARS = 160


def to_sms_segment(text: str, max_chars: int = SMS_MAX_CHARS) -> str:
    """Truncate text to fit a single SMS segment.

    Trims to ``max_chars - 1`` and appends a Unicode ellipsis when the
    input exceeds the cap. Matches the truncation logic in
    ``agents.sms_adapter`` so any notification can reuse it instead of
    re-implementing.
    """
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


class SmsIntakePayload(BaseModel):
    """Validated payload shape emitted by ``sms-entry-mcp.sms_inbound``.

    The SMS gateway hands one of these to
    :class:`agents.sms_adapter.SmsAdapter.handle_inbound_dataset`. Having
    a typed model here (vs the previous ad-hoc ``dict[str, Any]``) lets
    contracts catch shape drift between the MCP and the agent at the
    boundary.
    """

    model_config = ConfigDict(extra="allow")

    channel: Literal["sms"] = "sms"
    vertical: Vertical
    consent_profile: ConsentProfile = ConsentProfile.ANONYMOUS_HEAT
    general: dict[str, Any] = Field(default_factory=dict)
    exposure: Optional[dict[str, Any]] = None
    human: Optional[dict[str, Any]] = None
    auxiliary: Optional[dict[str, Any]] = None
    environmental: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Cluster detection output  (Cluster Detection Agent)
# ---------------------------------------------------------------------------
class ClusterAlert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cluster_id: str = Field(default_factory=lambda: f"outbreak.{uuid4().hex[:8]}")
    vertical: Vertical
    zcta: Optional[str] = None
    county_id: Optional[str] = None
    observation_ids: list[str]
    window_start: str
    window_end: str
    expected: float
    observed: int
    log_likelihood: float
    deferred_to: str = Field(
        default="ADHS",
        description="Per plan/03 backstop, final declaration is always human.",
    )
    cluster_kind: Literal[
        "spatial", "travel_import_cluster", "endemic_drift", "single_case"
    ] = Field(
        default="spatial",
        description=(
            "What sort of cluster fired. 'spatial' is the default ZCTA-week / "
            "2h Poisson scan (Tier 1/2). 'single_case' is the high-CFR "
            "single-case alert (Tier A). 'travel_import_cluster' is the "
            "travel-imported scatter detector. 'endemic_drift' is the "
            "chronic-baseline drift detector (Tier C)."
        ),
    )

    # ---- Calibrated-detector audit fields (Phase-3 cluster calibration). ----
    # All optional with defaults so legacy callers keep round-tripping.
    tier1_score: Optional[float] = Field(
        default=None,
        description="Tier-1 deterministic O/E ratio that tripped the alert.",
    )
    tier2_posterior: Optional[float] = Field(
        default=None,
        description="Tier-2 Gamma-Poisson posterior P(RR > 1.5 | data).",
    )
    baseline_window_start: Optional[str] = Field(
        default=None,
        description="ISO 8601 start of the trailing baseline window.",
    )
    baseline_window_end: Optional[str] = Field(
        default=None,
        description="ISO 8601 end of the trailing baseline window.",
    )
    rule_tripped: Optional[str] = Field(
        default=None,
        description="Free-text label of the rule that fired "
        "(e.g. 'vbd/zcta-week/theta3.0/k5/posterior0.95').",
    )
    pathogen_hint: Optional[str] = Field(
        default=None,
        description="Best-guess pathogen.* slug from the cluster's observations.",
    )
    historical_match: Optional[str] = Field(
        default=None,
        description="Slug of the closest historical outbreak (within 5 yr & 200 km); "
        "null if no neighbour is close enough.",
    )


# ---------------------------------------------------------------------------
# Per-agent audit trace  (Figure 3 timeliness clock anchor)
#
# Mirrors the columns of ``kg.agent_run`` defined in
# ``schema/deep/audit.sql``. The orchestrator's audit sink projects each
# pipeline step into one of these and the sink writes it to DuckLake (or an
# in-memory DuckDB during tests). The ``status`` Literal is kept for back-
# compat with the existing orchestrator code paths; the audit sink maps it
# to the SQL ``outcome`` enum ('success' / 'degraded' / 'error') at write
# time.
# ---------------------------------------------------------------------------
class AgentRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Identity
    run_id: str = Field(default_factory=lambda: uuid4().hex)
    agent: str
    observation_id: Optional[str] = None

    # Timing
    started_at: str
    finished_at: str
    duration_ms: float

    # Outcome
    status: Literal["ok", "degraded", "failed"]
    error: Optional[str] = None

    # Model + token accounting
    model: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    cache_read_tokens: Optional[int] = None
    cache_creation_tokens: Optional[int] = None
    cost_usd: Optional[float] = None

    # Reproducibility (sha256 of canonical-JSON input/output payloads)
    input_digest: Optional[str] = None
    output_digest: Optional[str] = None


# ---------------------------------------------------------------------------
# The observation node itself
# ---------------------------------------------------------------------------
class Observation(BaseModel):
    """End-to-end record carried through the pipeline.

    Persists as a single ``kg.node(node_type='observation')`` with the
    flat properties from ``dataset`` pivoted into ``kg.property`` rows,
    and ``triage`` / ``enrichments`` / ``cluster_alerts`` materialised as
    outbound edges (``gradedAs``, ``enrichedWith``, ``partOfCluster``).
    """

    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(default_factory=lambda: f"observation.{uuid4().hex}")
    kind: Kind = Kind.REPORT
    vertical: Vertical = Vertical.NEITHER
    source: Channel = Channel.MOBILE
    received_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    consent_profile: ConsentProfile = ConsentProfile.FULL_FOLLOWUP

    dataset: MinimumDataset = Field(default_factory=MinimumDataset)
    geo: Optional[GeoEnrichment] = None
    validation: Optional[ValidationReport] = None
    triage: Optional[TriageDecision] = None
    enrichments: EnrichmentBundle = Field(default_factory=EnrichmentBundle)
    notifications: list[Notification] = Field(default_factory=list)
    cluster_alerts: list[ClusterAlert] = Field(default_factory=list)

    validation_status: Optional[ValidationStatus] = None
    agent_runs: list[AgentRun] = Field(default_factory=list)


__all__ = [
    # Enums
    "Vertical",
    "Kind",
    "Channel",
    "ConsentProfile",
    "TriageClass",
    "VBD_TRIAGE_CLASSES",
    "HEAT_TRIAGE_CLASSES",
    "ValidationStatus",
    "HeatRisk",
    # Parameter classes
    "GeneralClass",
    "HumanClass",
    "SeverityClass",
    "ExposureClass",
    "AuxiliaryClass",
    "EnvironmentalClass",
    "LivestockClass",
    "WildlifeClass",
    "MinimumDataset",
    # Agent outputs
    "GeoEnrichment",
    "ValidationReport",
    "HeatVulnerabilityComponent",
    "HeatVulnerabilityScore",
    "CandidatePathogen",
    "TriageDecision",
    "EnrichmentRecord",
    "EnrichmentBundle",
    "Notification",
    "ClusterAlert",
    "AgentRun",
    "Observation",
]
