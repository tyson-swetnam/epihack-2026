"""Tests for the reportable-conditions canned list.

Spec contract: every entry has either an ICD-10 code OR a SNOMED CT
concept (or both). Codes are sourced from `schema/deep/standards.sql`
(T67.0XXA heatstroke, A20.* plague, A77.0 RMSF, B33.4 hantavirus,
A21.* tularemia, A92.3 / A92.30-A92.39 West Nile, A82.* rabies) plus
SNOMED CT concepts (dengue 38362002, Zika 3928002, SLE 16541001) for
the arboviral conditions standards.sql doesn't yet seed an ICD-10
code for.
"""

from __future__ import annotations

import re

from adhs_mcp import canned_data as CD
from adhs_mcp.server import ReportableConditionRow


# --------------------------------------------------------------- contract
def test_every_row_has_icd10_or_snomed():
    """Spec contract: at least one of ICD-10 or SNOMED is populated."""
    for r in CD.REPORTABLE_CONDITIONS:
        assert r["icd10"] or r["snomed_ct"], (
            f"{r['condition']}: neither ICD-10 nor SNOMED CT present"
        )


def test_every_row_round_trips_through_pydantic_model():
    for r in CD.REPORTABLE_CONDITIONS:
        model = ReportableConditionRow.model_validate(r)
        assert model.condition
        assert model.az_reporting_rule


# ---------------------------------------------- ICD-10 / SNOMED format
ICD10_RE = re.compile(r"^[A-Z]\d{2}(\.[0-9A-Z]+)?$")
SNOMED_RE = re.compile(r"^\d{6,}$")


def test_icd10_codes_use_dotted_format():
    """`schema/deep/standards.sql` stores ICD-10 codes in the dotted form."""
    for r in CD.REPORTABLE_CONDITIONS:
        if r["icd10"] is None:
            continue
        assert ICD10_RE.match(r["icd10"]), f"bad ICD-10: {r['icd10']!r}"


def test_snomed_codes_look_like_concept_ids():
    for r in CD.REPORTABLE_CONDITIONS:
        if r["snomed_ct"] is None:
            continue
        assert SNOMED_RE.match(r["snomed_ct"]), f"bad SNOMED: {r['snomed_ct']!r}"


# ------------------------------------------------------- spot-check codes
def test_rmsf_icd10_matches_standards_sql():
    """schema/deep/standards.sql: A77.0 Spotted fever due to R. rickettsii."""
    rmsf = next(
        r for r in CD.REPORTABLE_CONDITIONS if "Rocky Mountain" in r["condition"]
    )
    assert rmsf["icd10"] == "A77.0"
    assert rmsf["snomed_ct"] == "186772009"


def test_hantavirus_icd10_matches_standards_sql():
    """schema/deep/standards.sql: B33.4 Hantavirus (cardio-)pulmonary syndrome."""
    hps = next(
        r for r in CD.REPORTABLE_CONDITIONS if "Hantavirus" in r["condition"]
    )
    assert hps["icd10"] == "B33.4"
    assert hps["snomed_ct"] == "47523006"


def test_heatstroke_codes_present():
    """schema/deep/standards.sql: T67.0XXA heatstroke + SNOMED 39579001."""
    hs = next(
        r for r in CD.REPORTABLE_CONDITIONS
        if "Heatstroke" in r["condition"]
    )
    assert hs["icd10"] == "T67.0XXA"
    assert hs["snomed_ct"] == "39579001"


def test_west_nile_codes_present():
    """schema/deep/standards.sql: A92.30 + SNOMED 230145002."""
    wnv = next(
        r for r in CD.REPORTABLE_CONDITIONS
        if "West Nile" in r["condition"]
    )
    assert wnv["icd10"] == "A92.30"
    assert wnv["snomed_ct"] == "230145002"


def test_plague_codes_present():
    """schema/deep/standards.sql: A20.x + SNOMED 58750007."""
    plague = next(
        r for r in CD.REPORTABLE_CONDITIONS if r["condition"].startswith("Plague")
    )
    assert plague["icd10"].startswith("A20")
    assert plague["snomed_ct"] == "58750007"


def test_rabies_animal_and_human_both_present():
    rabies = [r for r in CD.REPORTABLE_CONDITIONS if "Rabies" in r["condition"]]
    cats = {r["condition"] for r in rabies}
    assert any("human" in c.lower() for c in cats)
    assert any("animal" in c.lower() for c in cats)


# ------------------------------------------------------ NNDSS coverage
def test_zoonotic_rows_carry_nndss_condition():
    """Every reportable condition standards.sql encodes as a NEDSS row
    surfaces a CDC NNDSS condition string. The heat row legitimately
    has no NNDSS condition (heat illness is not nationally notifiable);
    every other row must."""
    non_heat = [
        r for r in CD.REPORTABLE_CONDITIONS if r["category"] != "environmental"
    ]
    for r in non_heat:
        assert r["nndss_condition"], (
            f"{r['condition']}: missing NNDSS condition"
        )
