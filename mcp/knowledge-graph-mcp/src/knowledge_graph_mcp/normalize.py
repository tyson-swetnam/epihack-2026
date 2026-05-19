"""Fuzzy + alias-based diagnosis normalisation.

Maps a free-text diagnosis string to one of the canonical
``pathogen.*`` slugs seeded under ``schema/deep/pathogens.sql``.

Resolution strategy (highest-confidence match wins):

1. **Exact ICD-10 code** in the input ("A20.0", "A92.3", ...). We look
   up ``code.icd10.*`` nodes by their ``code`` property and follow
   ``mappedTo --> focus.*`` then ``targetsFocusArea<-- pathogen.*``.
   Returns a confidence of 0.99.

2. **Exact SNOMED concept code** ("58750007", "230145002", ...). Same
   shape as ICD-10 but on ``code.snomed.*`` nodes.

3. **Curated alias hit** -- short common-name lookup (plague, valley
   fever, RMSF, hantavirus, ...). Confidence 0.95.

4. **Substring / scientific-name match** against ``pathogen.label``,
   ``pathogen.scientific_name``, the slug suffix, and the linked
   ``disease.*`` label. Confidence 0.85.

5. **Fuzzy token similarity** (difflib SequenceMatcher) over the same
   surface forms. Confidence = SequenceMatcher ratio (capped at 0.80
   to keep it below the exact / alias matches).

Returns ``{pathogen_id, snomed_code, icd10_code, confidence,
match_reason}`` -- ``pathogen_id`` is ``None`` when no candidate
exceeds the ``min_confidence`` floor.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Optional

import duckdb


# ---------------------------------------------------------------------------
# Curated common-name -> pathogen.* lookup.
#
# The schema/deep/pathogens.sql seeds carry scientific names and ICD-10
# strings but not common aliases (e.g. "plague" -> Y. pestis,
# "valley fever" -> Coccidioides). We keep the alias table small and
# explicit here so the agent can reason about why a match fired.
# ---------------------------------------------------------------------------
CURATED_ALIASES: dict[str, str] = {
    # Plague (Y. pestis)
    "plague": "pathogen.yersinia_pestis",
    "bubonic plague": "pathogen.yersinia_pestis",
    "pneumonic plague": "pathogen.yersinia_pestis",
    "septicemic plague": "pathogen.yersinia_pestis",
    "y. pestis": "pathogen.yersinia_pestis",
    "y pestis": "pathogen.yersinia_pestis",
    "yersinia pestis": "pathogen.yersinia_pestis",
    "yersinia": "pathogen.yersinia_pestis",
    # West Nile
    "west nile": "pathogen.wnv",
    "west nile virus": "pathogen.wnv",
    "west nile fever": "pathogen.wnv",
    "wnv": "pathogen.wnv",
    # St. Louis encephalitis
    "st louis encephalitis": "pathogen.slev",
    "st. louis encephalitis": "pathogen.slev",
    "sle": "pathogen.slev",
    "slev": "pathogen.slev",
    # Dengue
    "dengue": "pathogen.denv",
    "dengue fever": "pathogen.denv",
    "denv": "pathogen.denv",
    # Zika
    "zika": "pathogen.zikv",
    "zika virus": "pathogen.zikv",
    "zikv": "pathogen.zikv",
    # Hantavirus
    "hantavirus": "pathogen.snv",
    "hps": "pathogen.snv",
    "hantavirus pulmonary syndrome": "pathogen.snv",
    "sin nombre virus": "pathogen.snv",
    "sin nombre": "pathogen.snv",
    "snv": "pathogen.snv",
    # Tularemia
    "tularemia": "pathogen.francisella_tularensis",
    "rabbit fever": "pathogen.francisella_tularensis",
    "francisella tularensis": "pathogen.francisella_tularensis",
    "francisella": "pathogen.francisella_tularensis",
    # RMSF
    "rmsf": "pathogen.rickettsia_rickettsii",
    "rocky mountain spotted fever": "pathogen.rickettsia_rickettsii",
    "spotted fever": "pathogen.rickettsia_rickettsii",
    "rickettsia rickettsii": "pathogen.rickettsia_rickettsii",
    "rickettsia": "pathogen.rickettsia_rickettsii",
    # Rabies
    "rabies": "pathogen.rabies_lyssavirus",
    "lyssavirus": "pathogen.rabies_lyssavirus",
    # HPAI
    "h5n1": "pathogen.hpai_h5n1",
    "avian influenza": "pathogen.hpai_h5n1",
    "bird flu": "pathogen.hpai_h5n1",
    "hpai": "pathogen.hpai_h5n1",
    # CWD
    "cwd": "pathogen.cwd_prion",
    "chronic wasting disease": "pathogen.cwd_prion",
    # Valley fever
    "valley fever": "pathogen.coccidioides",
    "coccidioidomycosis": "pathogen.coccidioides",
    "cocci": "pathogen.coccidioides",
    "coccidioides": "pathogen.coccidioides",
    # Lyme
    "lyme": "pathogen.borrelia_burgdorferi",
    "lyme disease": "pathogen.borrelia_burgdorferi",
    "borrelia": "pathogen.borrelia_burgdorferi",
    "borrelia burgdorferi": "pathogen.borrelia_burgdorferi",
    # Anaplasmosis
    "anaplasmosis": "pathogen.anaplasma_phagocytophilum",
    "anaplasma": "pathogen.anaplasma_phagocytophilum",
    # Babesiosis
    "babesiosis": "pathogen.babesia_microti",
    "babesia": "pathogen.babesia_microti",
    # Leptospirosis
    "leptospirosis": "pathogen.leptospira",
    "leptospira": "pathogen.leptospira",
    "weil's disease": "pathogen.leptospira",
    "weils disease": "pathogen.leptospira",
}

# ICD-10 surface form: one letter, two digits, optional .N (1+ chars), optional A suffix
_ICD10_RE = re.compile(r"\b([A-Z][0-9]{2}(?:\.[0-9A-Z]{1,4})?)\b", re.IGNORECASE)
# SNOMED concept codes are 6-18 digits; the seed only goes up to 9 digits.
_SNOMED_RE = re.compile(r"\b([0-9]{6,18})\b")


def normalize_diagnosis(
    conn: duckdb.DuckDBPyConnection,
    diagnosis_text: str,
    vocabulary_hint: Optional[str] = None,
    min_confidence: float = 0.55,
) -> dict:
    """Normalise a free-text diagnosis to a ``pathogen.*`` slug.

    Returns ``{pathogen_id, snomed_code, icd10_code, confidence,
    match_reason}``. ``pathogen_id`` is ``None`` when nothing crosses
    the ``min_confidence`` bar; callers can inspect ``match_reason``
    for diagnostics.
    """
    text = (diagnosis_text or "").strip()
    if not text:
        return _empty_result("empty_input")

    lower = text.lower()
    hint = (vocabulary_hint or "").strip().lower() or None

    # ---- 1. Exact ICD-10 hit ---------------------------------------------
    if hint in (None, "icd10", "icd-10", "icd10cm", "icd-10-cm"):
        for m in _ICD10_RE.finditer(text):
            code = m.group(1).upper()
            pathogen_id = _pathogen_from_icd10(conn, code)
            if pathogen_id:
                codes = _codes_for_pathogen(conn, pathogen_id)
                return {
                    "pathogen_id": pathogen_id,
                    "snomed_code": codes.get("snomed"),
                    "icd10_code": code,
                    "confidence": 0.99,
                    "match_reason": f"exact ICD-10 code {code}",
                }

    # ---- 2. Exact SNOMED hit ---------------------------------------------
    if hint in (None, "snomed", "snomed_ct", "snomedct"):
        for m in _SNOMED_RE.finditer(text):
            code = m.group(1)
            pathogen_id = _pathogen_from_snomed(conn, code)
            if pathogen_id:
                codes = _codes_for_pathogen(conn, pathogen_id)
                return {
                    "pathogen_id": pathogen_id,
                    "snomed_code": code,
                    "icd10_code": codes.get("icd10"),
                    "confidence": 0.99,
                    "match_reason": f"exact SNOMED CT {code}",
                }

    # ---- 3. Curated alias hit --------------------------------------------
    # Prefer the longest matching alias so "rocky mountain spotted fever"
    # beats "spotted fever".
    alias_hits = [
        (alias, pid)
        for alias, pid in CURATED_ALIASES.items()
        if alias in lower
    ]
    if alias_hits:
        alias_hits.sort(key=lambda kv: len(kv[0]), reverse=True)
        alias, pathogen_id = alias_hits[0]
        codes = _codes_for_pathogen(conn, pathogen_id)
        return {
            "pathogen_id": pathogen_id,
            "snomed_code": codes.get("snomed"),
            "icd10_code": codes.get("icd10"),
            "confidence": 0.95,
            "match_reason": f"alias '{alias}'",
        }

    # ---- 4. Substring match against label / scientific_name / slug -------
    surfaces = _pathogen_surfaces(conn)
    for pid, forms in surfaces.items():
        for form in forms:
            if form and form.lower() in lower:
                codes = _codes_for_pathogen(conn, pid)
                return {
                    "pathogen_id": pid,
                    "snomed_code": codes.get("snomed"),
                    "icd10_code": codes.get("icd10"),
                    "confidence": 0.85,
                    "match_reason": f"substring '{form}'",
                }

    # ---- 5. Fuzzy similarity ---------------------------------------------
    best_pid: Optional[str] = None
    best_score = 0.0
    best_form: Optional[str] = None
    for pid, forms in surfaces.items():
        for form in forms:
            if not form:
                continue
            ratio = SequenceMatcher(None, form.lower(), lower).ratio()
            if ratio > best_score:
                best_score = ratio
                best_pid = pid
                best_form = form
    if best_pid and best_score >= min_confidence:
        codes = _codes_for_pathogen(conn, best_pid)
        return {
            "pathogen_id": best_pid,
            "snomed_code": codes.get("snomed"),
            "icd10_code": codes.get("icd10"),
            # Cap so we never out-rank an exact / alias hit.
            "confidence": min(best_score, 0.80),
            "match_reason": f"fuzzy match '{best_form}' (ratio={best_score:.2f})",
        }

    return _empty_result(
        f"no candidate above min_confidence={min_confidence}",
        best_score=best_score,
        best_form=best_form,
    )


# ---------------------------------------------------------------------------
# Helpers (cached per connection via attribute storage)
# ---------------------------------------------------------------------------
def _empty_result(reason: str, **extras: object) -> dict:
    out = {
        "pathogen_id": None,
        "snomed_code": None,
        "icd10_code": None,
        "confidence": 0.0,
        "match_reason": reason,
    }
    out.update(extras)
    return out


def _pathogen_from_icd10(conn: duckdb.DuckDBPyConnection, code: str) -> Optional[str]:
    """ICD-10 code (e.g. 'A20.0') -> pathogen.* slug via
    code.icd10.* --mappedTo--> focus.* <--targetsFocusArea-- pathogen.*"""
    rows = conn.execute(
        """
        WITH code_node AS (
            SELECT node_id
            FROM kg.property
            WHERE key = 'code' AND value_text = ?
              AND node_id LIKE 'code.icd10.%'
        ),
        focus AS (
            SELECT DISTINCT e.object_id AS focus_id
            FROM kg.edge e
            WHERE e.predicate = 'mappedTo'
              AND e.subject_id IN (SELECT node_id FROM code_node)
              AND e.object_id LIKE 'focus.%'
        )
        SELECT DISTINCT e.subject_id AS pathogen_id
        FROM kg.edge e
        WHERE e.predicate = 'targetsFocusArea'
          AND e.object_id IN (SELECT focus_id FROM focus)
          AND e.subject_id LIKE 'pathogen.%'
        """,
        (code,),
    ).fetchall()
    return rows[0][0] if rows else None


def _pathogen_from_snomed(conn: duckdb.DuckDBPyConnection, code: str) -> Optional[str]:
    """SNOMED CT code -> pathogen via mappedTo focus chain."""
    rows = conn.execute(
        """
        WITH code_node AS (
            SELECT node_id
            FROM kg.property
            WHERE key = 'code' AND value_text = ?
              AND node_id LIKE 'code.snomed.%'
        ),
        focus AS (
            SELECT DISTINCT e.object_id AS focus_id
            FROM kg.edge e
            WHERE e.predicate = 'mappedTo'
              AND e.subject_id IN (SELECT node_id FROM code_node)
              AND e.object_id LIKE 'focus.%'
        )
        SELECT DISTINCT e.subject_id AS pathogen_id
        FROM kg.edge e
        WHERE e.predicate = 'targetsFocusArea'
          AND e.object_id IN (SELECT focus_id FROM focus)
          AND e.subject_id LIKE 'pathogen.%'
        """,
        (code,),
    ).fetchall()
    return rows[0][0] if rows else None


_ICD10_PRIMARY_RE = re.compile(r"\b([A-Z][0-9]{2}(?:\.[0-9A-Z]{1,4})?)")


def _codes_for_pathogen(conn: duckdb.DuckDBPyConnection, pathogen_id: str) -> dict:
    """Return ``{'icd10': ..., 'snomed': ...}`` for a pathogen slug.

    For ICD-10, prefer extracting the *first* code from the pathogen's
    own ``icd10`` property (e.g. ``'A20.0-A20.9 (plague forms)'`` ->
    ``'A20.0'``) since that's curated as the primary clinical code.
    Fall back to walking the focus chain when the property is missing.

    For SNOMED we walk pathogen --targetsFocusArea--> focus.* and pick
    the first ``code.snomed.*`` that ``mappedTo`` the same focus -- the
    seeded SNOMED codes are already 1:1 per focus area.
    """
    # First: pull the human-readable icd10 string off the pathogen itself.
    icd10_text_row = conn.execute(
        "SELECT value_text FROM kg.property WHERE node_id = ? AND key = 'icd10'",
        (pathogen_id,),
    ).fetchone()
    icd10_primary: Optional[str] = None
    if icd10_text_row and icd10_text_row[0]:
        m = _ICD10_PRIMARY_RE.search(icd10_text_row[0])
        if m:
            icd10_primary = m.group(1)

    rows = conn.execute(
        """
        WITH focus AS (
            SELECT DISTINCT e.object_id AS focus_id
            FROM kg.edge e
            WHERE e.predicate = 'targetsFocusArea'
              AND e.subject_id = ?
              AND e.object_id LIKE 'focus.%'
        ),
        icd_codes AS (
            SELECT DISTINCT p.value_text AS code
            FROM kg.edge e
            JOIN kg.property p ON p.node_id = e.subject_id AND p.key = 'code'
            WHERE e.predicate = 'mappedTo'
              AND e.object_id IN (SELECT focus_id FROM focus)
              AND e.subject_id LIKE 'code.icd10.%'
        ),
        snomed_codes AS (
            SELECT DISTINCT p.value_text AS code
            FROM kg.edge e
            JOIN kg.property p ON p.node_id = e.subject_id AND p.key = 'code'
            WHERE e.predicate = 'mappedTo'
              AND e.object_id IN (SELECT focus_id FROM focus)
              AND e.subject_id LIKE 'code.snomed.%'
        )
        SELECT
            (SELECT code FROM icd_codes    ORDER BY code LIMIT 1) AS icd10,
            (SELECT code FROM snomed_codes ORDER BY code LIMIT 1) AS snomed
        """,
        (pathogen_id,),
    ).fetchone()
    if not rows:
        return {"icd10": icd10_primary, "snomed": None}
    return {
        "icd10": icd10_primary or rows[0],
        "snomed": rows[1],
    }


_SURFACE_CACHE: "dict[int, tuple[int, dict[str, list[str]]]]" = {}


def _pathogen_surfaces(conn: duckdb.DuckDBPyConnection) -> dict[str, list[str]]:
    """Collect every searchable surface-form per ``pathogen.*`` node.

    Includes the label, scientific_name property, the slug suffix
    (e.g. ``yersinia_pestis`` -> ``yersinia pestis``), and any
    ``causes`` -> ``disease.*`` labels. Cached per-connection (keyed by
    ``id(conn)``) and invalidated whenever the pathogen-row count
    changes.
    """
    pathogen_count = conn.execute(
        "SELECT COUNT(*) FROM kg.node WHERE node_type = 'pathogen'"
    ).fetchone()[0]
    cached = _SURFACE_CACHE.get(id(conn))
    if cached is not None and cached[0] == pathogen_count:
        return cached[1]

    rows = conn.execute(
        """
        SELECT
            n.node_id,
            n.label,
            sci.value_text AS scientific_name
        FROM kg.node n
        LEFT JOIN kg.property sci
               ON sci.node_id = n.node_id AND sci.key = 'scientific_name'
        WHERE n.node_type = 'pathogen'
        """
    ).fetchall()

    disease_rows = conn.execute(
        """
        SELECT e.subject_id, d.label
        FROM kg.edge e
        JOIN kg.node d ON d.node_id = e.object_id
        WHERE e.predicate = 'causes'
          AND d.node_type = 'disease'
        """
    ).fetchall()
    disease_by_pid: dict[str, list[str]] = {}
    for pid, dlabel in disease_rows:
        disease_by_pid.setdefault(pid, []).append(dlabel)

    surfaces: dict[str, list[str]] = {}
    for pid, label, sci in rows:
        suffix = pid.split(".", 1)[1] if "." in pid else pid
        readable_slug = suffix.replace("_", " ")
        forms = [label, sci, readable_slug, *disease_by_pid.get(pid, [])]
        # De-duplicate and drop empties while preserving order.
        seen: set[str] = set()
        ordered: list[str] = []
        for f in forms:
            if not f:
                continue
            if f in seen:
                continue
            seen.add(f)
            ordered.append(f)
        surfaces[pid] = ordered

    _SURFACE_CACHE[id(conn)] = (pathogen_count, surfaces)
    return surfaces
