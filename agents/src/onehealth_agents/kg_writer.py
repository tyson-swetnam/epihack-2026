"""Persist inbound reports into the DuckLake knowledge graph.

This is the Phase-06.2 intake write-path, scoped to durable *logging* of
every user submission. It deliberately does **not** run the LLM agent chain
(that needs an Anthropic key and lands later); it records the structured
observation so no report is ever silently dropped, and so DuckLake's
time-travel versioning captures the full history of submissions.

Privacy contract (CONTRIBUTING.md / plan/06):
  * Location is already coarse on the wire (``CoarseLocation`` = zip or 1 km
    grid only); we persist it as-is — there is nothing finer to re-coarsen.
  * Free-text ``notes`` may carry PII, so we store **only a SHA-256 digest**,
    never the raw string. Structured fields are enums / coarse values.
  * The ``claim_token`` is the bearer secret a client uses to read status;
    we store only its SHA-256 digest so a catalog leak can't replay it.
  * The audit row in ``kg.agent_run`` carries digests, never raw payloads.

When ``KG_DUCKLAKE_URI`` is unset the writer degrades to an in-memory DuckDB
with a minimal schema, so the API still works in tests/dev (nothing persists
across restarts in that mode).
"""
from __future__ import annotations

import hashlib
import os
import threading
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from .audit import hash_for_audit

# Minimal schema for the in-memory fallback (DuckLake mode already has these).
_FALLBACK_SCHEMA = """
CREATE SCHEMA IF NOT EXISTS kg;
CREATE TABLE IF NOT EXISTS kg.node (
    node_id VARCHAR PRIMARY KEY, node_type VARCHAR NOT NULL, label VARCHAR NOT NULL,
    description VARCHAR, source_fig VARCHAR, created_at TIMESTAMP DEFAULT current_timestamp
);
CREATE TABLE IF NOT EXISTS kg.property (
    node_id VARCHAR NOT NULL, key VARCHAR NOT NULL,
    value_text VARCHAR, value_num DOUBLE, PRIMARY KEY (node_id, key)
);
CREATE TABLE IF NOT EXISTS kg.agent_run (
    run_id VARCHAR PRIMARY KEY, agent_name VARCHAR, observation_id VARCHAR,
    started_at TIMESTAMP, ended_at TIMESTAMP, duration_ms DOUBLE, model_id VARCHAR,
    prompt_tokens BIGINT, completion_tokens BIGINT, cache_read_tokens BIGINT,
    cache_creation_tokens BIGINT, cost_usd DOUBLE, outcome VARCHAR,
    input_digest VARCHAR, output_digest VARCHAR, error_message VARCHAR, source_fig VARCHAR
);
"""

