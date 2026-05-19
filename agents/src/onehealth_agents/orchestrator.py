"""Orchestrator -- wires the eight agents end-to-end.

Contract:

    Orchestrator.process(raw) -> Observation

The returned :class:`Observation` has its ``triage``, ``enrichments``,
``notifications``, and ``validation_status`` slots populated, plus a
per-agent :class:`AgentRun` audit trace in ``agent_runs`` so the
Figure-3 timeliness clock has a place to anchor.

Every per-agent :class:`AgentRun` is also handed to an
:class:`AuditSink` (default: :class:`InMemoryAuditSink`) so a DuckLake
deployment can persist the rows into ``kg.agent_run`` -- see
``schema/deep/audit.sql`` -- without the orchestrator having to know
how the storage is wired.

Each stage runs inside a ``try``/``except`` boundary. A failing agent
degrades to ``AgentRun.status='failed'`` plus a flag on the
observation; it never drops the whole report.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, TypeVar

from .audit import AuditSink, InMemoryAuditSink, cost_for_run, hash_for_audit
from .cluster import ClusterDetectionAgent
from .contracts import (
    AgentRun,
    EnrichmentBundle,
    Observation,
    Vertical,
    ValidationStatus,
)
from .enrichment import EnrichmentAgent
from .geo import GeoEnrichmentAgent
from .intake import IntakeAgent
from .mcp_client import FakeMCPClient, MCPClient
from .notification import NotificationAgent
from .triage import TriageAgent
from .update import KnowledgeUpdateAgent
from .validation import ValidationAgent


T = TypeVar("T")


# Per-agent default model assignment. Mirrors the cost-shaping policy
# from plan/03 + plan/05: Haiku on high-volume, Sonnet on the rule-gated
# triage step, Opus only where stakes are highest. Used to populate the
# ``model_id`` column of ``kg.agent_run`` when the agent itself does not
# report which model it used.
_DEFAULT_MODEL_FOR_AGENT: dict[str, str] = {
    "intake": "claude-haiku-4-5",
    "geo_enrichment": "claude-haiku-4-5",
    "validation": "claude-haiku-4-5",
    "triage": "claude-sonnet-4-6",
    "enrichment": "claude-sonnet-4-6",
    "notification": "claude-haiku-4-5",
    "cluster_detection": "claude-opus-4-7",
    "knowledge_update": "claude-haiku-4-5",
}


class Orchestrator:
    """End-to-end pipeline driver.

    The orchestrator constructs each agent once and reuses them; an
    explicit ``MCPClient`` may be passed (defaulting to
    :class:`FakeMCPClient` with its canned scenario handlers).
    """

    def __init__(
        self,
        mcp: MCPClient | None = None,
        audit_sink: AuditSink | None = None,
    ) -> None:
        self.mcp: MCPClient = mcp or FakeMCPClient.with_default_handlers()
        # NB: don't use ``or`` here -- an empty InMemoryAuditSink is falsy
        # because ``__len__`` returns 0 on a fresh instance.
        self.audit_sink: AuditSink = (
            audit_sink if audit_sink is not None else InMemoryAuditSink()
        )
        self.intake = IntakeAgent()
        self.geo = GeoEnrichmentAgent(self.mcp)
        self.validation = ValidationAgent()
        self.triage = TriageAgent()
        self.enrichment = EnrichmentAgent(self.mcp)
        self.notification = NotificationAgent()
        self.cluster = ClusterDetectionAgent()
        self.knowledge_update = KnowledgeUpdateAgent(self.mcp)

    # ------------------------------------------------------------------
    async def process(self, raw_input: dict | str) -> Observation:
        # 1. Intake -- digest the raw payload so the audit row anchors a
        #    reproducible input.
        intake_input_digest = hash_for_audit(raw_input)
        observation, intake_run = await self._timed(
            "intake",
            lambda: self._maybe_async(self.intake.run, raw_input),
            input_digest=intake_input_digest,
        )
        if observation is None:
            # Synthesise an empty observation so the pipeline keeps a record.
            observation = Observation()
            intake_run = intake_run.model_copy(
                update={
                    "status": "failed",
                    "error": intake_run.error or "intake returned None",
                    "observation_id": observation.observation_id,
                }
            )
        # Stamp the observation_id + output digest now that we have the obs.
        intake_run = self._finalize_run(intake_run, observation, observation)
        self._publish(observation, intake_run)

        # 2. Geo enrichment
        geo, geo_run = await self._timed(
            "geo_enrichment",
            lambda: self.geo.run(observation),
            input_digest=hash_for_audit(observation),
        )
        if geo is not None:
            observation.geo = geo
        geo_run = self._finalize_run(geo_run, observation, geo)
        self._publish(observation, geo_run)

        # 3. Validation
        validation, validation_run = await self._timed(
            "validation",
            lambda: self._sync(self.validation.run, observation),
            input_digest=hash_for_audit(observation),
        )
        if validation is not None:
            observation.validation = validation
            observation.validation_status = validation.status
        validation_run = self._finalize_run(validation_run, observation, validation)
        self._publish(observation, validation_run)

        # If validation rejected, stop early.
        if observation.validation_status == ValidationStatus.REJECT:
            return observation

        # 4. Triage
        triage, triage_run = await self._timed(
            "triage",
            lambda: self._sync(self.triage.run, observation),
            input_digest=hash_for_audit(observation),
        )
        if triage is not None:
            observation.triage = triage
            if observation.vertical == Vertical.NEITHER:
                observation.vertical = triage.vertical
        triage_run = self._finalize_run(triage_run, observation, triage)
        self._publish(observation, triage_run)

        # 5. Enrichment
        bundle, enrichment_run = await self._timed(
            "enrichment",
            lambda: self.enrichment.run(observation),
            input_digest=hash_for_audit(observation),
        )
        if bundle is not None:
            observation.enrichments = bundle
        elif not isinstance(observation.enrichments, EnrichmentBundle):
            observation.enrichments = EnrichmentBundle()
        enrichment_run = self._finalize_run(enrichment_run, observation, bundle)
        self._publish(observation, enrichment_run)

        # 6. Notification
        notes, notification_run = await self._timed(
            "notification",
            lambda: self._sync(self.notification.run, observation),
            input_digest=hash_for_audit(observation),
        )
        if notes is not None:
            observation.notifications = notes
        notification_run = self._finalize_run(notification_run, observation, notes)
        self._publish(observation, notification_run)

        return observation

    # ------------------------------------------------------------------
    async def detect_clusters(
        self, observations: list[Observation]
    ) -> list:
        """Run the Cluster Detection Agent over a buffered observation list."""
        return await self._sync(self.cluster.run, observations)

    async def refresh_from_mcp(self, servers: list[str]) -> list[Observation]:
        """Run the Knowledge Update Agent against the supplied servers."""
        return await self.knowledge_update.run(servers)

    # ------------------------------------------------------------------
    @staticmethod
    async def _maybe_async(fn: Callable[..., Any], *args: Any) -> Any:
        result = fn(*args)
        if asyncio.iscoroutine(result):
            return await result
        return result

    @staticmethod
    async def _sync(fn: Callable[..., T], *args: Any) -> T:
        return fn(*args)

    async def _run(
        self, name: str, fn: Callable[[], Awaitable[T] | T]
    ) -> T | None:
        """Run ``fn`` and discard the AgentRun (used only for the bootstrap intake)."""
        out, _ = await self._timed(name, fn)
        return out

    async def _run_on(
        self, observation: Observation, name: str, fn: Callable[[], Awaitable[T] | T]
    ) -> T | None:
        """Run ``fn``, record the resulting :class:`AgentRun` on the observation."""
        out, run = await self._timed(name, fn, input_digest=hash_for_audit(observation))
        run = self._finalize_run(run, observation, out)
        self._publish(observation, run)
        return out

    @staticmethod
    async def _timed(
        name: str,
        fn: Callable[[], Awaitable[T] | T],
        *,
        input_digest: str | None = None,
    ) -> tuple[T | None, AgentRun]:
        started = datetime.now(timezone.utc)
        model_id = _DEFAULT_MODEL_FOR_AGENT.get(name)
        try:
            value = fn()
            if asyncio.iscoroutine(value):
                value = await value
            ended = datetime.now(timezone.utc)
            return value, AgentRun(
                agent=name,
                started_at=started.isoformat(),
                finished_at=ended.isoformat(),
                duration_ms=(ended - started).total_seconds() * 1000.0,
                status="ok",
                model=model_id,
                input_digest=input_digest,
            )
        except Exception as exc:  # noqa: BLE001 -- isolation per plan/03
            ended = datetime.now(timezone.utc)
            return None, AgentRun(
                agent=name,
                started_at=started.isoformat(),
                finished_at=ended.isoformat(),
                duration_ms=(ended - started).total_seconds() * 1000.0,
                status="failed",
                error=f"{type(exc).__name__}: {exc}",
                model=model_id,
                input_digest=input_digest,
            )

    @staticmethod
    def _finalize_run(
        run: AgentRun,
        observation: Observation,
        output: Any,
    ) -> AgentRun:
        """Stamp ``observation_id`` + ``output_digest`` + ``cost_usd`` on a run."""
        update: dict[str, Any] = {"observation_id": observation.observation_id}
        if output is not None:
            update["output_digest"] = hash_for_audit(output)
        # Cost is currently driven by env-var token counts (zero unless the
        # agent reported them); the call is still cheap because the pricing
        # table short-circuits on missing model_id / token counts.
        update["cost_usd"] = cost_for_run(
            run.model,
            run.prompt_tokens,
            run.completion_tokens,
            run.cache_read_tokens,
            run.cache_creation_tokens,
        )
        return run.model_copy(update=update)

    def _publish(self, observation: Observation, run: AgentRun) -> None:
        """Attach ``run`` to the observation and forward to the audit sink."""
        observation.agent_runs.append(run)
        try:
            self.audit_sink.record(run)
        except Exception:  # noqa: BLE001 -- audit must never break the pipeline
            # The sink is best-effort: in the worst case we still have the
            # in-memory ``observation.agent_runs`` trace.
            pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = ["Orchestrator"]
