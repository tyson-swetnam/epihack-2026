"""Audit-sink plumbing for the eight-agent pipeline.

Every call into an agent ends with an :class:`AgentRun`. The orchestrator
hands that run to an :class:`AuditSink` which is responsible for writing
it somewhere durable (DuckLake in production, an in-memory list in
tests). The contract is intentionally narrow -- ``record(run)`` is the
only required method -- so a test harness can substitute a list and
production can substitute a writer that issues parameterised INSERTs
into ``kg.agent_run`` (see ``schema/deep/audit.sql``).

This module also pins the Claude pricing table the orchestrator uses to
fill the ``cost_usd`` column. The constants below are the published
dollars-per-million-tokens at the time of writing for the three Claude
models the pipeline calls in production:

================ ============= ============== =============== ==================
Model            input ($/Mt)  output ($/Mt)  cache_read     cache_creation
================ ============= ============== =============== ==================
Haiku 4.5        $1.00         $5.00          $0.10           $1.25
Sonnet 4.6       $3.00         $15.00         $0.30           $3.75
Opus 4.7         $15.00        $75.00         $1.50           $18.75
================ ============= ============== =============== ==================

Every constant is overridable via an environment variable (e.g.
``CLAUDE_HAIKU_INPUT_USD_PER_M``) so the deployment can adjust without a
code change when Anthropic updates the public rate card.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from .contracts import AgentRun


# ---------------------------------------------------------------------------
# Hashing helper
# ---------------------------------------------------------------------------
def _canonical_json(obj: Any) -> str:
    """Stable, sorted JSON encoding suitable for hashing."""
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
        ensure_ascii=False,
    )


def _json_default(value: Any) -> Any:
    """Fallback encoder for objects ``json`` does not handle natively."""
    # Pydantic v2 models expose model_dump.
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        return dump(mode="json")
    # Anything with __dict__ falls back to its dict; tuples to list; sets sorted.
    if isinstance(value, (set, frozenset)):
        return sorted(value, key=str)
    if isinstance(value, tuple):
        return list(value)
    if hasattr(value, "__dict__"):
        return value.__dict__
    return str(value)


def hash_for_audit(obj: Any) -> str:
    """Return the sha256 hex digest of ``obj`` after canonical-JSON encoding."""
    encoded = _canonical_json(obj).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


# ---------------------------------------------------------------------------
# Pricing table (dollars per million tokens). Env-var overrides honoured.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _Pricing:
    input_usd_per_m: float
    output_usd_per_m: float
    cache_read_usd_per_m: float
    cache_creation_usd_per_m: float


_DEFAULT_PRICING: dict[str, _Pricing] = {
    "claude-haiku-4-5": _Pricing(
        input_usd_per_m=1.00,
        output_usd_per_m=5.00,
        cache_read_usd_per_m=0.10,
        cache_creation_usd_per_m=1.25,
    ),
    "claude-sonnet-4-6": _Pricing(
        input_usd_per_m=3.00,
        output_usd_per_m=15.00,
        cache_read_usd_per_m=0.30,
        cache_creation_usd_per_m=3.75,
    ),
    "claude-opus-4-7": _Pricing(
        input_usd_per_m=15.00,
        output_usd_per_m=75.00,
        cache_read_usd_per_m=1.50,
        cache_creation_usd_per_m=18.75,
    ),
}


def _env_override(env_var: str, fallback: float) -> float:
    raw = os.environ.get(env_var)
    if raw is None or raw == "":
        return fallback
    try:
        return float(raw)
    except ValueError:
        return fallback


def _pricing_for(model_id: str) -> _Pricing | None:
    base = _DEFAULT_PRICING.get(model_id)
    if base is None:
        return None
    # Map model_id -> env-var infix (HAIKU, SONNET, OPUS).
    infix = {
        "claude-haiku-4-5": "HAIKU",
        "claude-sonnet-4-6": "SONNET",
        "claude-opus-4-7": "OPUS",
    }[model_id]
    return _Pricing(
        input_usd_per_m=_env_override(
            f"CLAUDE_{infix}_INPUT_USD_PER_M", base.input_usd_per_m
        ),
        output_usd_per_m=_env_override(
            f"CLAUDE_{infix}_OUTPUT_USD_PER_M", base.output_usd_per_m
        ),
        cache_read_usd_per_m=_env_override(
            f"CLAUDE_{infix}_CACHE_READ_USD_PER_M", base.cache_read_usd_per_m
        ),
        cache_creation_usd_per_m=_env_override(
            f"CLAUDE_{infix}_CACHE_CREATION_USD_PER_M", base.cache_creation_usd_per_m
        ),
    )


def cost_for_run(
    model_id: str | None,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    cache_read_tokens: int | None = None,
    cache_creation_tokens: int | None = None,
) -> float:
    """Compute cost in USD for a single agent invocation.

    Unknown model IDs and missing token counts collapse to a zero
    contribution rather than raising -- the audit log should never crash
    the pipeline.
    """
    if not model_id:
        return 0.0
    pricing = _pricing_for(model_id)
    if pricing is None:
        return 0.0
    prompt = prompt_tokens or 0
    completion = completion_tokens or 0
    cache_read = cache_read_tokens or 0
    cache_creation = cache_creation_tokens or 0
    return round(
        (
            prompt * pricing.input_usd_per_m
            + completion * pricing.output_usd_per_m
            + cache_read * pricing.cache_read_usd_per_m
            + cache_creation * pricing.cache_creation_usd_per_m
        )
        / 1_000_000.0,
        8,
    )


# ---------------------------------------------------------------------------
# Outcome mapping (pydantic ``status`` -> SQL ``outcome``)
# ---------------------------------------------------------------------------
_STATUS_TO_OUTCOME = {
    "ok": "success",
    "degraded": "degraded",
    "failed": "error",
}


def _outcome_for(run: AgentRun) -> str:
    return _STATUS_TO_OUTCOME.get(run.status, "error")


# ---------------------------------------------------------------------------
# Sink protocol + implementations
# ---------------------------------------------------------------------------
@runtime_checkable
class AuditSink(Protocol):
    """Anything that knows how to durably record an :class:`AgentRun`."""

    def record(self, run: AgentRun) -> None:  # pragma: no cover - protocol
        ...


class InMemoryAuditSink:
    """List-backed sink. Default for tests + the orchestrator's no-config path."""

    def __init__(self) -> None:
        self.runs: list[AgentRun] = []
        self._lock = threading.Lock()

    def record(self, run: AgentRun) -> None:
        with self._lock:
            self.runs.append(run)

    # Test conveniences -------------------------------------------------------
    def __len__(self) -> int:
        return len(self.runs)

    def __iter__(self):
        return iter(self.runs)

    def by_agent(self, agent: str) -> list[AgentRun]:
        return [r for r in self.runs if r.agent == agent]

    def clear(self) -> None:
        with self._lock:
            self.runs.clear()


