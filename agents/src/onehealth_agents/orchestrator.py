"""Orchestrator -- wires the eight agents end-to-end.

Contract:

    Orchestrator.process(raw) -> Observation

The returned :class:`Observation` has its ``triage``, ``enrichments``,
``notifications``, and ``validation_status`` slots populated, plus a
per-agent :class:`AgentRun` audit trace in ``agent_runs`` so the
Figure-3 timeliness clock has a place to anchor.

Each stage runs inside a ``try``/``except`` boundary. A failing agent
degrades to ``AgentRun.status='failed'`` plus a flag on the
observation; it never drops the whole report.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, TypeVar

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


class Orchestrator:
    """End-to-end pipeline driver.

    The orchestrator constructs each agent once and reuses them; an
    explicit ``MCPClient`` may be passed (defaulting to
    :class:`FakeMCPClient` with its canned scenario handlers).
    """

    def __init__(self, mcp: MCPClient | None = None) -> None:
        self.mcp: MCPClient = mcp or FakeMCPClient.with_default_handlers()
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
        # 1. Intake
        observation = await self._run(
            "intake", lambda: self._maybe_async(self.intake.run, raw_input)
        )
        if observation is None:
            # Synthesise an empty observation so the pipeline keeps a record.
            observation = Observation()
            observation.agent_runs.append(
                AgentRun(
                    agent="intake",
                    started_at=_now(),
                    finished_at=_now(),
                    duration_ms=0.0,
                    status="failed",
                    error="intake returned None",
                )
            )

        # 2. Geo enrichment
        geo = await self._run_on(
            observation, "geo_enrichment", lambda: self.geo.run(observation)
        )
        if geo is not None:
            observation.geo = geo

        # 3. Validation
        validation = await self._run_on(
            observation, "validation", lambda: self._sync(self.validation.run, observation)
        )
        if validation is not None:
            observation.validation = validation
            observation.validation_status = validation.status

        # If validation rejected, stop early.
        if observation.validation_status == ValidationStatus.REJECT:
            return observation

        # 4. Triage
        triage = await self._run_on(
            observation, "triage", lambda: self._sync(self.triage.run, observation)
        )
        if triage is not None:
            observation.triage = triage
            if observation.vertical == Vertical.NEITHER:
                observation.vertical = triage.vertical

        # 5. Enrichment
        bundle = await self._run_on(
            observation,
            "enrichment",
            lambda: self.enrichment.run(observation),
        )
        if bundle is not None:
            observation.enrichments = bundle
        elif not isinstance(observation.enrichments, EnrichmentBundle):
            observation.enrichments = EnrichmentBundle()

        # 6. Notification
        notes = await self._run_on(
            observation,
            "notification",
            lambda: self._sync(self.notification.run, observation),
        )
        if notes is not None:
            observation.notifications = notes

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
        out, run = await self._timed(name, fn)
        observation.agent_runs.append(run)
        return out

    @staticmethod
    async def _timed(
        name: str, fn: Callable[[], Awaitable[T] | T]
    ) -> tuple[T | None, AgentRun]:
        started = datetime.now(timezone.utc)
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
            )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = ["Orchestrator"]
