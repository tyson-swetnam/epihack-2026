"""Tests for the diagnosis normaliser.

Seeds a tiny synthetic crosswalk:

* ``pathogen.yersinia_pestis`` -> ``focus.plague``
* ``code.icd10.a200`` (display 'A20.0') -> ``focus.plague``
* ``code.snomed.plague`` (display '58750007') -> ``focus.plague``
* ``pathogen.wnv`` -> ``focus.wnv`` + the WNV SNOMED + A92.3 code

and then asserts the four canonical surface forms requested in the
brief (``plague`` / ``Y. pestis`` / ``Yersinia pestis`` / ``A20.0``)
all resolve to ``pathogen.yersinia_pestis``.
"""

from __future__ import annotations

import duckdb
import pytest

from knowledge_graph_mcp import normalize


@pytest.fixture()
def kg_conn() -> duckdb.DuckDBPyConnection:
    c = duckdb.connect(":memory:")
    c.execute("CREATE SCHEMA kg;")
    c.execute(
        "CREATE TABLE kg.node ("
        "  node_id VARCHAR PRIMARY KEY,"
        "  node_type VARCHAR NOT NULL,"
        "  label VARCHAR NOT NULL,"
        "  description VARCHAR,"
        "  source_fig VARCHAR);"
    )
    c.execute(
        "CREATE TABLE kg.edge ("
        "  edge_id BIGINT PRIMARY KEY,"
        "  subject_id VARCHAR NOT NULL,"
        "  predicate VARCHAR NOT NULL,"
        "  object_id VARCHAR NOT NULL,"
        "  source_fig VARCHAR);"
    )
    c.execute(
        "CREATE TABLE kg.property ("
        "  node_id VARCHAR NOT NULL,"
        "  key VARCHAR NOT NULL,"
        "  value_text VARCHAR,"
        "  value_num DOUBLE,"
        "  PRIMARY KEY (node_id, key));"
    )

    nodes = [
        # Focus areas
        ("focus.plague", "focus_area", "Plague", None, "test"),
        ("focus.wnv", "focus_area", "West Nile", None, "test"),
        # Pathogens
        ("pathogen.yersinia_pestis", "pathogen", "Yersinia pestis",
         "Bubonic / pneumonic / septicemic plague.", "test"),
        ("pathogen.wnv", "pathogen", "West Nile virus (WNV)",
         "Flavivirus arbovirus.", "test"),
        # Codes
        ("code.icd10.a200", "icd10_code", "A20.0 Bubonic plague", None, "test"),
        ("code.icd10.a923", "icd10_code", "A92.3 West Nile virus infection", None, "test"),
        ("code.snomed.plague", "snomed_concept", "SNOMED CT 58750007 Plague", None, "test"),
        ("code.snomed.wnv", "snomed_concept", "SNOMED CT 230145002 WNV", None, "test"),
        # Disease aliases via 'causes' edges
        ("disease.plague", "disease", "Plague", None, "test"),
        ("disease.west_nile_fever", "disease", "West Nile fever", None, "test"),
    ]
    c.executemany(
        "INSERT INTO kg.node VALUES (?, ?, ?, ?, ?)", nodes
    )

    edges = [
        (1, "pathogen.yersinia_pestis", "targetsFocusArea", "focus.plague", "test"),
        (2, "pathogen.wnv", "targetsFocusArea", "focus.wnv", "test"),
        (3, "code.icd10.a200", "mappedTo", "focus.plague", "test"),
        (4, "code.icd10.a923", "mappedTo", "focus.wnv", "test"),
        (5, "code.snomed.plague", "mappedTo", "focus.plague", "test"),
        (6, "code.snomed.wnv", "mappedTo", "focus.wnv", "test"),
        (7, "pathogen.yersinia_pestis", "causes", "disease.plague", "test"),
        (8, "pathogen.wnv", "causes", "disease.west_nile_fever", "test"),
    ]
    c.executemany(
        "INSERT INTO kg.edge VALUES (?, ?, ?, ?, ?)", edges
    )

    props = [
        ("pathogen.yersinia_pestis", "scientific_name", "Yersinia pestis", None),
        ("pathogen.yersinia_pestis", "icd10", "A20.0-A20.9 (plague forms)", None),
        ("pathogen.wnv", "scientific_name", "Orthoflavivirus nilense (West Nile virus)", None),
        ("pathogen.wnv", "icd10", "A92.3 (West Nile virus infection)", None),
        ("code.icd10.a200", "code", "A20.0", None),
        ("code.icd10.a200", "system", "ICD-10-CM", None),
        ("code.icd10.a923", "code", "A92.3", None),
        ("code.icd10.a923", "system", "ICD-10-CM", None),
        ("code.snomed.plague", "code", "58750007", None),
        ("code.snomed.plague", "system", "SNOMED CT", None),
        ("code.snomed.wnv", "code", "230145002", None),
        ("code.snomed.wnv", "system", "SNOMED CT", None),
    ]
    c.executemany(
        "INSERT INTO kg.property VALUES (?, ?, ?, ?)", props
    )
    return c


