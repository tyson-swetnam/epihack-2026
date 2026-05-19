"""EpiHack Arizona 2026 -- OneHealth eight-agent pipeline package.

See ``plan/03-agentic-architecture.md`` for the design and
``plan/04-data-flows.md`` for the worked end-to-end scenarios.
"""

from __future__ import annotations

from .audit import (
    AuditSink,
    DuckLakeAuditSink,
    InMemoryAuditSink,
    SqliteAuditSink,
    cost_for_run,
    hash_for_audit,
)
from .cluster import ClusterDetectionAgent
from .contracts import (  # noqa: F401  (re-exported for convenience)
    AgentRun,
    AuxiliaryClass,
    CandidatePathogen,
    Channel,
    ClusterAlert,
    ConsentProfile,
    EnrichmentBundle,
    EnrichmentRecord,
    EnvironmentalClass,
    ExposureClass,
    GeneralClass,
    GeoEnrichment,
    HEAT_TRIAGE_CLASSES,
    HeatRisk,
    HeatVulnerabilityComponent,
    HeatVulnerabilityScore,
    HumanClass,
    Kind,
    LivestockClass,
    MinimumDataset,
    Notification,
    Observation,
    SMS_MAX_CHARS as CONTRACTS_SMS_MAX_CHARS,
    SeverityClass,
    SmsIntakePayload,
    TriageClass,
    TriageDecision,
    VBD_TRIAGE_CLASSES,
    ValidationReport,
    ValidationStatus,
    Vertical,
    WildlifeClass,
    to_sms_segment,
)
from .enrichment import EnrichmentAgent
from .geo import GeoEnrichmentAgent
from .intake import IntakeAgent
from .mcp_client import FakeMCPClient, MCPClient, StdioMCPClient
from .notification import NotificationAgent
from .orchestrator import Orchestrator
from .sms_adapter import SMS_MAX_CHARS, SmsAdapter, SmsReply
from .triage import HEAT_SCORE_TABLE, HeatTriage, TriageAgent, VBDTriage
from .update import KnowledgeUpdateAgent
from .validation import ValidationAgent

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # Orchestrator
    "Orchestrator",
    # Audit
    "AuditSink",
    "InMemoryAuditSink",
    "DuckLakeAuditSink",
    "SqliteAuditSink",
    "hash_for_audit",
    "cost_for_run",
    # Agents
    "IntakeAgent",
    "GeoEnrichmentAgent",
    "ValidationAgent",
    "TriageAgent",
    "HeatTriage",
    "VBDTriage",
    "EnrichmentAgent",
    "NotificationAgent",
    "ClusterDetectionAgent",
    "KnowledgeUpdateAgent",
    "HEAT_SCORE_TABLE",
    # SMS adapter + shared SMS helpers
    "SmsAdapter",
    "SmsReply",
    "SMS_MAX_CHARS",
    "SmsIntakePayload",
    "to_sms_segment",
    # MCP
    "MCPClient",
    "FakeMCPClient",
    "StdioMCPClient",
    # Contracts
    "AgentRun",
    "AuxiliaryClass",
    "CandidatePathogen",
    "Channel",
    "ClusterAlert",
    "ConsentProfile",
    "EnrichmentBundle",
    "EnrichmentRecord",
    "EnvironmentalClass",
    "ExposureClass",
    "GeneralClass",
    "GeoEnrichment",
    "HEAT_TRIAGE_CLASSES",
    "HeatRisk",
    "HeatVulnerabilityComponent",
    "HeatVulnerabilityScore",
    "HumanClass",
    "Kind",
    "LivestockClass",
    "MinimumDataset",
    "Notification",
    "Observation",
    "SeverityClass",
    "TriageClass",
    "TriageDecision",
    "VBD_TRIAGE_CLASSES",
    "ValidationReport",
    "ValidationStatus",
    "Vertical",
    "WildlifeClass",
]
