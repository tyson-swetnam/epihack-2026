"""Sync MongoDB mobile-channel reports into DuckLake (plan/09 Phase C).

Mobile reports land in MongoDB (mongo_writer); analytics, the agents, and the
MCP servers read DuckLake. This job replays not-yet-synced report documents
into the DuckLake knowledge graph so the dataset stays unified.

- Reads docs where ``synced_to_ducklake`` is not True (the watermark).
- Writes each via ``KgWriter.persist_synced_observation`` — idempotent on
  ``observation_id`` and preserving the original id + digests.
- Marks the doc ``synced_to_ducklake: true`` only after a successful write.

Idempotent and safe to re-run; intended to run on a systemd timer. Run with:
    python -m onehealth_agents.sync.mongo_to_ducklake
"""
from __future__ import annotations

import logging
import sys

log = logging.getLogger(__name__)


def sync_once(batch: int = 500, *, mongo=None, kg=None) -> int:
    """Sync up to ``batch`` unsynced reports. Returns the number synced.

    ``mongo`` / ``kg`` may be injected (tests); otherwise the process
    singletons are used.
    """
    from ..kg_writer import get_writer
    from ..mongo_writer import get_mongo_writer

    coll = (mongo or get_mongo_writer()).collection
    kg = kg or get_writer()

    docs = list(coll.find({"synced_to_ducklake": {"$ne": True}}).limit(batch))
    synced = 0
    for doc in docs:
        oid = doc.get("observation_id")
        try:
            kg.persist_synced_observation(doc)
            coll.update_one(
                {"_id": doc["_id"]}, {"$set": {"synced_to_ducklake": True}}
            )
            synced += 1
        except Exception:  # noqa: BLE001 - one bad doc must not stall the batch
            log.exception("Mongo->DuckLake sync failed for observation_id=%s", oid)
    return synced


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    n = sync_once()
    log.info("synced %d report(s) Mongo -> DuckLake", n)
    print(f"synced {n} report(s) Mongo -> DuckLake")
    return 0


if __name__ == "__main__":
    sys.exit(main())
