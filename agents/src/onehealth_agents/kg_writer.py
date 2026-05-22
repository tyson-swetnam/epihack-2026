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
        has_photo: bool = False,
    ) -> tuple[str, str]:
        """Write one observation node + properties + intake audit row.

        Returns ``(observation_id, claim_token)``. The plaintext claim_token is
        returned to the caller exactly once; only its digest is stored.
        ``has_photo`` records whether a (stripped) photo accompanied the
        report, so the personal dashboard can offer view / remove.
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
            # Lifecycle state + photo flag, read back by the dashboard paths.
            ("state", "received", None),
            ("has_photo", None, 1.0 if has_photo else 0.0),
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

    def persist_synced_observation(self, doc: dict) -> bool:
        """Write a MongoDB report document into DuckLake, preserving its
        ``observation_id`` and digests (no new ids minted). Idempotent: skips
        if the node already exists. Returns True if inserted, False if it was
        already present. Used by the Mongo -> DuckLake sync (plan/09 Phase C).
        """
        observation_id = doc["observation_id"]
        now = datetime.now(timezone.utc)
        symptoms = doc.get("symptoms")
        count = doc.get("count")
        props: list[tuple[str, Optional[str], Optional[float]]] = [
            ("report_type", doc.get("report_type"), None),
            ("event_class", doc.get("event_class"), None),
            ("coarse_zip", doc.get("coarse_zip"), None),
            ("coarse_grid_id", doc.get("coarse_grid_id"), None),
            ("event_date", doc.get("event_date"), None),
            ("severity", doc.get("severity"), None),
            ("count", None, float(count) if count is not None else None),
            ("species", doc.get("species"), None),
            ("symptoms", ",".join(str(s) for s in symptoms) if symptoms else None, None),
            ("notes_sha256", doc.get("notes_sha256"), None),
            ("claim_token_sha256", doc.get("claim_token_sha256"), None),
            ("attached_user_id", doc.get("attached_user_id"), None),
            ("intake_at", doc.get("intake_at"), None),
            ("channel", doc.get("channel", "mobile"), None),
        ]
        props = [(k, t, n) for (k, t, n) in props if t is not None or n is not None]

        with self._lock:
            exists = self._con.execute(
                "SELECT count(*) FROM kg.node WHERE node_id = ?", (observation_id,)
            ).fetchone()[0]
            if exists:
                return False
            self._con.execute("BEGIN TRANSACTION;")
            try:
                self._con.execute(
                    "INSERT INTO kg.node (node_id, node_type, label, description, "
                    "source_fig, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        observation_id,
                        "observation",
                        f"{doc.get('report_type', '')} report",
                        None,
                        doc.get("source_fig", "app-intake"),
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
                        "mongo-sync",
                        observation_id,
                        now,
                        datetime.now(timezone.utc),
                        0.0,
                        None, None, None, None, None,
                        0.0,
                        "success",
                        doc.get("input_digest"),
                        hash_for_audit({"observation_id": observation_id}),
                        None,
                        "mongo-sync",
                    ),
                )
                self._con.execute("COMMIT;")
            except Exception:
                self._con.execute("ROLLBACK;")
                raise
        return True

    def read_status(self, observation_id: str, claim_token: str) -> Optional[str]:
        """Return the observation's state if the claim_token matches.

        * ``None``                -> no such observation.
        * raises ``PermissionError`` -> exists but the token doesn't match.
        Token comparison is digest-vs-digest (we never stored the plaintext).
        """
        with self._lock:
            props = self._read_props_locked(observation_id)
        if "claim_token_sha256" not in props:
            return None
        if props["claim_token_sha256"][0] != _sha256(claim_token):
            raise PermissionError("claim_token mismatch")
        return props.get("state", ("received", None))[0] or "received"

    # -- Dashboard read/write paths -----------------------------------------

    def _read_props_locked(
        self, observation_id: str
    ) -> dict[str, tuple[Optional[str], Optional[float]]]:
        """All (value_text, value_num) properties for a node. Caller holds lock."""
        rows = self._con.execute(
            "SELECT key, value_text, value_num FROM kg.property WHERE node_id = ?",
            (observation_id,),
        ).fetchall()
        return {key: (vtext, vnum) for key, vtext, vnum in rows}

    def _owns(
        self,
        props: dict[str, tuple[Optional[str], Optional[float]]],
        *,
        user_id: Optional[str],
        claim_token: Optional[str],
    ) -> bool:
        """True iff the supplied credential proves ownership of this report."""
        if user_id is not None:
            owner = props.get("attached_user_id", (None, None))[0]
            if owner is not None and owner == user_id:
                return True
        if claim_token is not None:
            digest = props.get("claim_token_sha256", (None, None))[0]
            if digest is not None and digest == _sha256(claim_token):
                return True
        return False

    def _summary_from_props(
        self, observation_id: str, props: dict[str, tuple[Optional[str], Optional[float]]]
    ) -> dict[str, Any]:
        """Shape a kg.property bag into a ReportSummary-compatible dict."""
        has_photo = (props.get("has_photo", (None, 0.0))[1] or 0.0) >= 1.0
        zip_ = props.get("coarse_zip", (None, None))[0]
        grid_id = props.get("coarse_grid_id", (None, None))[0]
        loc: dict[str, Any] = {}
        if zip_:
            loc["zip"] = zip_
        if grid_id:
            loc["grid_id"] = grid_id
            loc.setdefault("resolution_m", 1000)
        return {
            "observation_id": observation_id,
            "report_type": props.get("report_type", (None, None))[0],
            "event_class": props.get("event_class", (None, None))[0],
            "coarse_location": loc,
            "event_date": props.get("event_date", (None, None))[0],
            "severity": props.get("severity", (None, None))[0],
            "state": props.get("state", ("received", None))[0] or "received",
            "has_photo": has_photo,
            "photo_url": (
                f"/v1/reports/{observation_id}/photo" if has_photo else None
            ),
            "created_at": props.get("intake_at", (None, None))[0],
        }

    def list_user_reports(self, user_id: str) -> list[dict[str, Any]]:
        """Owner-scoped: every report attached to ``user_id``, newest first."""
        with self._lock:
            rows = self._con.execute(
                "SELECT node_id FROM kg.property "
                "WHERE key = 'attached_user_id' AND value_text = ?",
                (user_id,),
            ).fetchall()
            summaries = [
                self._summary_from_props(node_id, self._read_props_locked(node_id))
                for (node_id,) in rows
            ]
        summaries.sort(key=lambda s: s.get("created_at") or "", reverse=True)
        return summaries

    def _update_prop_locked(
        self, observation_id: str, key: str, value_text: Optional[str], value_num: Optional[float]
    ) -> None:
        updated = self._con.execute(
            "UPDATE kg.property SET value_text = ?, value_num = ? "
            "WHERE node_id = ? AND key = ?",
            (value_text, value_num, observation_id, key),
        )
        # DuckDB UPDATE doesn't reliably report rowcount across versions; do a
        # presence check and INSERT if the key wasn't there yet.
        present = self._con.execute(
            "SELECT 1 FROM kg.property WHERE node_id = ? AND key = ?",
            (observation_id, key),
        ).fetchone()
        if present is None:
            self._con.execute(
                "INSERT INTO kg.property (node_id, key, value_text, value_num) "
                "VALUES (?, ?, ?, ?)",
                (observation_id, key, value_text, value_num),
            )
        _ = updated

    def set_state(
        self,
        observation_id: str,
        state: str,
        *,
        user_id: Optional[str] = None,
        claim_token: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Set lifecycle state (e.g. 'withdrawn') after verifying ownership.

        * ``None``                  -> no such observation.
        * raises ``PermissionError`` -> exists but the credential doesn't own it.
        Otherwise returns the updated ReportSummary-compatible dict.
        """
        with self._lock:
            props = self._read_props_locked(observation_id)
            if not props:
                return None
            if not self._owns(props, user_id=user_id, claim_token=claim_token):
                raise PermissionError("not the owner")
            self._update_prop_locked(observation_id, "state", state, None)
            props = self._read_props_locked(observation_id)
            return self._summary_from_props(observation_id, props)

    def remove_photo(
        self,
        observation_id: str,
        *,
        user_id: Optional[str] = None,
        claim_token: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Drop the photo flag/ref after verifying ownership. Idempotent."""
        with self._lock:
            props = self._read_props_locked(observation_id)
            if not props:
                return None
            if not self._owns(props, user_id=user_id, claim_token=claim_token):
                raise PermissionError("not the owner")
            self._update_prop_locked(observation_id, "has_photo", None, 0.0)
            self._con.execute(
                "DELETE FROM kg.property WHERE node_id = ? AND key = 'photo_ref'",
                (observation_id,),
            )
            props = self._read_props_locked(observation_id)
            return self._summary_from_props(observation_id, props)

    def aggregate_by_zcta(
        self, anchor_zip: str, min_cell: int = 1
    ) -> dict[str, list[dict[str, Any]]]:
        """ZCTA-bucketed report counts, split into the anchor ZIP vs the rest.

        Excludes withdrawn reports and any bucket below ``min_cell`` (small-cell
        suppression — privacy rule 6). Returns ``{"local": [...], "regional": [...]}``
        of ``ZctaAggregate``-compatible dicts.
        """
        with self._lock:
            rows = self._con.execute(
                """
                SELECT z.value_text AS zcta, t.value_text AS report_type, count(*) AS n
                FROM kg.property z
                JOIN kg.property t
                  ON t.node_id = z.node_id AND t.key = 'report_type'
                LEFT JOIN kg.property s
                  ON s.node_id = z.node_id AND s.key = 'state'
                WHERE z.key = 'coarse_zip' AND z.value_text IS NOT NULL
                  AND COALESCE(s.value_text, 'received') <> 'withdrawn'
                GROUP BY z.value_text, t.value_text
                """
            ).fetchall()
        local: list[dict[str, Any]] = []
        regional: list[dict[str, Any]] = []
        for zcta, report_type, n in rows:
            if n < min_cell or not report_type:
                continue
            agg = {"zcta": zcta, "report_type": report_type, "count": int(n)}
            (local if zcta == anchor_zip else regional).append(agg)
        local.sort(key=lambda a: a["count"], reverse=True)
        regional.sort(key=lambda a: a["count"], reverse=True)
        return {"local": local, "regional": regional}

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