# ---------------------------------------------------------------------------
# Mandatory canonical-forms test from the brief
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "surface_form",
    ["plague", "Y. pestis", "Yersinia pestis", "A20.0"],
)
def test_plague_surface_forms_all_resolve(kg_conn, surface_form):
    out = normalize.normalize_diagnosis(kg_conn, surface_form)
    assert out["pathogen_id"] == "pathogen.yersinia_pestis", (
        f"surface form {surface_form!r} resolved to {out!r}"
    )
    assert out["confidence"] >= 0.9
    # ICD-10 + SNOMED codes ride along for downstream HL7 / FHIR shaping.
    assert out["icd10_code"] == "A20.0"
    assert out["snomed_code"] == "58750007"


# ---------------------------------------------------------------------------
# Mode-specific assertions
# ---------------------------------------------------------------------------
def test_exact_icd10_beats_substring(kg_conn):
    # 'A20.0' should fire the exact-ICD-10 path with confidence 0.99,
    # not the substring path.
    out = normalize.normalize_diagnosis(kg_conn, "patient presenting with A20.0")
    assert out["pathogen_id"] == "pathogen.yersinia_pestis"
    assert out["match_reason"].startswith("exact ICD-10")
    assert out["confidence"] == pytest.approx(0.99)


def test_exact_snomed(kg_conn):
    out = normalize.normalize_diagnosis(kg_conn, "58750007", vocabulary_hint="snomed")
    assert out["pathogen_id"] == "pathogen.yersinia_pestis"
    assert out["match_reason"].startswith("exact SNOMED")


def test_alias_lookup_handles_punctuation(kg_conn):
    # 'Y. pestis' carries a period that the alias map normalises through
    # lowercase substring match (the alias entry is 'y. pestis').
    out = normalize.normalize_diagnosis(kg_conn, "Suspected Y. pestis infection")
    assert out["pathogen_id"] == "pathogen.yersinia_pestis"
    assert out["match_reason"].startswith("alias")


def test_wnv_disambiguation(kg_conn):
    # Make sure other pathogens still work and we don't accidentally bias
    # toward Y. pestis.
    out = normalize.normalize_diagnosis(kg_conn, "West Nile virus")
    assert out["pathogen_id"] == "pathogen.wnv"
    assert out["icd10_code"] == "A92.3"
    assert out["snomed_code"] == "230145002"


def test_vocabulary_hint_skips_other_paths(kg_conn):
    # If the caller hints 'icd10' and the input is a SNOMED-shaped string
    # (8 digits), we should NOT try the SNOMED path. The fuzzy fallback
    # may still grab something, but it can't be the exact-SNOMED route.
    out = normalize.normalize_diagnosis(
        kg_conn, "58750007", vocabulary_hint="icd10"
    )
    assert not out["match_reason"].startswith("exact SNOMED")


def test_empty_input(kg_conn):
    out = normalize.normalize_diagnosis(kg_conn, "")
    assert out["pathogen_id"] is None
    assert out["confidence"] == 0.0


def test_unknown_input_returns_no_match(kg_conn):
    out = normalize.normalize_diagnosis(
        kg_conn, "completely-unrelated-string-zzz", min_confidence=0.99
    )
    assert out["pathogen_id"] is None
