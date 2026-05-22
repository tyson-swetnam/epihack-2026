#!/usr/bin/env python3
"""Export a privacy-safe ZCTA-week signal aggregation from DuckLake.

Reads the durable intake observations out of the DuckLake knowledge graph
(``kg.node`` + ``kg.property``) and writes ``dashboard/data/signals.json`` — the
read-only feed the agency analysis dashboard renders.

What this is allowed to emit (privacy contract, CONTRIBUTING.md / plan/06):

  * **ZCTA-week aggregations only** — counts per ZIP per ISO-week, never an
    individual observation, never a precise location, never raw notes.
  * **Observation space only — never a diagnosis.** A "signal" is an
    above-baseline count of a *category of report* (e.g. febrile-or-rash
    reports, gastrointestinal-or-food-safety reports, animal die-off-or-bite
    reports). It is deliberately NOT labelled with a disease/pathogen. The
    Cluster Detection Agent flags an anomaly in counts; naming a cause is a
    downstream, human, agency-side act (Scenario D), not something this
    surveillance export ever asserts.
  * Small-cell suppression: symptom-category breakdowns for a ZIP-week are
    suppressed below ``MIN_CELL`` to avoid re-identification.

Anomaly score is an EARS C1-style standardised exceedance: for each ZIP and
signal grouping, baseline = mean+sd of that ZIP's own prior-week counts; the
recent-window count is scored ``(obs - mean) / sd``. No epidemiological model
is claimed beyond "this count is unusual for this place."

Run (as the deploy user, against the live catalog)::

    sudo -u onehealth env \\
      KG_DUCKLAKE_URI="ducklake:postgres:dbname=epihack host=127.0.0.1 user=onehealth password=..." \\
      KG_DUCKLAKE_DATA_PATH="/srv/onehealth/ducklake-data" \\
      .venv/bin/python scripts/export_signals.py
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import duckdb

# --- config ----------------------------------------------------------------

OUT_PATH = Path(
    os.environ.get(
        "SIGNALS_OUT",
        str(Path(__file__).resolve().parent.parent / "dashboard" / "data" / "signals.json"),
    )
)
MIN_CELL = 3            # suppress symptom breakdowns below this count
MIN_RECENT = 8          # ignore places with fewer recent reports (noise floor)
RECENT_DAYS = 14        # the "recent window" scored against baseline
TOP_SIGNALS = 12        # cap on emitted signal rows

# Observation-space signal groupings. Each maps a human-readable, NON-diagnostic
# label to the set of event_class slugs that compose it. The label describes
# *what was reported*, never what it might mean clinically.
SIGNAL_GROUPS = {
    "febrile_or_rash": {
        "label": "Febrile / rash reports",
        "blurb": "Above-baseline count of human reports tagged fever/chills "
                 "or rash/bite. Routing signal only — not a diagnosis.",
        "classes": ["human.fever_chills", "human.rash_or_bite"],
    },
    "gi_or_food": {
        "label": "Gastrointestinal / food-safety reports",
        "blurb": "Above-baseline count of human gastrointestinal reports and "
                 "environmental food-safety reports in the same ZIP.",
        "classes": ["human.gastrointestinal", "env.food_safety"],
    },
    "animal_dieoff_or_bite": {
        "label": "Animal die-off / bite reports",
        "blurb": "Above-baseline count of dead/sick-wildlife, livestock and "
                 "mass-die-off reports plus human animal-bite/scratch reports.",
        "classes": [
            "animal.dead_wildlife", "animal.mass_die_off",
            "animal.dead_livestock", "animal.sick_unusual_behaviour",
            "human.animal_bite_scratch",
        ],
    },
}

# ZIP -> coarse place + county label, for analyst-facing display only. Coarse,
# already-public geography; no precise location is introduced here.
ZIP_PLACE = {
    "85621": ("Nogales", "Santa Cruz"), "85648": ("Nogales", "Santa Cruz"),
    "86403": ("Lake Havasu City", "Mohave"), "86404": ("Lake Havasu City", "Mohave"),
    "86406": ("Lake Havasu City", "Mohave"),
    "85632": ("Portal", "Cochise"), "85607": ("Portal", "Cochise"),
}


def connect() -> duckdb.DuckDBPyConnection:
    uri = os.environ["KG_DUCKLAKE_URI"]
    con = duckdb.connect(":memory:")
    for ext in ("ducklake", "postgres"):
        try:
            con.execute(f"INSTALL {ext}; LOAD {ext};")
        except Exception:  # noqa: BLE001 - may be statically linked
            pass
    data_path = os.environ.get("KG_DUCKLAKE_DATA_PATH")
    opts = f" (DATA_PATH '{data_path}')" if data_path else ""
    con.execute(f"ATTACH '{uri}' AS epihack{opts};")
    con.execute("USE epihack;")
    return con


def build_obs_view(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE OR REPLACE TEMP VIEW obs AS
        SELECT
          n.node_id,
          MAX(CASE WHEN p.key='report_type' THEN p.value_text END) AS report_type,
          MAX(CASE WHEN p.key='event_class' THEN p.value_text END) AS event_class,
          MAX(CASE WHEN p.key='coarse_zip'  THEN p.value_text END) AS zip,
          MAX(CASE WHEN p.key='event_date'  THEN p.value_text END) AS event_date,
          MAX(CASE WHEN p.key='symptoms'    THEN p.value_text END) AS symptoms
        FROM kg.node n JOIN kg.property p USING(node_id)
        WHERE n.node_type='observation'
          AND n.source_fig IN ('synthetic-load', 'app-intake')
        GROUP BY n.node_id
        """
    )


