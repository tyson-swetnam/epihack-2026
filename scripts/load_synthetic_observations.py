#!/usr/bin/env python3
"""Generate several thousand SYNTHETIC report submissions and persist them
into the real DuckLake knowledge graph, via the same kg.node/property/agent_run
shape the production KgWriter writes.

This script was originally drafted on the live Jetstream2 demo VM as
``/tmp/gen_synth.py`` (untracked) and was promoted into the repo on
2026-05-23 as part of the post-EpiHack archival pass. See
``plan/ANSIBLE-AUDIT-2026-05-23.md`` "Synthetic dataset is operationally
invisible" and ``plan/10-archival-and-docs.md`` Phase 7c.

Usage::

    cd /srv/onehealth/epihack-2026         # the deployed checkout
    sudo -u onehealth env \
      KG_DUCKLAKE_URI="ducklake:postgres:dbname=epihack host=127.0.0.1 user=onehealth password=$PG_PASSWORD" \
      KG_DUCKLAKE_DATA_PATH="/srv/onehealth/ducklake-data" \
      ./agents/.venv/bin/python scripts/load_synthetic_observations.py

The Ansible ``ducklake`` role gates this behind ``ducklake_load_synthetic_demo``
(defaults to ``false``); flip it to ``true`` in inventory/host vars to load
the demo cohort on a fresh provision.

Privacy / never-diagnose invariants (deliberate):
  * No record stores a disease, diagnosis, or condition. Only report_type,
    event_class (a *category* the user picks), coarse ZIP, severity, count,
    species, and symptom *categories* are stored.
  * Free-text notes are stored ONLY as a SHA-256 digest — never raw. The
    vivid clinical detail that could imply a diagnosis (e.g. "blood from the
    nose and mouth", "rash with high fever") is exactly what gets discarded.
  * The three geographic "signals" (Nogales / Lake Havasu City / Portal) are
    shaped by the GENERATOR only; they exist purely as elevated counts of
    ordinary observation categories in observation space — detectable as
    anomalies, never labeled.

Rows are tagged source_fig='synthetic-load' + a synthetic_batch property so
they are cleanly identifiable and removable. Re-running deletes the prior
synthetic batch first (idempotent).
"""
from __future__ import annotations

import hashlib
import os
import random
import sys
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

# Validate every synthetic record through the real API model (fidelity).
from onehealth_agents.api.models import CoarseLocation, ReportPayload
from onehealth_agents.kg_writer import KgWriter
try:
    from onehealth_agents.audit import hash_for_audit
