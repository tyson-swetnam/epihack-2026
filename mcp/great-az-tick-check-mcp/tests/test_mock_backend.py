"""Tests for the mock backend.

Covers:
- The full create -> status (received -> identifying -> testing ->
  complete) flow.
- The species-guess response shape, including the `verify_with_lab`
  flag and the alternatives list.
- The deterministic Walker-lab mailing address text (so a code change
  that breaks the address fails CI loudly).
- Mailing-label URL generation including format validation.
- The pathogens-screened reference list shape.

All synthetic; no live credentials required.
"""

from __future__ import annotations

import pytest

from great_az_tick_check_mcp.client import (
    AZ_TICK_SPECIES,
    PATHOGENS_SCREENED,
    WALKER_LAB_MAILING_ADDRESS,
    GreatAZTickCheckClient,
)


# ----------------------------------------------------------------- fixtures
@pytest.fixture
def client() -> GreatAZTickCheckClient:
    """Fresh mock client (no GATTC_BACKEND_URL)."""
    return GreatAZTickCheckClient(backend_url=None)


SAMPLE_KWARGS = dict(
    submitter_email="hiker@example.com",
    submitter_name="Pat Hiker",
    county="Santa Cruz",
    zip_code="85624",
    tick_date="2026-05-12",
    host="human",
    attachment_duration_hours=6.0,
    body_location="leg",
    photo_url="https://example.com/tick.jpg",
    consent_to_research_use=True,
)


# ----------------------------------------------------------------- address
def test_mailing_address_matches_resources_md():
    """The address text must match wildlife/resources.md verbatim.

    A drift here means submitters might mail their ticks to the wrong
    place -- worth a hard CI failure.
    """
    expected_lines = [
        "Dr. Kathleen Walker",
        "Forbes 410, Department of Entomology",
        "P.O. Box 210036",
        "University of Arizona",
        "Tucson, AZ 85721",
    ]
    assert WALKER_LAB_MAILING_ADDRESS == "\n".join(expected_lines)


# ---------------------------------------------------------- create + status
def test_create_submission_returns_expected_keys(client):
    out = client.create_submission(**SAMPLE_KWARGS)
    assert set(out) >= {
        "submission_id",
        "mailing_address",
        "mailing_label_url",
        "status_url",
        "estimated_turnaround_days",
        "backend_mode",
    }
    assert out["backend_mode"] == "mock"
    assert out["mailing_address"] == WALKER_LAB_MAILING_ADDRESS
    sid = out["submission_id"]
    # short-but-not-tiny ID
    assert 8 <= len(sid) <= 32
    assert out["status_url"].endswith(f"/{sid}")
    assert out["mailing_label_url"].endswith(f"/{sid}.pdf")
    assert out["estimated_turnaround_days"] > 0


def test_full_status_progression(client):
    sid = client.create_submission(**SAMPLE_KWARGS)["submission_id"]

    # The mock advances one step per poll.
    s1 = client.get_status(sid)
    assert s1["status"] == "received"
    assert "species" not in s1
    assert "pathogens_tested" not in s1

    s2 = client.get_status(sid)
    assert s2["status"] == "identifying"

    s3 = client.get_status(sid)
    assert s3["status"] == "testing"

    s4 = client.get_status(sid)
    assert s4["status"] == "complete"
    assert "species" in s4
    assert s4["species"]["scientific_name"]
    assert isinstance(s4["pathogens_tested"], list)
    assert len(s4["pathogens_tested"]) == len(PATHOGENS_SCREENED)
    for row in s4["pathogens_tested"]:
        assert {"scientific_name", "disease", "icd10", "result", "method"} <= row.keys()

    # Subsequent polls remain `complete`.
    s5 = client.get_status(sid)
    assert s5["status"] == "complete"


def test_unknown_submission_id_is_not_found(client):
    out = client.get_status("does-not-exist-0000")
    assert out["status"] == "not_found"


def test_invalid_host_rejected(client):
    bad = dict(SAMPLE_KWARGS, host="cow")  # only human/pet/environment allowed
    with pytest.raises(ValueError):
        client.create_submission(**bad)


# -------------------------------------------------------------- mailing label
def test_mailing_label_pdf_and_png(client):
    sid = client.create_submission(**SAMPLE_KWARGS)["submission_id"]
    pdf = client.mailing_label(sid, fmt="pdf")
    png = client.mailing_label(sid, fmt="png")
    assert pdf["url"].endswith(f"/{sid}.pdf")
    assert png["url"].endswith(f"/{sid}.png")
    assert pdf["mailing_address"] == WALKER_LAB_MAILING_ADDRESS


def test_mailing_label_rejects_bad_format(client):
    sid = client.create_submission(**SAMPLE_KWARGS)["submission_id"]
    with pytest.raises(ValueError):
        client.mailing_label(sid, fmt="jpeg")


# ----------------------------------------------------------------- species
def test_species_guess_shape(client):
    out = client.species_guess(
        "https://example.com/tick.jpg", lat=31.54, lon=-110.76
    )
    assert out["verify_with_lab"] is True
    assert out["lab_contact"] == WALKER_LAB_MAILING_ADDRESS
    bg = out["best_guess"]
    assert {"common_name", "scientific_name", "confidence", "notes"} <= bg.keys()
    # Confidence is intentionally low -- we never want callers acting on it
    # as a definitive ID.
    assert 0.0 < bg["confidence"] < 1.0
    # Alternatives cover the other AZ-relevant ticks.
    assert len(out["alternatives"]) == len(AZ_TICK_SPECIES) - 1
    for alt in out["alternatives"]:
        assert {"common_name", "scientific_name", "notes"} <= alt.keys()


# ----------------------------------------------------------- pathogen list
def test_pathogens_screened_contents():
    """Spot-check the reference list. ICD-10 for Rickettsia rickettsii
    must match standards.sql (A77.0); other codes match pathogens.sql."""
    by_name = {p["scientific_name"]: p for p in PATHOGENS_SCREENED}
    assert by_name["Rickettsia rickettsii"]["icd10"] == "A77.0"
    assert by_name["Borrelia burgdorferi"]["icd10"].startswith("A69.2")
    assert by_name["Babesia microti"]["icd10"] == "B60.0"
    assert by_name["Anaplasma phagocytophilum"]["icd10"].startswith("A77.4")
    assert by_name["Ehrlichia chaffeensis"]["icd10"].startswith("A77.4")
    # Every row carries the keys the MCP tool advertises.
    for p in PATHOGENS_SCREENED:
        assert {
            "pathogen_id",
            "scientific_name",
            "disease",
            "icd10",
            "icd10_description",
            "primary_vector",
        } <= p.keys()


# ------------------------------------------------------------- HTTP backend
def test_http_backend_raises_until_real_api_exists():
    """If GATTC_BACKEND_URL is set, calls must fail loudly rather than
    silently falling back to mock data. A deployer who mistypes the
    URL needs to see the failure immediately."""
    c = GreatAZTickCheckClient(backend_url="https://example.invalid/api")
    assert c.mode == "http"
    with pytest.raises(NotImplementedError):
        c.create_submission(**SAMPLE_KWARGS)