# ---------------------------------------------------------------------------
# DuckLake (DuckDB) sink
# ---------------------------------------------------------------------------
_INSERT_SQL = """
INSERT INTO kg.agent_run (
    run_id, agent_name, observation_id,
    started_at, ended_at, duration_ms,
    model_id,
    prompt_tokens, completion_tokens,
    cache_read_tokens, cache_creation_tokens,
    cost_usd,
    outcome,
    input_digest, output_digest,
    error_message,
    source_fig
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT DO NOTHING
""".strip()


class DuckLakeAuditSink:
    """Persists :class:`AgentRun` rows into ``kg.agent_run``.

    Connects to DuckLake when ``KG_DUCKLAKE_URI`` is set; otherwise opens an
    in-memory DuckDB connection (useful in tests + Phase-0 demos that don't
    have a Postgres catalog yet).
    """

    def __init__(
        self,
        connection: Any | None = None,
        ducklake_uri: str | None = None,
        source_fig: str = "agent-runtime",
    ) -> None:
        # Late import so ``onehealth_agents`` stays importable without duckdb
        # at install-time (production environments will always have it).
        if connection is None:
            try:
                import duckdb  # type: ignore[import-not-found]
            except ImportError as exc:  # pragma: no cover - install error
                raise ImportError(
                    "DuckLakeAuditSink requires the 'duckdb' package. "
                    "Install with `pip install duckdb`."
                ) from exc

            uri = ducklake_uri or os.environ.get("KG_DUCKLAKE_URI")
            if uri:
                connection = duckdb.connect(uri)
            else:
                connection = duckdb.connect(":memory:")

        self._con = connection
        self._lock = threading.Lock()
        self._source_fig = source_fig

    # ---- internal helpers ---------------------------------------------------
    @staticmethod
    def _row_for(run: AgentRun, source_fig: str) -> tuple:
        return (
            run.run_id,
            run.agent,
            run.observation_id,
            run.started_at,
            run.finished_at,
            run.duration_ms,
            run.model,
            run.prompt_tokens,
            run.completion_tokens,
            run.cache_read_tokens,
            run.cache_creation_tokens,
            run.cost_usd,
            _outcome_for(run),
            run.input_digest,
            run.output_digest,
            run.error,
            source_fig,
        )

    # ---- public API ---------------------------------------------------------
    def record(self, run: AgentRun) -> None:
        row = self._row_for(run, self._source_fig)
        with self._lock:
            self._con.execute(_INSERT_SQL, row)

    @property
    def connection(self) -> Any:
        """Underlying DuckDB / DuckLake connection (for tests + ad-hoc queries)."""
        return self._con