except Exception:  # pragma: no cover
    def hash_for_audit(obj):
        import json
        return hashlib.sha256(
            json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()

SEED = 20260521
random.seed(SEED)
BATCH = "synthetic-2026-05-21"
TODAY = date(2026, 5, 21)
NOW = datetime(2026, 5, 21, 16, 0, tzinfo=timezone.utc)


def sha256(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


# --- AZ ZIP -> county, with rough population weights for a realistic spread ---
# (weights are relative; Maricopa/Pima dominate, rural counties are sparse)
ZIPS = [
    # Maricopa (Phoenix metro)
    ("85008", "Maricopa", 60), ("85015", "Maricopa", 55), ("85035", "Maricopa", 60),
    ("85201", "Maricopa", 45), ("85281", "Maricopa", 40), ("85301", "Maricopa", 42),
    ("85225", "Maricopa", 44), ("85382", "Maricopa", 30), ("85338", "Maricopa", 28),
    ("85003", "Maricopa", 25), ("85345", "Maricopa", 30),
    # Pima (Tucson)
    ("85705", "Pima", 38), ("85710", "Pima", 36), ("85719", "Pima", 30),
    ("85741", "Pima", 28), ("85745", "Pima", 26), ("85706", "Pima", 30),
    # Pinal
    ("85122", "Pinal", 18), ("85132", "Pinal", 10), ("85128", "Pinal", 10),
    # Yavapai
    ("86301", "Yavapai", 14), ("86326", "Yavapai", 9),
    # Coconino
    ("86001", "Coconino", 14), ("86004", "Coconino", 10),
    # Mohave (incl. Lake Havasu City cluster ZIPs, baseline weight only here)
    ("86401", "Mohave", 10), ("86442", "Mohave", 9),
    # Yuma
    ("85364", "Yuma", 16), ("85365", "Yuma", 12),
    # Cochise (incl. Portal/Douglas region baseline)
    ("85635", "Cochise", 12), ("85607", "Cochise", 6),
    # Santa Cruz (incl. Nogales baseline)
    ("85648", "Santa Cruz", 6),
    # Navajo / Apache / Gila / Graham / La Paz / Greenlee
    ("85901", "Navajo", 8), ("86025", "Navajo", 5),
    ("85925", "Apache", 5), ("86512", "Apache", 4),
    ("85501", "Gila", 6), ("85546", "Graham", 5),
    ("85344", "La Paz", 4), ("85533", "Greenlee", 3),
]
ZIP_POOL = [z for (z, _c, w) in ZIPS for _ in range(w)]
ZIP_COUNTY = {z: c for (z, c, _w) in ZIPS}
# add cluster ZIP -> county so county tagging is complete
ZIP_COUNTY.update({"85621": "Santa Cruz", "86403": "Mohave", "86404": "Mohave",
                   "86406": "Mohave", "85632": "Cochise"})

HUMAN_CLASSES = {
    "human.heat_distress": 0.26, "human.respiratory": 0.15,
    "human.gastrointestinal": 0.14, "human.fever_chills": 0.11,
    "human.rash_or_bite": 0.09, "human.exposure_water": 0.05,
    "human.exposure_animal": 0.05, "human.animal_bite_scratch": 0.15,
}
ANIMAL_CLASSES = {
    "animal.dead_wildlife": 0.30, "animal.sick_unusual_behaviour": 0.20,
    "animal.pet_sick": 0.20, "animal.dead_livestock": 0.10,
    "animal.unusual_species_sighting": 0.10, "animal.mass_die_off": 0.05,
    "animal.malnourishment": 0.05,
}
ENV_CLASSES = {
    "env.standing_water": 0.20, "env.air_quality": 0.20, "env.smoke_or_burn": 0.15,
    "env.water_quality": 0.15, "env.sewage": 0.10, "env.illegal_dumping": 0.10,
    "env.food_safety": 0.10,
}
SYMPTOMS_BY_CLASS = {
    "human.heat_distress": ["heat_cramps", "dizziness", "confusion"],
    "human.respiratory": ["cough", "shortness_of_breath"],
    "human.gastrointestinal": ["nausea_vomiting", "diarrhea"],
    "human.fever_chills": ["fever", "chills", "headache", "muscle_aches"],
    "human.rash_or_bite": ["rash"],
}
SEVERITIES = ["grin", "neutral", "frown", "alarm"]
SPECIES = ["javelina", "mule deer", "gray fox", "raccoon", "striped skunk",
           "white-nosed coati", "coyote", "desert cottontail", "rock squirrel"]


def wpick(d):
    keys, weights = list(d.keys()), list(d.values())
    return random.choices(keys, weights=weights, k=1)[0]


def rand_recent(days_back_max, recent_bias=False):
    if recent_bias:
        # weight toward the most recent days (rising signal)
        d = int(abs(random.triangular(0, days_back_max, 0)))
    else:
        d = random.randint(0, days_back_max)
    return TODAY - timedelta(days=d)


records = []  # list of dicts: payload + meta(notes, when)


def add(payload_kwargs, when: date, notes: str | None):
    records.append({"payload": ReportPayload(**payload_kwargs), "when": when, "notes": notes})


# ---------------------------------------------------------------------------
# 1) BASELINE — ~4000 reports spread across the state over ~75 days
# ---------------------------------------------------------------------------
N_BASE = 4000
for _ in range(N_BASE):
    rt = random.choices(["human", "animal", "environmental"], weights=[50, 22, 28])[0]
    zp = random.choice(ZIP_POOL)
    when = rand_recent(75)
    sev = random.choices(SEVERITIES, weights=[18, 50, 24, 8])[0]
    notes = None
    if rt == "human":
        ec = wpick(HUMAN_CLASSES)
        syms = SYMPTOMS_BY_CLASS.get(ec)
        symptoms = random.sample(syms, k=random.randint(1, len(syms))) if syms else None
        kw = dict(report_type="human", event_class=ec,
                  coarse_location=CoarseLocation(zip=zp), event_date=when,
                  severity=sev, symptoms=symptoms)
    elif rt == "animal":
        ec = wpick(ANIMAL_CLASSES)
        cnt = None
        if ec in ("animal.dead_wildlife", "animal.mass_die_off", "animal.dead_livestock"):
            cnt = random.choices([1, 2, 3], weights=[70, 22, 8])[0]
        kw = dict(report_type="animal", event_class=ec,
                  coarse_location=CoarseLocation(zip=zp), event_date=when,
                  severity=sev, count=cnt,
                  species=random.choice(SPECIES) if random.random() < 0.6 else None)
    else:
        ec = wpick(ENV_CLASSES)
        kw = dict(report_type="environmental", event_class=ec,
                  coarse_location=CoarseLocation(zip=zp), event_date=when, severity=sev)
    add(kw, when, notes)

# ---------------------------------------------------------------------------
# 2) NOGALES SIGNAL — elevated febrile + rash human reports (dengue-LIKE
#    symptom profile; never labeled). ZIPs 85621 / 85648, last ~24 days, rising.
# ---------------------------------------------------------------------------
DENGUE_LIKE = ["fever", "chills", "headache", "muscle_aches", "rash", "nausea_vomiting"]
NOTE_NOGALES = [
    "high fever and terrible body and joint aches for several days",
    "fever, headache behind the eyes, and a rash appearing on the arms",
    "bad muscle pain, chills, and now a skin rash; lots of mosquitoes lately",
    "fever for 4 days, exhausted, some nausea and a faint rash",
]
for _ in range(170):
    zp = random.choices(["85621", "85648"], weights=[80, 20])[0]
    ec = random.choices(["human.fever_chills", "human.rash_or_bite", "human.gastrointestinal"],
                        weights=[60, 30, 10])[0]
    syms = random.sample(DENGUE_LIKE, k=random.randint(3, 5))
    if "fever" not in syms:
        syms[0] = "fever"
    when = rand_recent(24, recent_bias=True)
    add(dict(report_type="human", event_class=ec,
             coarse_location=CoarseLocation(zip=zp), event_date=when,
             severity=random.choices(SEVERITIES, weights=[2, 18, 50, 30])[0],
             symptoms=list(dict.fromkeys(syms))),
        when, random.choice(NOTE_NOGALES))

# ---------------------------------------------------------------------------
# 3) LAKE HAVASU CITY SIGNAL — point-source food-safety + GI spike, ~9-day
#    window. ZIPs 86403/86404/86406. env.food_safety + human.gastrointestinal.
# ---------------------------------------------------------------------------
NOTE_HAVASU_ENV = [
    "got sick after eating at a riverside food vendor",
    "spoiled food smell and several people ill after the same lunch spot",
    "suspect undercooked food from a festival booth by the lake",
]
NOTE_HAVASU_GI = [
    "severe vomiting and diarrhea hours after eating out",
    "whole family has stomach cramps and diarrhea since the cookout",
    "nausea, vomiting, watery diarrhea overnight",
]
havasu_start = 9
for _ in range(140):
    zp = random.choice(["86403", "86404", "86406"])
    when = TODAY - timedelta(days=int(abs(random.triangular(0, havasu_start, 4))))
    if random.random() < 0.42:
        add(dict(report_type="environmental", event_class="env.food_safety",
                 coarse_location=CoarseLocation(zip=zp), event_date=when,
                 severity=random.choices(SEVERITIES, weights=[3, 25, 52, 20])[0]),
            when, random.choice(NOTE_HAVASU_ENV))
    else:
        syms = ["nausea_vomiting", "diarrhea"]
        if random.random() < 0.3:
            syms.append("fever")
        add(dict(report_type="human", event_class="human.gastrointestinal",
                 coarse_location=CoarseLocation(zip=zp), event_date=when,
                 severity=random.choices(SEVERITIES, weights=[2, 20, 53, 25])[0],
                 symptoms=syms),
            when, random.choice(NOTE_HAVASU_GI))

# ---------------------------------------------------------------------------
# 4) PORTAL SIGNAL — animal die-off (multiple dead, hemorrhagic detail only in
#    hashed notes) + animal bite/scratch reports. ZIP 85632 (+ nearby 85607),
#    last ~18 days.
# ---------------------------------------------------------------------------
NOTE_PORTAL_DEAD = [
    "found several dead wildlife with blood around the nose and mouth",
    "multiple dead javelina near the wash, bleeding from the muzzle",
    "two foxes dead in the yard, blood from nose, very unusual",
    "dead deer and a coati within days, all with bloody orifices",
]
NOTE_PORTAL_BITE = [
    "scratched by a sick-acting fox that was stumbling",
    "bitten on the hand by a raccoon that seemed disoriented",
    "javelina charged and bit a hiker on the trail",
]
for _ in range(85):
    zp = random.choices(["85632", "85607"], weights=[82, 18])[0]
    when = rand_recent(18, recent_bias=True)
    roll = random.random()
    if roll < 0.30:
        add(dict(report_type="human", event_class="human.animal_bite_scratch",
                 coarse_location=CoarseLocation(zip=zp), event_date=when,
                 severity=random.choices(SEVERITIES, weights=[2, 22, 50, 26])[0],
                 species=random.choice(["gray fox", "raccoon", "javelina", "striped skunk"])),
            when, random.choice(NOTE_PORTAL_BITE))
    else:
        ec = random.choices(["animal.dead_wildlife", "animal.mass_die_off",
                             "animal.sick_unusual_behaviour", "animal.dead_livestock"],
                            weights=[42, 22, 24, 12])[0]
        cnt = random.randint(2, 9) if ec in ("animal.dead_wildlife", "animal.mass_die_off") \
            else random.choice([1, 2, 3])
        add(dict(report_type="animal", event_class=ec,
                 coarse_location=CoarseLocation(zip=zp), event_date=when,
                 severity=random.choices(SEVERITIES, weights=[1, 12, 40, 47])[0],
                 count=cnt, species=random.choice(SPECIES)),
            when, random.choice(NOTE_PORTAL_DEAD))

random.shuffle(records)
print(f"generated {len(records)} synthetic reports (seed={SEED})")

# ---------------------------------------------------------------------------
# Persist into DuckLake (same row shape as KgWriter.persist_observation),
# bulk-inserted in one transaction => one DuckLake snapshot.
# ---------------------------------------------------------------------------
w = KgWriter()  # reads KG_DUCKLAKE_URI / KG_DUCKLAKE_DATA_PATH from env
con = w._con
assert w.persistent, "KgWriter is NOT persistent — KG_DUCKLAKE_URI not set!"

node_rows, prop_rows, run_rows = [], [], []
for rec in records:
    p = rec["payload"]
    oid = str(uuid4())
    claim = uuid4().hex
    when_dt = datetime(rec["when"].year, rec["when"].month, rec["when"].day,
                       random.randint(6, 22), random.randint(0, 59), tzinfo=timezone.utc)
    zp = p.coarse_location.zip
    props = [
        ("report_type", str(p.report_type), None),
        ("event_class", str(p.event_class), None),
        ("coarse_zip", zp, None),
        ("county", ZIP_COUNTY.get(zp), None),
        ("event_date", str(p.event_date) if p.event_date else None, None),
        ("severity", p.severity, None),
        ("count", None, float(p.count) if p.count is not None else None),
        ("species", p.species, None),
        ("symptoms", ",".join(str(s) for s in p.symptoms) if p.symptoms else None, None),
        # free text -> digest ONLY (never the raw clinical detail)
        ("notes_sha256", sha256(rec["notes"]) if rec["notes"] else None, None),
        ("claim_token_sha256", sha256(claim), None),
        ("intake_at", when_dt.isoformat(), None),
        ("synthetic_batch", BATCH, None),
    ]
    props = [(k, t, n) for (k, t, n) in props if t is not None or n is not None]
    node_rows.append((oid, "observation", f"{p.report_type} report", None,
                      "synthetic-load", when_dt))
    for k, t, n in props:
        prop_rows.append((oid, k, t, n))
    run_rows.append((
        str(uuid4()), "intake", oid, when_dt, when_dt, 0.0,
        None, None, None, None, None, 0.0, "success",
        hash_for_audit(p.model_dump(mode="json")),
        hash_for_audit({"observation_id": oid}), None, "synthetic-load",
    ))

AGENT_RUN_INSERT = (
    "INSERT INTO kg.agent_run (run_id, agent_name, observation_id, started_at, "
    "ended_at, duration_ms, model_id, prompt_tokens, completion_tokens, "
    "cache_read_tokens, cache_creation_tokens, cost_usd, outcome, input_digest, "
    "output_digest, error_message, source_fig) VALUES "
    "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
)

# Idempotency: clear any prior synthetic batch first.
prior = con.execute(
    "SELECT count(*) FROM kg.node WHERE source_fig = 'synthetic-load'"
).fetchone()[0]
con.execute("BEGIN TRANSACTION;")
try:
    if prior:
        con.execute(
            "DELETE FROM kg.property WHERE node_id IN "
            "(SELECT node_id FROM kg.node WHERE source_fig='synthetic-load');"
        )
        con.execute("DELETE FROM kg.agent_run WHERE source_fig='synthetic-load';")
        con.execute("DELETE FROM kg.node WHERE source_fig='synthetic-load';")
        print(f"cleared {prior} rows from a prior synthetic batch")
    con.executemany(
        "INSERT INTO kg.node (node_id, node_type, label, description, source_fig, "
        "created_at) VALUES (?,?,?,?,?,?)", node_rows)
    con.executemany(
        "INSERT INTO kg.property (node_id, key, value_text, value_num) VALUES (?,?,?,?)",
        prop_rows)
    con.executemany(AGENT_RUN_INSERT, run_rows)
    con.execute("COMMIT;")
except Exception:
    con.execute("ROLLBACK;")
    raise

print(f"persisted: {len(node_rows)} observation nodes, {len(prop_rows)} properties, "
      f"{len(run_rows)} agent_run rows")
total = con.execute(
    "SELECT count(*) FROM kg.node WHERE node_type='observation'"
).fetchone()[0]
print(f"kg.node observations now total: {total}")
