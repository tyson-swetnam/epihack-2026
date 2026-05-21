"""Canned data for the ADHS MCP server.

ADHS surveillance data is published as PDFs (annual heat-mortality
reports, weekly arbovirus summaries) and ArcGIS Experience dashboards
(the Heat Preparedness Network map). There is no documented public
REST API. To keep the rest of the EpiHack stack moving without
scraping PDFs at request time, this module captures stable canned
values sourced from:

- ``heat/04-vulnerable-populations.md`` for the ADHS heat-mortality
  headline numbers (>4,320 deaths 2013-2024; 990 in 2023; ~4,298 ER
  visits/year; Maricopa surveillance since 2006).
- ``schema/heat.sql`` for the same statewide totals encoded as
  knowledge-graph properties on the ``group.heat`` node, plus the
  ADHS Heat Preparedness Network ArcGIS map URL on
  ``tool.adhs_heat_map``, the heat-mortality dashboard URL on
  ``tool.adhs_heat_mortality_dash``, the Governor's Extreme Heat
  Preparedness Plan launch date, and the MAG HRN season anchor.
- ``schema/deep/standards.sql`` for ICD-10-CM, SNOMED CT, and CDC
  NNDSS codes mapping to the ADHS-reportable conditions (T67.0XXA
  heatstroke, A20.* plague, A77.0 RMSF, B33.4 hantavirus, A21.*
  tularemia, A92.3 / A92.30-A92.39 West Nile, A82.* rabies).
- ``wildlife/resources.md`` for the Maricopa Vector Control 800-trap
  network footprint (the County feeds weekly summaries to ADHS).
- The ADHS Vector-Borne & Zoonotic Diseases program page at
  <https://www.azdhs.gov/preparedness/epidemiology-disease-control/
  vector-borne-zoonotic-diseases/> for the program description.

Contributors updating these numbers from a new ADHS report should
only need to edit this file -- the FastMCP tools in ``server.py``
read these constants directly.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Reference URLs (single source of truth -- referenced by tools + resources).
# ---------------------------------------------------------------------------
ADHS_HOME_URL: str = "https://www.azdhs.gov/"
ADHS_VBZD_PROGRAM_URL: str = (
    "https://www.azdhs.gov/preparedness/epidemiology-disease-control/"
    "vector-borne-zoonotic-diseases/"
)
ADHS_HEAT_MORTALITY_PORTAL_URL: str = "https://pub.azdhs.gov/health-stats/report/heat/"
ADHS_HEAT_MORTALITY_2023_PDF_URL: str = (
    "https://www.azdhs.gov/documents/preparedness/epidemiology-disease-control/"
    "extreme-weather/pubs/heat-related-mortality-year-2012-2023.pdf"
)
ADHS_HEAT_PREPAREDNESS_MAP_URL: str = (
    "https://experience.arcgis.com/experience/c5bdf9ab90894e1baa5860c450dedb3b"
)
ADHS_HEAT_PROGRAM_URL: str = (
    "https://www.azdhs.gov/preparedness/epidemiology-disease-control/"
    "extreme-weather/heat-safety/heat-preparedness/index.php"
)

# Generic placeholder for a per-row source_report_url -- the canned
# arbovirus summary points back at the ADHS VBZD program page until a
# specific weekly-summary PDF URL pattern is locked in.
_ARBO_SOURCE_URL: str = ADHS_VBZD_PROGRAM_URL


# ---------------------------------------------------------------------------
# Pathogens & acronyms (mirror vectorsurv://disease-acronyms but pinned
# to the ADHS terminology / reportable-conditions list).
# ---------------------------------------------------------------------------
PATHOGEN_ACRONYMS: list[dict[str, str]] = [
    {"acronym": "WNV",         "name": "West Nile virus",
     "category": "arbovirus"},
    {"acronym": "SLEV",        "name": "St. Louis encephalitis virus",
     "category": "arbovirus"},
    {"acronym": "WEEV",        "name": "Western equine encephalitis virus",
     "category": "arbovirus"},
    {"acronym": "DENV",        "name": "Dengue virus",
     "category": "arbovirus"},
    {"acronym": "ZIKV",        "name": "Zika virus",
     "category": "arbovirus"},
    {"acronym": "CHIKV",       "name": "Chikungunya virus",
     "category": "arbovirus"},
    {"acronym": "HANTAVIRUS",  "name": "Hantavirus pulmonary syndrome (Sin Nombre virus)",
     "category": "zoonotic"},
    {"acronym": "PLAGUE",      "name": "Yersinia pestis (plague)",
     "category": "zoonotic"},
    {"acronym": "RABIES",      "name": "Rabies virus",
     "category": "zoonotic"},
    {"acronym": "RMSF",        "name": "Rocky Mountain spotted fever (Rickettsia rickettsii)",
     "category": "tick-borne"},
    {"acronym": "TULAREMIA",   "name": "Tularemia (Francisella tularensis)",
     "category": "zoonotic"},
]

# Set of pathogens accepted by `adhs_recent_cases`. Kept as a tuple so
# it can be re-used as a Literal[] without re-quoting each value.
ACCEPTED_PATHOGENS: tuple[str, ...] = (
    "WNV", "SLEV", "DENV", "ZIKV",
    "HANTAVIRUS", "PLAGUE", "RABIES",
    "RMSF", "TULAREMIA",
)


# ---------------------------------------------------------------------------
# Weekly case counts -- `adhs_recent_cases`.
#
# Structure: dict keyed by pathogen acronym; each entry is a list of
# weekly rows. Realistic 12-week 2024 series for WNV in Maricopa and
# hantavirus in Coconino / Apache; stubs for the rest. Each row has the
# same keys as the `RecentCaseRow` pydantic model in `server.py`.
#
# Note on shape: ``week_of`` is a Monday (ISO date) so a downstream
# join with VectorSurv's weekly trap data is direct.
# ---------------------------------------------------------------------------
def _wnv_maricopa_2024() -> list[dict[str, Any]]:
    """12-week realistic series for Maricopa WNV cases, summer 2024.

    Numbers chosen to bend like a typical late-monsoon WNV epicurve --
    a slow June ramp, a July-August peak, a September tail. The
    cumulative total (104 confirmed + 18 probable = 122) is at the
    lower end of recent Maricopa season totals; 2021 was the
    "unprecedented" outlier documented in
    https://www.cdc.gov/mmwr/volumes/72/wr/mm7217a1.htm.
    """
    # (week_of_monday, confirmed, probable)
    series = [
        ("2024-06-17",  1, 0),
        ("2024-06-24",  2, 1),
        ("2024-07-01",  3, 1),
        ("2024-07-08",  6, 2),
        ("2024-07-15", 10, 2),
        ("2024-07-22", 14, 3),
        ("2024-07-29", 18, 3),
        ("2024-08-05", 17, 2),
        ("2024-08-12", 14, 2),
        ("2024-08-19", 10, 1),
        ("2024-08-26",  6, 1),
        ("2024-09-02",  3, 0),
    ]
    return [
        {
            "week_of": wk,
            "county": "Maricopa",
            "confirmed": c,
            "probable": p,
            "source_report_url": _ARBO_SOURCE_URL,
        }
        for wk, c, p in series
    ]


def _hantavirus_2024() -> list[dict[str, Any]]:
    """Sparse hantavirus cases in Coconino + Apache counties, 2024.

    Sin Nombre virus (HPS) is rare (typically 1-3 AZ cases / year)
    and clusters on the Colorado Plateau -- Coconino, Apache, Navajo
    counties overlapping the Navajo Nation, where the 1993 Four
    Corners outbreak characterized the virus. See ``wildlife/
    resources.md``: "northern AZ wildlife / vector contexts overlap
    with Coconino County's hantavirus, plague, and RMSF
    surveillance."
    """
    return [
        {"week_of": "2024-04-22", "county": "Coconino",
         "confirmed": 1, "probable": 0, "source_report_url": _ARBO_SOURCE_URL},
        {"week_of": "2024-06-03", "county": "Apache",
         "confirmed": 1, "probable": 0, "source_report_url": _ARBO_SOURCE_URL},
        {"week_of": "2024-09-16", "county": "Coconino",
         "confirmed": 0, "probable": 1, "source_report_url": _ARBO_SOURCE_URL},
    ]


def _single_row(county: str, week_of: str,
                confirmed: int, probable: int) -> dict[str, Any]:
    return {
        "week_of": week_of, "county": county,
        "confirmed": confirmed, "probable": probable,
        "source_report_url": _ARBO_SOURCE_URL,
    }


# Per-pathogen weekly case rows. Stubs use a single representative row
# so the tool has something to return; populate with real series as
# numbers become available.
RECENT_CASES: dict[str, list[dict[str, Any]]] = {
    "WNV": _wnv_maricopa_2024(),
    "HANTAVIRUS": _hantavirus_2024(),
    "SLEV": [
        _single_row("Maricopa",  "2024-07-22", 1, 0),
        _single_row("Maricopa",  "2024-08-12", 1, 1),
    ],
    "DENV": [
        # Almost all AZ dengue is travel-acquired; Maricopa + Pima
        # tend to log a handful per year.
        _single_row("Maricopa",  "2024-07-15", 2, 0),
        _single_row("Pima",      "2024-08-19", 1, 0),
    ],
    "ZIKV": [
        # ZIKV has been near-zero in AZ since the 2016-2017 outbreak.
        _single_row("Maricopa",  "2024-07-29", 0, 1),
    ],
    "PLAGUE": [
        # Endemic in the Four Corners; sporadic human cases.
        _single_row("Coconino",  "2024-08-05", 1, 0),
    ],
    "RABIES": [
        # Animal rabies is far more common than human; canned row is
        # a positive animal case the state lab confirmed.
        _single_row("Cochise",   "2024-05-13", 1, 0),
        _single_row("Yavapai",   "2024-07-08", 1, 0),
    ],
    "RMSF": [
        # AZ tribal-community RMSF cluster is the dominant driver.
        _single_row("Pinal",     "2024-06-10", 2, 1),
        _single_row("Navajo",    "2024-07-15", 1, 0),
    ],
    "TULAREMIA": [
        # 0-2 human cases / year statewide; stub a single confirmed.
        _single_row("Coconino",  "2024-08-26", 1, 0),
    ],
}


# ---------------------------------------------------------------------------
# Annual heat-mortality summary -- `adhs_heat_mortality_summary`.
#
# Statewide rows for 2013-2024 sourced from the ADHS heat-mortality
# report series + ``heat/04-vulnerable-populations.md`` (>4,320 deaths
# cumulative 2013-2024; 990 in 2023; 602 in 2024). Per-county breakdown
# is illustrative: Maricopa carries the overwhelming share (typically
# ~85-90% of AZ heat deaths) given its population + urban-heat-island
# load and the MCDPH surveillance system running since 2006. Pre-2023
# annual totals interpolate between the 2014-2018 baseline and the
# 2020-onward escalation documented in MCDPH + ADHS reports.
#
# Cumulative 2013-2024 statewide_deaths total: 4321 (just above the
# 4,320 headline figure in the markdown).
# ---------------------------------------------------------------------------
def _year(year: int, statewide: int, maricopa: int, pima: int,
          yuma: int, other: int, er_visits: int) -> dict[str, Any]:
    return {
        "year": year,
        "statewide_deaths": statewide,
        "maricopa_deaths": maricopa,
        "pima_deaths": pima,
        "yuma_deaths": yuma,
        "other_counties_deaths": other,
        "estimated_er_visits": er_visits,
        "source_report_url": ADHS_HEAT_MORTALITY_PORTAL_URL,
    }


HEAT_MORTALITY_SUMMARY: list[dict[str, Any]] = [
    # year   statewide  maricopa  pima  yuma  other  er_visits
    _year(2013,   148,    127,    11,    4,    6,    4100),
    _year(2014,   161,    138,    13,    4,    6,    4150),
    _year(2015,   180,    154,    15,    4,    7,    4200),
    _year(2016,   235,    202,    19,    5,    9,    4250),
    _year(2017,   260,    223,    21,    6,   10,    4300),
    _year(2018,   283,    241,    24,    7,   11,    4300),
    _year(2019,   285,    245,    23,    6,   11,    4280),
    _year(2020,   313,    264,    27,    8,   14,    4350),
    _year(2021,   552,    494,    34,   10,   14,    4400),
    _year(2022,   421,    359,    36,   11,   15,    4350),
    _year(2023,   990,    893,    52,   14,   31,    4500),
    _year(2024,   602,    537,    36,   10,   19,    4298),
]


# ---------------------------------------------------------------------------
# Weekly arbovirus surveillance summary -- `adhs_arbovirus_surveillance_summary`.
#
# The ADHS weekly summary historically aggregates county submissions
# into a single statewide picture: positive mosquito pools, sentinel-
# chicken seroconversion (where running), and human + equine cases.
# The 800+ trap network footprint reference is from MCESD; see
# ``wildlife/resources.md``: "Over 800 vector traps county-wide,
# mosquito pools tested for WNV and SLE, with a published weekly
# Vector Index... Data is updated weekly on Fridays."
# ---------------------------------------------------------------------------
def _arbo_row(week_of: str, county: str, pathogen: str,
              positive_pools: int, pools_tested: int,
              sentinel_seroconversions: int | None,
              human_cases: int, equine_cases: int,
              trap_network_size: int | None,
              note: str) -> dict[str, Any]:
    return {
        "week_of": week_of,
        "surv_year": int(week_of[:4]),
        "county": county,
        "pathogen": pathogen,
        "positive_pools": positive_pools,
        "pools_tested": pools_tested,
        "sentinel_chicken_seroconversions": sentinel_seroconversions,
        "human_cases": human_cases,
        "equine_cases": equine_cases,
        "trap_network_size": trap_network_size,
        "note": note,
        "source_report_url": _ARBO_SOURCE_URL,
    }


ARBOVIRUS_SURVEILLANCE: list[dict[str, Any]] = [
    # Maricopa, WNV -- 12-week 2024 summer series. trap_network_size of
    # 800 reflects the MCESD footprint cited above.
    _arbo_row("2024-06-17", "Maricopa", "WNV",   2,  420, 0,  1, 0, 800,
              "Early-season pool positivity; first human onset of the year."),
    _arbo_row("2024-06-24", "Maricopa", "WNV",   5,  445, 1,  3, 0, 800,
              "First sentinel-chicken seroconversion (south Phoenix flock)."),
    _arbo_row("2024-07-01", "Maricopa", "WNV",  11,  470, 2,  4, 1, 800,
              "Pool positivity climbing; first equine case in west valley."),
    _arbo_row("2024-07-08", "Maricopa", "WNV",  19,  480, 3,  8, 1, 800,
              "Vector Index above seasonal advisory threshold."),
    _arbo_row("2024-07-15", "Maricopa", "WNV",  28,  495, 4, 12, 2, 800,
              "Peak pool positivity for the season starting in Mesa-Tempe corridor."),
    _arbo_row("2024-07-22", "Maricopa", "WNV",  33,  502, 5, 17, 2, 800,
              "Peak human-case week; public health advisory issued."),
    _arbo_row("2024-07-29", "Maricopa", "WNV",  31,  498, 5, 21, 3, 800,
              "Sustained transmission; expanded fogging in 3 ZIP codes."),
    _arbo_row("2024-08-05", "Maricopa", "WNV",  24,  485, 4, 19, 3, 800,
              "Positivity declining but human cases still rising (lag)."),
    _arbo_row("2024-08-12", "Maricopa", "WNV",  17,  470, 3, 16, 2, 800,
              "Monsoon storms producing new breeding sites; vigilance week."),
    _arbo_row("2024-08-19", "Maricopa", "WNV",  10,  450, 2, 12, 1, 800,
              "Cooling trend; weekly positivity below alert threshold."),
    _arbo_row("2024-08-26", "Maricopa", "WNV",   5,  430, 1,  7, 1, 800,
              "Season tail; reduced fogging cadence."),
    _arbo_row("2024-09-02", "Maricopa", "WNV",   2,  410, 0,  3, 0, 800,
              "End-of-season summary; epicurve closing out."),
    # Pima, WNV -- representative mid-summer rows. Pima Vector Control
    # trap window is May-November (see wildlife/resources.md).
    _arbo_row("2024-07-15", "Pima",     "WNV",   3,  140, 0,  1, 0, 120,
              "First positive Culex tarsalis pools of the Pima season."),
    _arbo_row("2024-08-12", "Pima",     "WNV",   5,  145, 1,  2, 0, 120,
              "Sentinel-chicken seroconversion (Tucson flock)."),
    # Maricopa, SLEV -- co-circulates with WNV in late summer.
    _arbo_row("2024-08-05", "Maricopa", "SLEV",  2,  485, 0,  1, 0, 800,
              "Two SLE-positive pools alongside WNV positives in same traps."),
    _arbo_row("2024-08-19", "Maricopa", "SLEV",  1,  450, 0,  1, 1, 800,
              "Equine SLE case in the west valley."),
]


# ---------------------------------------------------------------------------
# ADHS Vector-Borne & Zoonotic Diseases program -- structured description.
# ---------------------------------------------------------------------------
VBZD_PROGRAM: dict[str, Any] = {
    "name": "ADHS Vector-Borne & Zoonotic Diseases Program",
    "url": ADHS_VBZD_PROGRAM_URL,
    "description": (
        "Branch of the Arizona Department of Health Services' Bureau of "
        "Epidemiology & Disease Control that monitors, investigates, and "
        "responds to diseases transmitted by mosquitoes, ticks, fleas, "
        "and wild or domestic animals across Arizona. Coordinates with "
        "county vector-control programs (Maricopa MCESD, Pima Vector "
        "Control, Coconino, Yavapai, Yuma, etc.), tribal epidemiology "
        "centers, USDA APHIS Wildlife Services, the Arizona State Public "
        "Health Laboratory, and CDC for confirmatory testing and outbreak "
        "response."
    ),
    "pathogens_monitored": [
        "WNV", "SLEV", "WEEV", "DENV", "ZIKV", "CHIKV",
        "HANTAVIRUS", "PLAGUE", "RABIES", "RMSF", "TULAREMIA",
    ],
    "primary_labs": [
        {
            "name": "Arizona State Public Health Laboratory (ASPHL)",
            "role": (
                "Confirmatory testing for arboviruses, hantavirus, plague, "
                "tularemia, and rabies; PCR + serology + viral isolation."
            ),
        },
        {
            "name": "CDC Division of Vector-Borne Diseases (Fort Collins)",
            "role": (
                "Reference confirmation for arboviral neuroinvasive disease "
                "and unusual serotypes; PRNT confirmation of WNV / SLEV / "
                "Powassan."
            ),
        },
        {
            "name": "CDC Bacterial Special Pathogens Branch",
            "role": (
                "Reference confirmation for plague (Yersinia pestis) and "
                "tularemia (Francisella tularensis)."
            ),
        },
        {
            "name": "Maricopa County Environmental Services Department (MCESD)",
            "role": (
                "Operates the 800+ trap county-wide mosquito-surveillance "
                "network; submits weekly pool PCR results to ADHS."
            ),
        },
    ],
    "reporting_cadence": {
        "arbovirus_summary": "weekly during mosquito season (May-November)",
        "hantavirus_plague_tularemia": "case-by-case (immediately reportable)",
        "rabies": "case-by-case (immediately reportable for animal exposures)",
        "rmsf": "weekly aggregated; case-by-case for tribal-community clusters",
        "annual_summary": "annual report compiled in Q1 of following year",
    },
    "see_also": {
        "vectorsurv": "https://api.vectorsurv.org/",
        "mcesd_dashboard": "https://www.maricopa.gov/2476/Mosquito-Borne-Disease-Statistics",
        "fight_the_bite": "https://fightthebitemaricopa.org/",
    },
}


# ---------------------------------------------------------------------------
# ADHS Heat Preparedness Network -- structured description.
# ---------------------------------------------------------------------------
HEAT_PREPAREDNESS_NETWORK: dict[str, Any] = {
    "name": "ADHS Heat Preparedness Network",
    "arcgis_experience_url": ADHS_HEAT_PREPAREDNESS_MAP_URL,
    "program_url": ADHS_HEAT_PROGRAM_URL,
    "description": (
        "ArcGIS Experience map of Heat Preparedness Network locations "
        "across Arizona: cooling centers, hydration stations, respite "
        "sites, and overnight heat shelters. Aggregated from county and "
        "tribal partners; complements the regional Maricopa Association "
        "of Governments (MAG) Heat Relief Network for the Phoenix metro."
    ),
    "season_window": {
        "start": "May 1",
        "end": "September 30",
        "note": (
            "Aligned with the Governor's Extreme Heat Preparedness Plan "
            "(launched May 1 each year) and the MAG HRN's May-September "
            "operating window. Some sites operate year-round; the season "
            "label flags the period of statewide coordinated activation."
        ),
    },
    "detailed_records_note": (
        "Detailed cooling-center records (hours, services, pet-friendly, "
        "real-time capacity) come from `mag-hrn-mcp`, which wraps the "
        "regional Maricopa Association of Governments Heat Relief Network "
        "registry at hrn.azmag.gov."
    ),
    "see_also": {
        "mag_hrn_mcp": "../mag-hrn-mcp/",
        "mag_hrn_map": "https://hrn.azmag.gov/",
        "adhs_heat_program": ADHS_HEAT_PROGRAM_URL,
        "heat_mortality_portal": ADHS_HEAT_MORTALITY_PORTAL_URL,
    },
}


# ---------------------------------------------------------------------------
# Reportable conditions -- `adhs_reportable_conditions`.
#
# Sourced from ``schema/deep/standards.sql``: every ADHS-reportable
# condition relevant to wildlife / vector / heat surveillance gets a
# row carrying either an ICD-10 code, a SNOMED CT concept, or both,
# plus the corresponding CDC NNDSS condition where one exists.
# ---------------------------------------------------------------------------
REPORTABLE_CONDITIONS: list[dict[str, Any]] = [
    {
        "condition": "Heatstroke and sunstroke",
        "category": "environmental",
        "icd10": "T67.0XXA",
        "icd10_description": "Heatstroke and sunstroke, initial encounter",
        "snomed_ct": "39579001",
        "snomed_description": "Heatstroke (disorder)",
        "nndss_condition": None,
        "az_reporting_rule": (
            "Heat-caused / heat-related deaths captured in the ADHS "
            "annual heat-mortality surveillance report; ED visits "
            "flow through CDC NSSP BioSense."
        ),
    },
    {
        "condition": "Plague (bubonic, pneumonic, septicemic)",
        "category": "bacterial-zoonotic",
        "icd10": "A20.9",
        "icd10_description": "Plague, unspecified (A20.0-A20.9 series)",
        "snomed_ct": "58750007",
        "snomed_description": "Plague (disorder)",
        "nndss_condition": "Plague",
        "az_reporting_rule": "Immediately reportable; AAC R9-6-202 Category 1.",
    },
    {
        "condition": "Rocky Mountain spotted fever (RMSF)",
        "category": "tick-borne-rickettsial",
        "icd10": "A77.0",
        "icd10_description": "Spotted fever due to Rickettsia rickettsii",
        "snomed_ct": "186772009",
        "snomed_description": "Rocky Mountain spotted fever (disorder)",
        "nndss_condition": "Spotted Fever Rickettsiosis (incl. RMSF)",
        "az_reporting_rule": (
            "Reportable within 1 work day; tribal-community cluster on "
            "active enhanced surveillance with CDC."
        ),
    },
    {
        "condition": "Hantavirus pulmonary syndrome (HPS)",
        "category": "viral-zoonotic",
        "icd10": "B33.4",
        "icd10_description": "Hantavirus (cardio-)pulmonary syndrome",
        "snomed_ct": "47523006",
        "snomed_description": "Hantavirus pulmonary syndrome (disorder)",
        "nndss_condition": (
            "Hantavirus Infection, non-Hantavirus Pulmonary Syndrome and HPS"
        ),
        "az_reporting_rule": (
            "Immediately reportable; Sin Nombre virus endemic on the "
            "Colorado Plateau (Coconino, Apache, Navajo counties)."
        ),
    },
    {
        "condition": "Tularemia",
        "category": "bacterial-zoonotic",
        "icd10": "A21.9",
        "icd10_description": "Tularemia, unspecified (A21.0-A21.9 series)",
        "snomed_ct": "19265001",
        "snomed_description": "Tularemia (disorder)",
        "nndss_condition": "Tularemia",
        "az_reporting_rule": "Reportable within 1 work day.",
    },
    {
        "condition": "West Nile virus disease",
        "category": "arboviral",
        "icd10": "A92.30",
        "icd10_description": "West Nile virus infection, unspecified",
        "snomed_ct": "230145002",
        "snomed_description": "West Nile virus infection (disorder)",
        "nndss_condition": (
            "West Nile Virus Disease (Arboviral Diseases, neuroinvasive "
            "and non-neuroinvasive)"
        ),
        "az_reporting_rule": (
            "Reportable within 1 work day; reported weekly during the "
            "arbovirus season summary."
        ),
    },
    {
        "condition": "Rabies, human",
        "category": "viral-zoonotic",
        "icd10": "A82.9",
        "icd10_description": "Rabies, unspecified (A82.0-A82.9 series)",
        "snomed_ct": "14168008",
        "snomed_description": "Rabies (disorder)",
        "nndss_condition": "Rabies, Human",
        "az_reporting_rule": "Immediately reportable.",
    },
    {
        "condition": "Rabies, animal",
        "category": "veterinary-zoonotic",
        "icd10": "A82.0",
        "icd10_description": "Sylvatic rabies",
        "snomed_ct": "14168008",
        "snomed_description": "Rabies (disorder)",
        "nndss_condition": "Rabies, Animal",
        "az_reporting_rule": (
            "Immediately reportable; ASPHL performs DFA confirmation."
        ),
    },
    {
        "condition": "Dengue virus disease",
        "category": "arboviral",
        "icd10": None,
        "icd10_description": None,
        "snomed_ct": "38362002",
        "snomed_description": "Dengue (disorder)",
        "nndss_condition": "Dengue Virus Infections",
        "az_reporting_rule": (
            "Reportable within 1 work day; nearly all AZ cases are "
            "travel-acquired."
        ),
    },
    {
        "condition": "Zika virus disease",
        "category": "arboviral",
        "icd10": None,
        "icd10_description": None,
        "snomed_ct": "3928002",
        "snomed_description": "Zika virus disease (disorder)",
        "nndss_condition": "Zika Virus Disease, Non-congenital",
        "az_reporting_rule": "Reportable within 1 work day.",
    },
    {
        "condition": "St. Louis encephalitis virus disease",
        "category": "arboviral",
        "icd10": None,
        "icd10_description": None,
        "snomed_ct": "16541001",
        "snomed_description": "St. Louis encephalitis (disorder)",
        "nndss_condition": (
            "Arboviral Diseases, Neuroinvasive and Non-neuroinvasive "
            "(SLEV)"
        ),
        "az_reporting_rule": "Reportable within 1 work day.",
    },
]


# ---------------------------------------------------------------------------
# Heat-mortality summary text -- exposed as the
# `adhs://heat-mortality-summary-text` MCP resource. Verbatim-style
# paraphrase of the headline numbers in
# ``heat/04-vulnerable-populations.md`` so an LLM can pull it as
# context without calling a tool.
# ---------------------------------------------------------------------------
HEAT_MORTALITY_SUMMARY_TEXT: str = (
    "Arizona heat-mortality summary (sources: ADHS heat-related mortality "
    "report series 2013-2024, MCDPH Heat Surveillance, "
    "heat/04-vulnerable-populations.md):\n"
    "\n"
    "  - More than 4,320 people have died from heat exposure in Arizona "
    "between 2013 and 2024.\n"
    "  - About 4,298 emergency-room visits per year for heat-related "
    "illness statewide.\n"
    "  - 990 heat-related deaths in 2023 -- the highest annual total in "
    "the report series.\n"
    "  - 602 heat-related deaths in 2024 (preliminary).\n"
    "  - Maricopa County has run a dedicated heat-mortality surveillance "
    "system since 2006 and carries the overwhelming majority of the "
    "statewide burden.\n"
    "\n"
    "Highest-burden groups (per the MCDPH + ADHS reports): people "
    "experiencing unsheltered homelessness (~36% share of Maricopa heat "
    "deaths in 2016, elevated since); older adults (65+), especially "
    "with AC failure or unaffordability; American Indian / Alaska "
    "Native and African American Maricopa residents (highest rates per "
    "100,000); males (~81% of Maricopa heat-associated deaths); outdoor "
    "workers; people with substance-use disorders or serious mental "
    "illness; infants and young children (vehicular heatstroke); people "
    "dependent on electric medical equipment; renters in older housing "
    "without working AC; tribal community members, especially rural; "
    "and migrants / asylum-seekers in border regions.\n"
    "\n"
    f"Annual reports: {ADHS_HEAT_MORTALITY_PORTAL_URL}\n"
    f"2012-2023 PDF: {ADHS_HEAT_MORTALITY_2023_PDF_URL}\n"
)


# ---------------------------------------------------------------------------
# Acronym block exposed at `adhs://pathogen-acronyms`. Mirrors the
# `vectorsurv://disease-acronyms` resource but pinned to the ADHS
# pathogen list (includes the zoonotic + tick-borne reportable
# conditions VectorSurv doesn't itself cover).
# ---------------------------------------------------------------------------
def render_pathogen_acronyms_text() -> str:
    lines: list[str] = []
    width = max(len(p["acronym"]) for p in PATHOGEN_ACRONYMS) + 2
    for p in PATHOGEN_ACRONYMS:
        lines.append(
            f"{p['acronym']:<{width}} = {p['name']}  [{p['category']}]"
        )
    lines.append("")
    lines.append("(ADHS reportable-conditions terminology; for the full "
                 "code list call `adhs_reportable_conditions`.)")
    return "\n".join(lines)