# ---------------------------------------------------------------------------
# Tiny in-process SQLite-backed sink. Exists for environments that can't ship
# DuckDB (e.g. some CI minimal images) but still want a parameterised-INSERT
# audit trail you can SELECT against. Schema mirrors ``kg.agent_run``.
# ---------------------------------------------------------------------------
class SqliteAuditSink:
    """Optional minimal-dependency sink; mirrors the DuckLake column shape."""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS agent_run (
        run_id TEXT PRIMARY KEY,
        agent_name TEXT NOT NULL,
        observation_id TEXT,
        started_at TEXT NOT NULL,
        ended_at TEXT,
        duration_ms REAL,
        model_id TEXT,
        prompt_tokens INTEGER,
        completion_tokens INTEGER,
        cache_read_tokens INTEGER,
        cache_creation_tokens INTEGER,
        cost_usd REAL,
        outcome TEXT,
        input_digest TEXT,
        output_digest TEXT,
        error_message TEXT,
        source_fig TEXT DEFAULT 'agent-runtime'
    )
    """

    def __init__(self, path: str = ":memory:") -> None:
        self._con = sqlite3.connect(path)
        self._con.execute(self.SCHEMA)
        self._lock = threading.Lock()

    def record(self, run: AgentRun) -> None:
        with self._lock:
            self._con.execute(
                """
                INSERT OR IGNORE INTO agent_run (
                    run_id, agent_name, observation_id,
                    started_at, ended_at, duration_ms,
                    model_id,
                    prompt_tokens, completion_tokens,
                    cache_read_tokens, cache_creation_tokens,
                    cost_usd, outcome,
                    input_digest, output_digest,
                    error_message, source_fig
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.run_id,
                    run.agent,
                    run.observation_id,
                    run.started_at,
                    run.finished_at,
                    run.duration_ms,
                    run.model,
                    run.prompt_tokens,
                    run.completion_tokens,
                    run.cache_read_tokens,
                    run.cache_creation_tokens,
                    run.cost_usd,
                    _outcome_for(run),
                    run.input_digest,
                    run.output_digest,
                    run.error,
                    "agent-runtime",
                ),
            )
            self._con.commit()

    @property
    def connection(self) -> sqlite3.Connection:
        return self._con


__all__ = [
    "AuditSink",
    "InMemoryAuditSink",
    "DuckLakeAuditSink",
    "SqliteAuditSink",
    "hash_for_audit",
    "cost_for_run",
]
