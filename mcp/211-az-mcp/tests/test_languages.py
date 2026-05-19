"""Language-coverage tests for the 211 Arizona MCP server.

The plan calls for English + Spanish direct-operator coverage and
explicit indigenous-language access pathways through partner
organisations (ITCA-TEC, Navajo Epidemiology Center, IHS, etc.).
These tests assert the resource payload spells those out so the
NotificationAgent can render an accurate "languages we can help in"
panel and the agents can warm-transfer to the right partner.
"""

from __future__ import annotations

import json

from az211_mcp.mock_data import LANGUAGES_SUPPORTED
from az211_mcp.server import languages_resource


def test_english_and_spanish_are_direct_operator_languages() -> None:
    direct = LANGUAGES_SUPPORTED["direct_operator_languages"]
    assert "English" in direct
    assert "Spanish" in direct


def test_interpreter_service_is_documented() -> None:
    interp = LANGUAGES_SUPPORTED["interpreter_service"]
    assert interp["provider"]
    # 200+ languages is the canonical Language Line claim.
    assert "200" in interp["languages"] or "language" in interp["languages"].lower()


def test_indigenous_language_pathways_include_navajo() -> None:
    paths = LANGUAGES_SUPPORTED["indigenous_language_pathways"]
    names = [p["language"] for p in paths]
    assert any("Navajo" in n or "Diné" in n for n in names)


def test_indigenous_language_pathways_include_oodham_and_apache_and_hopi() -> None:
    paths = LANGUAGES_SUPPORTED["indigenous_language_pathways"]
    names = " ".join(p["language"] for p in paths)
    assert "O'odham" in names
    assert "Apache" in names
    assert "Hopi" in names


def test_indigenous_pathway_entries_have_partner_url_and_pathway() -> None:
    for p in LANGUAGES_SUPPORTED["indigenous_language_pathways"]:
        assert p["language"]
        assert p["pathway"]
        # URL should point at the named partner organisation.
        assert p["url"].startswith("http")


def test_languages_resource_returns_valid_json_with_required_keys() -> None:
    # The MCP resource is registered as a function; FastMCP wraps it
    # so calling it directly returns the JSON payload string.
    payload = languages_resource()
    parsed = json.loads(payload)
    assert "direct_operator_languages" in parsed
    assert "indigenous_language_pathways" in parsed
    assert "English" in parsed["direct_operator_languages"]
    assert "Spanish" in parsed["direct_operator_languages"]