def iso_week(d: str) -> str:
    y, w, _ = datetime.fromisoformat(d).isocalendar()
    return f"{y}-W{w:02d}"


def main() -> None:
    con = connect()
    build_obs_view(con)

    rows = con.execute(
        "SELECT zip, event_class, event_date, symptoms FROM obs "
        "WHERE zip IS NOT NULL AND event_date IS NOT NULL"
    ).fetchall()

    # class -> signal-group key
    class_to_group: dict[str, str] = {}
    for key, spec in SIGNAL_GROUPS.items():
        for cls in spec["classes"]:
            class_to_group[cls] = key

    max_date = max(datetime.fromisoformat(r[2]).date() for r in rows)

    def place_of(z: str) -> tuple[str, Optional[str]]:
        return ZIP_PLACE.get(z, ("ZIP " + z, None))

    # ZCTA-week counts (the privacy unit) keyed by (zip, group, week).
    weekly: dict[tuple[str, str, str], int] = {}
    # Recent-window tallies, aggregated to PLACE (multi-ZIP towns merged) so a
    # cluster split across adjacent ZIPs reads as one signal.
    recent_count: dict[tuple[str, str], int] = {}          # (place, group)
    recent_symptoms: dict[tuple[str, str], dict[str, int]] = {}
    place_zctas: dict[str, set] = {}                        # place -> {zip,...}
    place_recent_total: dict[str, int] = {}                # place -> all reports
    group_recent_total: dict[str, int] = {}                # group -> statewide
    grand_recent_total = 0

    for zip_, ev_class, ev_date, symptoms in rows:
        place, _county = place_of(zip_)
        days_ago = (max_date - datetime.fromisoformat(ev_date).date()).days
        is_recent = days_ago < RECENT_DAYS
        if is_recent:
            place_recent_total[place] = place_recent_total.get(place, 0) + 1
            grand_recent_total += 1
        grp = class_to_group.get(ev_class)
        if grp is None:
            continue
        weekly[(zip_, grp, iso_week(ev_date))] = (
            weekly.get((zip_, grp, iso_week(ev_date)), 0) + 1
        )
        place_zctas.setdefault(place, set()).add(zip_)
        if is_recent:
            recent_count[(place, grp)] = recent_count.get((place, grp), 0) + 1
            group_recent_total[grp] = group_recent_total.get(grp, 0) + 1
            if symptoms:
                bag = recent_symptoms.setdefault((place, grp), {})
                for s in symptoms.split(","):
                    bag[s] = bag.get(s, 0) + 1

    # Score each (place, group). Expectation is the count this place *would*
    # see if its share of that signal matched its share of overall report
    # volume statewide; the standardised exceedance is a Poisson z-score,
    # (obs - exp) / sqrt(exp). This rewards genuine geographic concentration
    # and is self-suppressing for small places, so a sharp local spike no
    # longer inflates its own baseline (the flaw of a per-place self-baseline).
    signals = []
    for (place, grp), recent in recent_count.items():
        if recent < MIN_RECENT:
            continue
        share = place_recent_total.get(place, 0) / max(grand_recent_total, 1)
        expected = max(group_recent_total.get(grp, 0) * share, 0.5)
        z = (recent - expected) / (expected ** 0.5)
        spec = SIGNAL_GROUPS[grp]
        county = next(
            (place_of(z2)[1] for z2 in place_zctas.get(place, ()) if place_of(z2)[1]),
            None,
        )

        sym = recent_symptoms.get((place, grp), {})
        sym_safe = {k: v for k, v in sym.items() if v >= MIN_CELL}

        sev = (
            "urgent" if z >= 8 else
            "alert" if z >= 4 else
            "watch" if z >= 2 else
            "info"
        )
        signals.append({
            "signal_id": f"signal.{place.replace(' ', '_').lower()}.{grp}.{max_date.isoformat()}",
            "kg_node_id": None,
            "zctas": sorted(place_zctas.get(place, ())),
            "place": place,
            "county": county,
            "group": grp,
            "label": spec["label"],
            "blurb": spec["blurb"],
            "recent_window_days": RECENT_DAYS,
            "recent_count": recent,
            "expected_count": round(expected, 1),
            "exceedance_z": round(z, 2),
            "severity": sev,
            "top_symptom_categories": dict(
                sorted(sym_safe.items(), key=lambda kv: -kv[1])
            ),
        })

    signals.sort(key=lambda s: -s["exceedance_z"])
    flagged = [s for s in signals if s["severity"] in ("watch", "alert", "urgent")]
    flagged = flagged[:TOP_SIGNALS]

    # ZCTA-week matrix for the flagged places (counts only, all signal groups).
    flagged_zips = sorted({z for s in flagged for z in s["zctas"]})
    weeks = sorted({wk for (_z, _g, wk) in weekly})
    matrix = []
    for zip_ in flagged_zips:
        place, county = place_of(zip_)
        for grp in SIGNAL_GROUPS:
            series = [weekly.get((zip_, grp, wk), 0) for wk in weeks]
            if sum(series) == 0:
                continue
            matrix.append({
                "zcta": zip_, "place": place, "county": county,
                "group": grp, "label": SIGNAL_GROUPS[grp]["label"],
                "weeks": weeks, "counts": series,
            })

    total_obs = con.execute(
        "SELECT count(*) FROM obs WHERE zip IS NOT NULL"
    ).fetchone()[0]

    out = {
        "_about": (
            "Privacy-safe ZCTA-week signal aggregation exported from the live "
            "DuckLake knowledge graph by scripts/export_signals.py. Signals are "
            "above-baseline counts of REPORT CATEGORIES (observation space). "
            "They are NOT diagnoses: no disease or pathogen is named here, by "
            "design. Naming a cause is a downstream agency act (Scenario D)."
        ),
        "_generated_at": datetime.now(timezone.utc).isoformat(),
        "_source": "DuckLake kg.node/kg.property (source_fig in synthetic-load, app-intake)",
        "_privacy": (
            f"ZCTA-week aggregations only; no individual observations; symptom "
            f"cells < {MIN_CELL} suppressed; coarse ZIP geography only."
        ),
        "data_through": max_date.isoformat(),
        "total_observations": total_obs,
        "method": (
            "Poisson exceedance per place per signal group: observed recent "
            "{d}-day count vs the count expected from the place's share of "
            "statewide report volume; z = (obs - exp)/sqrt(exp). "
            "Places with < {m} recent reports are not scored."
        ).format(d=RECENT_DAYS, m=MIN_RECENT),
        "signals": flagged,
        "zcta_week_matrix": matrix,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {OUT_PATH}")
    print(f"  total observations (zip-bearing): {total_obs}")
    print(f"  flagged signals: {len(flagged)}")
    for s in flagged:
        print(f"    [{s['severity']:6}] {s['place']:18} {s['label']:36} "
              f"n={s['recent_count']:3} z={s['exceedance_z']}")


if __name__ == "__main__":
    main()