_AGENT_RUN_INSERT = """
INSERT INTO kg.agent_run (
    run_id, agent_name, observation_id, started_at, ended_at, duration_ms,
    model_id, prompt_tokens, completion_tokens, cache_read_tokens,
    cache_creation_tokens, cost_usd, outcome, input_digest, output_digest,
    error_message, source_fig
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""".strip()
# NB: no ON CONFLICT — DuckLake tables carry no PK/UNIQUE constraint, and
# every row uses a freshly minted UUID so there is nothing to conflict on.


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class KgWriter:
    """Thread-safe writer for intake observations + audit rows into DuckLake."""

    def __init__(self, connection: Any | None = None, ducklake_uri: str | None = None):
        self._lock = threading.Lock()
        self.persistent = False
        if connection is not None:
            self._con = connection
            self.persistent = True
            return

        import duckdb  # late import; always present in production

        uri = ducklake_uri or os.environ.get("KG_DUCKLAKE_URI")
        if uri:
            con = duckdb.connect(":memory:")
            for ext in ("ducklake", "postgres"):
                try:
                    con.execute(f"INSTALL {ext}; LOAD {ext};")
                except Exception:  # noqa: BLE001 - may be statically linked
                    pass
            attach_opts = ""
            data_path = os.environ.get("KG_DUCKLAKE_DATA_PATH")
            if data_path:
                attach_opts = f" (DATA_PATH '{data_path.replace(chr(39), chr(39) * 2)}')"
            con.execute(f"ATTACH '{uri.replace(chr(39), chr(39) * 2)}' AS epihack{attach_opts};")
            con.execute("USE epihack;")
            self._con = con
            self.persistent = True
        else:
            con = duckdb.connect(":memory:")
            con.execute(_FALLBACK_SCHEMA)
            self._con = con

    def persist_observation(
        self,
        payload: Any,
        user_id: Optional[str] = None,
    ) -> tuple[str, str]:
        """Write one observation node + properties + intake audit row.

        Returns ``(observation_id, claim_token)``. The plaintext claim_token is
        returned to the caller exactly once; only its digest is stored.
        """
        observation_id = str(uuid4())
        claim_token = uuid4().hex
        now = datetime.now(timezone.utc)

        loc = payload.coarse_location
        # (key, value_text, value_num) triples — value_text for strings/enums,
        # value_num for ordinals/counts.
        props: list[tuple[str, Optional[str], Optional[float]]] = [
            ("report_type", str(payload.report_type), None),
            ("event_class", str(payload.event_class), None),
            ("coarse_zip", loc.zip, None),
            ("coarse_grid_id", loc.grid_id, None),
            ("event_date", str(payload.event_date) if payload.event_date else None, None),
            ("severity", payload.severity, None),
            ("count", None, float(payload.count) if payload.count is not None else None),
            ("species", payload.species, None),
            (
                "symptoms",
                ",".join(str(s) for s in payload.symptoms) if payload.symptoms else None,
                None,
            ),
            # Free text is logged only as a digest — never the raw string.
            ("notes_sha256", _sha256(payload.notes) if payload.notes else None, None),
            ("claim_token_sha256", _sha256(claim_token), None),
            ("attached_user_id", user_id, None),
            ("intake_at", now.isoformat(), None),
        ]
        props = [(k, t, n) for (k, t, n) in props if t is not None or n is not None]

        input_digest = hash_for_audit(payload.model_dump(mode="json"))
        output_digest = hash_for_audit({"observation_id": observation_id})

        with self._lock:
            self._con.execute("BEGIN TRANSACTION;")
            try:
                self._con.execute(
                    "INSERT INTO kg.node (node_id, node_type, label, description, "
                    "source_fig, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        observation_id,
                        "observation",
                        f"{payload.report_type} report",
                        None,
                        "app-intake",
                        now,
                    ),
                )
                for key, vtext, vnum in props:
                    self._con.execute(
                        "INSERT INTO kg.property (node_id, key, value_text, value_num) "
                        "VALUES (?, ?, ?, ?)",
                        (observation_id, key, vtext, vnum),
                    )
                self._con.execute(
                    _AGENT_RUN_INSERT,
                    (
                        str(uuid4()),
                        "intake",
                        observation_id,
                        now,
                        datetime.now(timezone.utc),
                        0.0,
                        None,
                        None,
                        None,
                        None,
                        None,
                        0.0,
                        "success",
                        input_digest,
                        output_digest,
                        None,
                        "app-intake",
                    ),
                )
                self._con.execute("COMMIT;")
            except Exception:
                self._con.execute("ROLLBACK;")
                raise
        return observation_id, claim_token

    def read_status(self, observation_id: str, claim_token: str) -> Optional[str]:
        """Return the observation's state if the claim_token matches.

        * ``None``                -> no such observation.
        * raises ``PermissionError`` -> exists but the token doesn't match.
        Token comparison is digest-vs-digest (we never stored the plaintext).
        """
        with self._lock:
            row = self._con.execute(
                "SELECT value_text FROM kg.property "
                "WHERE node_id = ? AND key = 'claim_token_sha256'",
                (observation_id,),
            ).fetchone()
        if row is None:
            return None
        if row[0] != _sha256(claim_token):
            raise PermissionError("claim_token mismatch")
        return "received"

    @property
    def connection(self) -> Any:
        return self._con


# Lazy module-level singleton — built on first use, reused for the process.
_writer: Optional[KgWriter] = None
_writer_lock = threading.Lock()


def get_writer() -> KgWriter:
    global _writer
    if _writer is None:
        with _writer_lock:
            if _writer is None:
                _writer = KgWriter()
    return _writer
