"""Persist inbound reports into MongoDB — the mobile-channel write path.

plan/09-mobile-datastore.md: mobile reports (``X-Client-Channel: mobile``) are
written here; web reports stay on DuckLake (``kg_writer``). Both go through
FastAPI, so the privacy contract is enforced in one place before either sink.

Privacy posture mirrors ``kg_writer`` exactly: structured/coarse fields are
stored verbatim, but free-text ``notes`` and the bearer ``claim_token`` are
stored **only as SHA-256 digests**. A later sync job (Phase C) replays these
documents into DuckLake so the agents/MCP analytics stay unified; the
``synced_to_ducklake`` flag is the watermark for that job.

When ``MONGODB_URI`` is unset the writer falls back to an in-memory
``mongomock`` client, so the API and the offline tests work with no
infrastructure (nothing persists across process restarts in that mode).
"""
from __future__ import annotations

import hashlib
import os
import threading
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from .audit import hash_for_audit


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class MongoWriter:
    """Thread-safe writer for mobile-channel reports into a Mongo collection."""

    def __init__(
        self,
        collection: Any | None = None,
        mongodb_uri: str | None = None,
        db_name: str = "onehealth",
        collection_name: str = "reports",
    ) -> None:
        self._lock = threading.Lock()
        self.persistent = False
        if collection is not None:
            self._coll = collection
            self.persistent = True
            return

        uri = mongodb_uri or os.environ.get("MONGODB_URI")
        if uri:
            import pymongo  # late import; only needed when a real URI is set

            client: Any = pymongo.MongoClient(uri)
            self.persistent = True
        else:
            # No infra yet (Phase B provisions it) -> in-memory mongomock so
            # the mobile channel still works in dev/tests.
            import mongomock

            client = mongomock.MongoClient()
        self._coll = client[db_name][collection_name]

    def persist_observation(
        self, payload: Any, user_id: Optional[str] = None
    ) -> tuple[str, str]:
        """Insert one report document. Returns ``(observation_id, claim_token)``;
        the plaintext claim_token is returned once, only its digest is stored."""
        observation_id = str(uuid4())
        claim_token = uuid4().hex
        now = datetime.now(timezone.utc)
        loc = payload.coarse_location

        doc = {
            "observation_id": observation_id,
            "node_type": "observation",
            "channel": "mobile",
            "source_fig": "app-intake",
            "report_type": str(payload.report_type),
            "event_class": str(payload.event_class),
            "coarse_zip": loc.zip,
            "coarse_grid_id": loc.grid_id,
            "event_date": str(payload.event_date) if payload.event_date else None,
            "severity": payload.severity,
            "count": payload.count,
            "species": payload.species,
            "symptoms": [str(s) for s in payload.symptoms] if payload.symptoms else None,
            # Free text + bearer token are never stored raw — digests only.
            "notes_sha256": _sha256(payload.notes) if payload.notes else None,
            "claim_token_sha256": _sha256(claim_token),
            "attached_user_id": user_id,
            "intake_at": now.isoformat(),
            "input_digest": hash_for_audit(payload.model_dump(mode="json")),
            # Watermark for the Phase-C Mongo -> DuckLake sync.
            "synced_to_ducklake": False,
        }
        with self._lock:
            self._coll.insert_one(doc)
        return observation_id, claim_token

    def read_status(self, observation_id: str, claim_token: str) -> Optional[str]:
        """``None`` if no such report; ``PermissionError`` on token mismatch;
        otherwise the state string. Digest-vs-digest comparison."""
        with self._lock:
            doc = self._coll.find_one({"observation_id": observation_id})
        if doc is None:
            return None
        if doc.get("claim_token_sha256") != _sha256(claim_token):
            raise PermissionError("claim_token mismatch")
        return "received"

    @property
    def collection(self) -> Any:
        return self._coll


_writer: Optional[MongoWriter] = None
_writer_lock = threading.Lock()


def get_mongo_writer() -> MongoWriter:
    global _writer
    if _writer is None:
        with _writer_lock:
            if _writer is None:
                _writer = MongoWriter()
    return _writer
