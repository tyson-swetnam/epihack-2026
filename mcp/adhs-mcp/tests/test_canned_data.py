"""Tests for the canned-data constants.

Pin the numbers that appear in `heat/04-vulnerable-populations.md` and
`schema/heat.sql` so a drift fails CI loudly. Contributors updating
the numbers from a new ADHS report must also bump these assertions.
"""

from __future__ import annotations

from adhs_mcp import canned_data as CD


# ----------------------------------------------------------- heat-mortality
def test_heat_mortality_covers_2013_to_2024():
    years = [r["year"] for r in CD.HEAT_MORTALITY_SUMMARY]
    assert years == list(range(2013, 2025))


def test_heat_mortality_2023_equals_990():
    """`heat/04-vulnerable-populations.md`: 990 heat-related deaths in 2023."""
    by_year = {r["year"]: r for r in CD.HEAT_MORTALITY_SUMMARY}
    assert by_year[2023]["statewide_deaths"] == 990


def test_heat_mortality_2024_equals_602():
    """Task spec: 602 in 2024."""
    by_year = {r["year"]: r for r in CD.HEAT_MORTALITY_SUMMARY}
    assert by_year[2024]["statewide_deaths"] == 602


def test_heat_mortality_cumulative_2013_2024_at_least_4320():
    """`heat/04-vulnerable-populations.md`: >4,320 deaths 2013-2024."""
    total = sum(r["statewide_deaths"] for r in CD.HEAT_MORTALITY_SUMMARY)
    assert total >= 4320


def test_heat_mortality_er_visits_2024_is_4298():
    """`heat/04-vulnerable-populations.md`: ~4,298 ER visits per year."""
    by_year = {r["year"]: r for r in CD.HEAT_MORTALITY_SUMMARY}
    assert by_year[2024]["estimated_er_visits"] == 4298


def test_heat_mortality_maricopa_share_dominates():
    """Maricopa carries the overwhelming majority of statewide deaths.

    Sanity check: per the MCDPH heat-surveillance program (running
    since 2006), Maricopa is consistently >75% of Arizona's annual
    heat-mortality total. If a future revision drops below 70%
    statewide, someone needs to revisit the per-county split.
    """
    for r in CD.HEAT_MORTALITY_SUMMARY:
        share = r["maricopa_deaths"] / r["statewide_deaths"]
        assert share >= 0.70, (
            f"{r['year']}: Maricopa share {share:.0%} below 70%"
        )


def test_heat_mortality_county_breakdown_sums_to_statewide():
    """Per-county counts must add up exactly to the statewide total."""
    for r in CD.HEAT_MORTALITY_SUMMARY:
        s = (
            r["maricopa_deaths"]
            + r["pima_deaths"]
            + r["yuma_deaths"]
            + r["other_counties_deaths"]
        )
        assert s == r["statewide_deaths"], (
            f"{r['year']}: county sum {s} != statewide {r['statewide_deaths']}"
        )


# ------------------------------------------------------------- recent cases
def test_recent_cases_has_wnv_maricopa_12_week_2024_series():
    rows = CD.RECENT_CASES["WNV"]
    assert len(rows) == 12
    assert all(r["county"] == "Maricopa" for r in rows)
    assert all(r["week_of"].startswith("2024-") for r in rows)
    # Series peaks somewhere in late July / early August.
    peak = max(rows, key=lambda r: r["confirmed"])
    assert "2024-07" in peak["week_of"] or "2024-08" in peak["week_of"]


def test_recent_cases_hantavirus_covers_coconino_and_apache():
    rows = CD.RECENT_CASES["HANTAVIRUS"]
    counties = {r["county"] for r in rows}
    assert "Coconino" in counties
    assert "Apache" in counties


def test_recent_cases_has_all_accepted_pathogens():
    """Every accepted pathogen has at least a stub row."""
    for p in CD.ACCEPTED_PATHOGENS:
        assert p in CD.RECENT_CASES, f"{p}: missing canned rows"
        assert len(CD.RECENT_CASES[p]) >= 1


# ----------------------------------------------------------- arbo surveillance
def test_arbovirus_surveillance_has_maricopa_2024_wnv_rows():
    rows = [
        r for r in CD.ARBOVIRUS_SURVEILLANCE
        if r["county"] == "Maricopa" and r["pathogen"] == "WNV"
        and r["surv_year"] == 2024
    ]
    assert len(rows) == 12  # 12-week series, matching RECENT_CASES["WNV"]


def test_arbovirus_surveillance_maricopa_uses_800_trap_footprint():
    """`wildlife/resources.md`: MCESD operates 800+ traps county-wide."""
    rows = [
        r for r in CD.ARBOVIRUS_SURVEILLANCE if r["county"] == "Maricopa"
    ]
    assert rows, "no Maricopa arbovirus rows in canned data"
    assert all(r["trap_network_size"] == 800 for r in rows)


# -------------------------------------------------------------------- URLs
def test_heat_preparedness_network_arcgis_url():
    """`schema/heat.sql` ties the ADHS Heat Preparedness map to this URL."""
    assert (
        CD.HEAT_PREPAREDNESS_NETWORK["arcgis_experience_url"]
        == "https://experience.arcgis.com/experience/c5bdf9ab90894e1baa5860c450dedb3b"
    )


def test_vbzd_program_url():
    assert CD.VBZD_PROGRAM["url"].startswith("https://www.azdhs.gov/")
    assert "vector-borne-zoonotic-diseases" in CD.VBZD_PROGRAM["url"]


def test_heat_mortality_portal_url():
    """`schema/heat.sql` (`tool.adhs_heat_mortality_dash`) anchors this URL."""
    assert (
        CD.ADHS_HEAT_MORTALITY_PORTAL_URL
        == "https://pub.azdhs.gov/health-stats/report/heat/"
    )


# ----------------------------------------------- summary text + acronyms
def test_summary_text_mentions_headline_numbers():
    text = CD.HEAT_MORTALITY_SUMMARY_TEXT
    assert "4,320" in text
    assert "990" in text
    assert "602" in text
    assert "4,298" in text


def test_render_pathogen_acronyms_includes_every_pathogen():
    rendered = CD.render_pathogen_acronyms_text()
    for p in CD.PATHOGEN_ACRONYMS:
        assert p["acronym"] in rendered
