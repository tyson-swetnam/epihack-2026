"""Offline tests for the MongoDB mobile-channel write-path (plan/09).

Uses mongomock (no infra). Asserts the privacy posture matches kg_writer:
free-text notes and the claim_token are stored only as SHA-256 digests.
"""
from __future__ import annotations

import hashlib

import mongomock
import pytest

from onehealth_agents.api.models import ReportPayload
from onehealth_agents.mongo_writer import MongoWriter


def _payload() -> ReportPayload:
    return ReportPayload.model_validate(
        {
            "report_type": "animal",
            "event_class": "animal.mass_die_off",
            "coarse_location": {"zip": "86001"},
            "severity": "alarm",
            "count": 12,
            "species": "bats",
            "notes": "a dozen bats found dead under the bridge",
        }
    )


def _writer() -> MongoWriter:
    coll = mongomock.MongoClient()["onehealth"]["reports"]
    return MongoWriter(collection=coll)


def test_persist_writes_doc_with_coarse_fields():
    w = _writer()
    obs_id, token = w.persist_observation(_payload())
    doc = w.collection.find_one({"observation_id": obs_id})
    assert doc is not None
    assert doc["channel"] == "mobile"
    assert doc["report_type"] == "animal"
    assert doc["event_class"] == "animal.mass_die_off"
    assert doc["coarse_zip"] == "86001"
    assert doc["count"] == 12
    assert doc["synced_to_ducklake"] is False


def test_notes_and_token_stored_only_as_digests():
    w = _writer()
    payload = _payload()
    obs_id, token = w.persist_observation(payload)
    doc = w.collection.find_one({"observation_id": obs_id})

    # Raw free-text must never be persisted.
    assert "notes" not in doc
    assert payload.notes not in str(doc.values())
    assert doc["notes_sha256"] == hashlib.sha256(payload.notes.encode()).hexdigest()

    # Bearer token stored as a digest, not plaintext.
    assert token not in str(doc.values())
    assert doc["claim_token_sha256"] == hashlib.sha256(token.encode()).hexdigest()


def test_read_status_verifies_claim_token():
    w = _writer()
    obs_id, token = w.persist_observation(_payload())

    assert w.read_status(obs_id, token) == "received"
    assert w.read_status("nonexistent", token) is None
    with pytest.raises(PermissionError):
        w.read_status(obs_id, "wrong-token")
