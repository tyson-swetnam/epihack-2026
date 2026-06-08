"""Offline test for the Mongo -> DuckLake sync (plan/09 Phase C).

mongomock for Mongo + in-memory DuckDB for the kg writer. Asserts the sync is
idempotent and preserves the original observation_id + digests.
"""
from __future__ import annotations

import mongomock

from onehealth_agents.api.models import ReportPayload
from onehealth_agents.kg_writer import KgWriter
from onehealth_agents.mongo_writer import MongoWriter
from onehealth_agents.sync.mongo_to_ducklake import sync_once


def _payload() -> ReportPayload:
    return ReportPayload.model_validate(
        {
            "report_type": "animal",
            "event_class": "animal.mass_die_off",
            "coarse_location": {"zip": "86001"},
            "notes": "synced via phase C",
        }
    )


def test_sync_copies_mobile_report_into_ducklake_idempotently():
    mongo = MongoWriter(collection=mongomock.MongoClient()["onehealth"]["reports"])
    kg = KgWriter()  # no MONGODB/DUCKLAKE uri -> in-memory DuckDB fallback

    obs_id, _token = mongo.persist_observation(_payload())

    # First sync: one report copied.
    assert sync_once(mongo=mongo, kg=kg) == 1

    # It landed in DuckLake under the SAME observation_id, with digests intact.
    row = kg.connection.execute(
        "SELECT count(*) FROM kg.node WHERE node_id = ?", (obs_id,)
    ).fetchone()[0]
    assert row == 1
    notes_digest = kg.connection.execute(
        "SELECT value_text FROM kg.property WHERE node_id = ? AND key = 'notes_sha256'",
        (obs_id,),
    ).fetchone()
    assert notes_digest is not None and notes_digest[0]

    # The Mongo doc is now watermarked.
    doc = mongo.collection.find_one({"observation_id": obs_id})
    assert doc["synced_to_ducklake"] is True

    # Re-running syncs nothing (watermark) and the kg node isn't duplicated.
    assert sync_once(mongo=mongo, kg=kg) == 0
    again = kg.connection.execute(
        "SELECT count(*) FROM kg.node WHERE node_id = ?", (obs_id,)
    ).fetchone()[0]
    assert again == 1
