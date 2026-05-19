"""Canned reference data for the 211 Arizona mock backend.

Everything here is approximate and intended for offline / demo use.
For the live numbers, hours, and service areas see
<https://211arizona.org/crisis/heat-relief/> and the operator
directories on the linked county / agency sites. The structure of
these dicts mirrors what we expect a future real API to return, so
swapping to a live backend should not require call-site changes.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Postal-code -> county hint. Just the prefix ranges we need for routing
# the canned utility-assistance + cooling-center lookups; the mock
# falls back to "Maricopa" for unrecognised codes so demos always
# return *something*.
# ---------------------------------------------------------------------------
ZIP_COUNTY_HINTS: dict[str, str] = {
    # Maricopa (metro Phoenix)
    "850": "Maricopa",
    "851": "Maricopa",
    "852": "Maricopa",
    "853": "Maricopa",
    # Pima (Tucson)
    "856": "Pima",
    "857": "Pima",
    # Yuma
    "853_y": "Yuma",  # 85364, 85365, 85367; matched via explicit check below
    # Coconino (Flagstaff)
    "860": "Coconino",
    "863": "Coconino",
    # Navajo / Apache
    "865": "Navajo",
    "864": "Navajo",
}


def county_for_zip(postal_code: str | None) -> str:
    """Best-effort ZIP -> county mapping for the mock data set.

    Only the prefixes we actually use in the canned providers matter;
    everything else falls back to Maricopa so the demo never empties.
    """
    if not postal_code:
        return "Maricopa"
    pc = str(postal_code).strip()
    # Yuma overrides Maricopa for 853xx range
    if pc.startswith("8536") or pc.startswith("8535"):
        return "Yuma"
    prefix = pc[:3]
    return ZIP_COUNTY_HINTS.get(prefix, "Maricopa")


# ---------------------------------------------------------------------------
# Utility-assistance / community-action-agency providers. 7 entries
# spread across Maricopa, Pima, Coconino, Yuma, and Navajo counties.
# Each provider lists which `kind` filters it should match.
# ---------------------------------------------------------------------------
UTILITY_PROVIDERS: list[dict[str, Any]] = [
    {
        "id": "wildfire-maricopa",
        "name": "Wildfire (formerly Arizona Community Action Association)",
        "county": "Maricopa",
        "phone": "602-604-0640",
        "url": "https://wildfireaz.org/",
        "services": ["electric", "gas", "water", "weatherization", "emergency_ac_repair"],
        "notes": (
            "Statewide community-action network; administers LIHEAP and "
            "emergency AC-repair across Maricopa County partner agencies."
        ),
    },
    {
        "id": "ccs-maricopa",
        "name": "Catholic Charities Community Services — Phoenix",
        "county": "Maricopa",
        "phone": "602-749-4405",
        "url": "https://www.catholiccharitiesaz.org/",
        "services": ["electric", "gas", "water"],
        "notes": "Emergency utility-bill assistance; appointment-based.",
    },
    {
        "id": "sva-maricopa",
        "name": "St. Vincent de Paul — Phoenix",
        "county": "Maricopa",
        "phone": "602-266-4357",
        "url": "https://www.stvincentdepaul.net/",
        "services": ["electric", "gas", "emergency_ac_repair"],
        "notes": "Emergency AC repair / replacement program during heat season.",
    },
    {
        "id": "cap-pima",
        "name": "Pima County Community Action Agency",
        "county": "Pima",
        "phone": "520-724-2667",
        "url": "https://webcms.pima.gov/government/community_workforce_development/community_action_agency/",
        "services": ["electric", "gas", "water", "weatherization"],
        "notes": "LIHEAP intake for Pima County; weatherization referrals.",
    },
    {
        "id": "ccs-yuma",
        "name": "Catholic Community Services — Yuma",
        "county": "Yuma",
        "phone": "928-217-2433",
        "url": "https://ccs-soaz.org/",
        "services": ["electric", "gas", "weatherization"],
        "notes": "LIHEAP and weatherization in Yuma County.",
    },
    {
        "id": "ccs-coconino",
        "name": "Coconino County Community Services — Flagstaff",
        "county": "Coconino",
        "phone": "928-679-7457",
        "url": "https://www.coconino.az.gov/2492/Community-Services",
        "services": ["electric", "gas", "weatherization"],
        "notes": "Northern Arizona LIHEAP and weatherization.",
    },
    {
        "id": "navapache",
        "name": "NACOG / Navapache Community Action",
        "county": "Navajo",
        "phone": "928-532-6105",
        "url": "https://www.nacog.org/",
        "services": ["electric", "gas", "weatherization"],
        "notes": (
            "Northern Arizona Council of Governments community-action; "
            "serves Navajo, Apache, and Yavapai counties."
        ),
    },
]


# ---------------------------------------------------------------------------
# Cooling-center canned entries used by az211_cooling_center_referral_nearby.
# In production this tool will cross-call mag-hrn-mcp instead.
# Centers are tagged with a coarse lat/lon and the county they sit in.
# ---------------------------------------------------------------------------
COOLING_CENTERS: list[dict[str, Any]] = [
    {
        "id": "center.phx_central_library",
        "name": "Burton Barr Central Library (cooling center)",
        "address": "1221 N Central Ave, Phoenix, AZ 85004",
        "county": "Maricopa",
        "lat": 33.4737,
        "lon": -112.0735,
        "hours": "09:00-20:00",
        "pets_ok": False,
        "wheelchair_accessible": True,
        "phone": "602-262-4636",
    },
    {
        "id": "center.phx_human_services",
        "name": "Human Services Campus respite center",
        "address": "204 S 12th Ave, Phoenix, AZ 85007",
        "county": "Maricopa",
        "lat": 33.4458,
        "lon": -112.0938,
        "hours": "24h during heat season",
        "pets_ok": True,
        "wheelchair_accessible": True,
        "phone": "602-256-6945",
    },
    {
        "id": "center.tucson_el_pueblo",
        "name": "El Pueblo Senior Center cooling station",
        "address": "101 W Irvington Rd, Tucson, AZ 85714",
        "county": "Pima",
        "lat": 32.1497,
        "lon": -110.9747,
        "hours": "08:00-17:00",
        "pets_ok": False,
        "wheelchair_accessible": True,
        "phone": "520-791-4865",
    },
    {
        "id": "center.flagstaff_library",
        "name": "Flagstaff Downtown Library cooling station",
        "address": "300 W Aspen Ave, Flagstaff, AZ 86001",
        "county": "Coconino",
        "lat": 35.1986,
        "lon": -111.6519,
        "hours": "09:00-19:00",
        "pets_ok": False,
        "wheelchair_accessible": True,
        "phone": "928-213-2330",
    },
]


# ---------------------------------------------------------------------------
# Crisis-referral entries by topic.
# ---------------------------------------------------------------------------
CRISIS_REFERRALS: dict[str, list[dict[str, Any]]] = {
    "heat": [
        {
            "id": "211-heatrelief",
            "name": "211 Arizona Heat Relief line",
            "phone": "2-1-1",
            "alt_phone": "1-877-211-8661",
            "hours": "year-round; expanded hours during heat season (May 1 - Sept 30)",
            "languages": ["English", "Spanish"],
            "url": "https://211arizona.org/crisis/heat-relief/",
        },
        {
            "id": "mag-hrn",
            "name": "MAG Heat Relief Network map",
            "phone": None,
            "hours": "online directory",
            "languages": ["English", "Spanish"],
            "url": "https://hrn.azmag.gov/",
        },
    ],
    "housing": [
        {
            "id": "211-housing",
            "name": "211 Arizona housing & shelter line",
            "phone": "2-1-1",
            "hours": "24/7",
            "languages": ["English", "Spanish"],
            "url": "https://211arizona.org/",
        },
        {
            "id": "hsc-phx",
            "name": "Human Services Campus (Phoenix)",
            "phone": "602-256-6945",
            "hours": "24/7",
            "languages": ["English", "Spanish"],
            "url": "https://hsc-az.org/",
        },
    ],
    "food": [
        {
            "id": "stmarys-foodbank",
            "name": "St. Mary's Food Bank Alliance",
            "phone": "602-242-3663",
            "hours": "M-F 08:00-17:00",
            "languages": ["English", "Spanish"],
            "url": "https://www.firstfoodbank.org/",
        },
        {
            "id": "cfb-pima",
            "name": "Community Food Bank of Southern Arizona",
            "phone": "520-622-0525",
            "hours": "M-F 08:00-17:00",
            "languages": ["English", "Spanish"],
            "url": "https://www.communityfoodbank.org/",
        },
    ],
    "behavioral_health": [
        {
            "id": "988",
            "name": "988 Suicide & Crisis Lifeline",
            "phone": "988",
            "hours": "24/7",
            "languages": ["English", "Spanish", "ASL via video relay"],
            "url": "https://988lifeline.org/",
        },
        {
            "id": "solari-crisis",
            "name": "Solari Crisis Response Network (statewide AZ)",
            "phone": "1-844-534-4673",
            "hours": "24/7",
            "languages": ["English", "Spanish"],
            "url": "https://solariinc.org/",
        },
    ],
}


# ---------------------------------------------------------------------------
# Operator hours, returned by the az211://hours MCP resource.
# ---------------------------------------------------------------------------
OPERATOR_HOURS: dict[str, Any] = {
    "main_line": {
        "dial": "2-1-1",
        "alt": "1-877-211-8661",
        "year_round_hours": "06:00 - 22:00 MST (Mon - Sun)",
        "heat_season_hours": "24/7 from May 1 to September 30 (expanded for heat relief)",
        "notes": (
            "211 Arizona is operated by Solari Crisis & Human Services. "
            "Live operators in English and Spanish."
        ),
    },
    "crisis_lifeline_988": {
        "dial": "988",
        "hours": "24/7",
    },
    "solari_crisis_response": {
        "dial": "1-844-534-4673",
        "hours": "24/7 statewide; the operating partner behind 211 Arizona",
    },
    "veterans_crisis_line": {
        "dial": "988 then press 1",
        "alt_text": "Text 838255",
        "hours": "24/7",
    },
    "asl_video_relay": {
        "method": "ASL via SVRS / video relay to 988 or 211",
        "hours": "24/7",
    },
}


# ---------------------------------------------------------------------------
# Languages supported, returned by the az211://languages MCP resource.
# Indigenous-language access is real but provided through partner
# organisations (ITCA-TEC, IHS, tribal community-health programs) and
# the Language Line Solutions interpreter service contracted by Solari;
# the listing below names the partner pathways.
# ---------------------------------------------------------------------------
LANGUAGES_SUPPORTED: dict[str, Any] = {
    "direct_operator_languages": ["English", "Spanish"],
    "interpreter_service": {
        "provider": "Language Line Solutions (or equivalent contract)",
        "languages": "200+ languages on-demand",
        "notes": "Connect-time may be longer than direct-language calls.",
    },
    "indigenous_language_pathways": [
        {
            "language": "Diné bizaad (Navajo)",
            "pathway": (
                "Navajo Epidemiology Center, Navajo Nation Community Health "
                "Representatives, and IHS Navajo Area facilities provide "
                "Diné-language intake. 211 Arizona warm-transfers when "
                "appropriate."
            ),
            "url": "https://nec.navajo-nsn.gov/",
        },
        {
            "language": "O'odham (Tohono O'odham, Akimel O'odham)",
            "pathway": (
                "Tohono O'odham Nation Department of Health & Human "
                "Services and the Inter Tribal Council of Arizona "
                "Tribal Epidemiology Center (ITCA-TEC) coordinate "
                "O'odham-language outreach."
            ),
            "url": "https://itcaonline.com/",
        },
        {
            "language": "Apache (Western Apache, Yavapai-Apache)",
            "pathway": (
                "San Carlos Apache and White Mountain Apache tribal "
                "health programs provide Apache-language support; "
                "ITCA-TEC coordinates referrals."
            ),
            "url": "https://itcaonline.com/",
        },
        {
            "language": "Hopilavayi (Hopi)",
            "pathway": (
                "Hopi Tribe Department of Health and Human Services; "
                "warm-transfer from 211 Arizona where available."
            ),
            "url": "https://www.hopi-nsn.gov/",
        },
    ],
}


__all__ = [
    "COOLING_CENTERS",
    "CRISIS_REFERRALS",
    "LANGUAGES_SUPPORTED",
    "OPERATOR_HOURS",
    "UTILITY_PROVIDERS",
    "ZIP_COUNTY_HINTS",
    "county_for_zip",
]
