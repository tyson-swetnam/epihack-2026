"""Canned offline dataset for the iNaturalist MCP server.

The iNaturalist public API at https://api.inaturalist.org/v1/ is open
and unauthenticated for read-only endpoints, but the build sandbox
needs to run tests with no network. This module ships a synthetic
canned dataset of ~20 Arizona observations covering the taxa most
relevant to AZ One Health surveillance (ticks, mosquitoes, fleas,
deer mice, prairie dogs, rock squirrels, cottontails) so the rest of
the stack can develop offline.

The canned dataset is also what the client falls back to when
``INAT_OFFLINE=1`` is set or when an HTTP request to the live API
fails with a connection error -- "mock-by-default" per the project
plan.

Taxon IDs below are the canonical iNaturalist IDs as documented on
the public taxa pages (verify by visiting
``https://www.inaturalist.org/taxa/{id}``). Every ID is overridable
via ``INAT_TAXON_<KEY>`` env vars at client-construction time so a
contributor can patch a drifted ID without a code change.

Place ID 53 corresponds to the US state of Arizona on iNaturalist
(``https://api.inaturalist.org/v1/places/53`` returns
``{name: "Arizona", admin_level: 10}``). The variable
``AZ_PLACE_ID`` is the project-wide default; override via
``INAT_AZ_PLACE_ID``.
"""

from __future__ import annotations

import os
from typing import Any

# ---------------------------------------------------------------------------
# Place + taxon IDs. All env-overridable so contributors can patch any
# drift without a code change.
# ---------------------------------------------------------------------------
AZ_PLACE_ID: int = int(os.environ.get("INAT_AZ_PLACE_ID", "53"))

# Higher taxa (order / family level).
TAXON_TICKS: int = int(os.environ.get("INAT_TAXON_TICKS", "47119"))       # Order Ixodida
TAXON_MOSQUITOES: int = int(os.environ.get("INAT_TAXON_MOSQUITOES", "84738"))  # Family Culicidae
TAXON_FLEAS: int = int(os.environ.get("INAT_TAXON_FLEAS", "84377"))       # Order Siphonaptera
TAXON_RODENTS: int = int(os.environ.get("INAT_TAXON_RODENTS", "43698"))   # Order Rodentia

# AZ-relevant tick species.
TAXON_RHIPICEPHALUS_SANGUINEUS: int = int(
    os.environ.get("INAT_TAXON_RHIPICEPHALUS_SANGUINEUS", "84219")
)  # Brown dog tick
TAXON_DERMACENTOR_ANDERSONI: int = int(
    os.environ.get("INAT_TAXON_DERMACENTOR_ANDERSONI", "126099")
)  # Rocky Mountain wood tick
TAXON_DERMACENTOR_VARIABILIS: int = int(
    os.environ.get("INAT_TAXON_DERMACENTOR_VARIABILIS", "84223")
)  # American dog tick
TAXON_IXODES_PACIFICUS: int = int(
    os.environ.get("INAT_TAXON_IXODES_PACIFICUS", "62366")
)  # Western black-legged tick

# AZ-relevant wildlife disease reservoirs.
TAXON_PEROMYSCUS_MANICULATUS: int = int(
    os.environ.get("INAT_TAXON_PEROMYSCUS_MANICULATUS", "46559")
)  # Deer mouse (hantavirus reservoir)
TAXON_CYNOMYS_GUNNISONI: int = int(
    os.environ.get("INAT_TAXON_CYNOMYS_GUNNISONI", "46211")
)  # Gunnison's prairie dog (plague)
TAXON_OTOSPERMOPHILUS_VARIEGATUS: int = int(
    os.environ.get("INAT_TAXON_OTOSPERMOPHILUS_VARIEGATUS", "73704")
)  # Rock squirrel (plague)
TAXON_SYLVILAGUS_AUDUBONII: int = int(
    os.environ.get("INAT_TAXON_SYLVILAGUS_AUDUBONII", "43130")
)  # Desert cottontail (tularemia)


# ---------------------------------------------------------------------------
# Tick-genus reference (used by the ``inat://tick-genera-az`` resource
# and ``inat_taxon_lookup``).
# ---------------------------------------------------------------------------
AZ_TICK_GENERA: list[dict[str, Any]] = [
    {
        "taxon_id": TAXON_TICKS,
        "rank": "order",
        "scientific_name": "Ixodida",
        "common_name": "ticks",
        "notes": "All AZ ticks roll up under Ixodida.",
    },
    {
        "taxon_id": TAXON_RHIPICEPHALUS_SANGUINEUS,
        "rank": "species",
        "scientific_name": "Rhipicephalus sanguineus",
        "common_name": "brown dog tick",
        "notes": (
            "Dominant statewide species; principal RMSF vector in AZ, "
            "especially in tribal-community clusters."
        ),
    },
    {
        "taxon_id": TAXON_DERMACENTOR_ANDERSONI,
        "rank": "species",
        "scientific_name": "Dermacentor andersoni",
        "common_name": "Rocky Mountain wood tick",
        "notes": "Higher-elevation AZ; Colorado tick fever, RMSF, tularemia.",
    },
    {
        "taxon_id": TAXON_DERMACENTOR_VARIABILIS,
        "rank": "species",
        "scientific_name": "Dermacentor variabilis",
        "common_name": "American dog tick",
        "notes": "Co-occurs with brown dog tick; secondary RMSF + tularemia vector.",
    },
    {
        "taxon_id": TAXON_IXODES_PACIFICUS,
        "rank": "species",
        "scientific_name": "Ixodes pacificus",
        "common_name": "Western black-legged tick",
        "notes": "Lyme + anaplasmosis; documented in Mohave County.",
    },
]


# ---------------------------------------------------------------------------
# Taxon reference table -- the lookup target for `inat_taxon_lookup`
# when the live API isn't reachable.
# ---------------------------------------------------------------------------
TAXON_REFERENCE: list[dict[str, Any]] = [
    {
        "id": TAXON_TICKS,
        "name": "Ixodida",
        "preferred_common_name": "ticks",
        "rank": "order",
        "ancestor_ids": [1, 47120, 47119],
        "aliases": ["tick", "ticks", "ixodida"],
    },
    {
        "id": TAXON_MOSQUITOES,
        "name": "Culicidae",
        "preferred_common_name": "mosquitoes",
        "rank": "family",
        "ancestor_ids": [1, 47158, 84738],
        "aliases": ["mosquito", "mosquitoes", "culicidae"],
    },
    {
        "id": TAXON_FLEAS,
        "name": "Siphonaptera",
        "preferred_common_name": "fleas",
        "rank": "order",
        "ancestor_ids": [1, 47158, 84377],
        "aliases": ["flea", "fleas", "siphonaptera"],
    },
    {
        "id": TAXON_RODENTS,
        "name": "Rodentia",
        "preferred_common_name": "rodents",
        "rank": "order",
        "ancestor_ids": [1, 40151, 43698],
        "aliases": ["rodent", "rodents", "rodentia"],
    },
    {
        "id": TAXON_RHIPICEPHALUS_SANGUINEUS,
        "name": "Rhipicephalus sanguineus",
        "preferred_common_name": "brown dog tick",
        "rank": "species",
        "ancestor_ids": [TAXON_TICKS],
        "aliases": ["brown dog tick", "rhipicephalus sanguineus"],
    },
    {
        "id": TAXON_DERMACENTOR_ANDERSONI,
        "name": "Dermacentor andersoni",
        "preferred_common_name": "Rocky Mountain wood tick",
        "rank": "species",
        "ancestor_ids": [TAXON_TICKS],
        "aliases": ["rocky mountain wood tick", "dermacentor andersoni"],
    },
    {
        "id": TAXON_DERMACENTOR_VARIABILIS,
        "name": "Dermacentor variabilis",
        "preferred_common_name": "American dog tick",
        "rank": "species",
        "ancestor_ids": [TAXON_TICKS],
        "aliases": ["american dog tick", "dermacentor variabilis"],
    },
    {
        "id": TAXON_IXODES_PACIFICUS,
        "name": "Ixodes pacificus",
        "preferred_common_name": "Western black-legged tick",
        "rank": "species",
        "ancestor_ids": [TAXON_TICKS],
        "aliases": ["western black-legged tick", "ixodes pacificus"],
    },
    {
        "id": TAXON_PEROMYSCUS_MANICULATUS,
        "name": "Peromyscus maniculatus",
        "preferred_common_name": "deer mouse",
        "rank": "species",
        "ancestor_ids": [TAXON_RODENTS],
        "aliases": ["deer mouse", "peromyscus maniculatus"],
    },
    {
        "id": TAXON_CYNOMYS_GUNNISONI,
        "name": "Cynomys gunnisoni",
        "preferred_common_name": "Gunnison's prairie dog",
        "rank": "species",
        "ancestor_ids": [TAXON_RODENTS],
        "aliases": ["gunnison's prairie dog", "gunnison prairie dog", "cynomys gunnisoni"],
    },
    {
        "id": TAXON_OTOSPERMOPHILUS_VARIEGATUS,
        "name": "Otospermophilus variegatus",
        "preferred_common_name": "rock squirrel",
        "rank": "species",
        "ancestor_ids": [TAXON_RODENTS],
        "aliases": ["rock squirrel", "otospermophilus variegatus"],
    },
    {
        "id": TAXON_SYLVILAGUS_AUDUBONII,
        "name": "Sylvilagus audubonii",
        "preferred_common_name": "desert cottontail",
        "rank": "species",
        "ancestor_ids": [],
        "aliases": ["desert cottontail", "sylvilagus audubonii", "cottontail"],
    },
]


# ---------------------------------------------------------------------------
# Friendly-name -> taxon ID dispatch table for the `taxon=...` argument
# to the observation tools.
# ---------------------------------------------------------------------------
TAXON_KEYWORDS: dict[str, int] = {
    "ticks": TAXON_TICKS,
    "tick": TAXON_TICKS,
    "ixodida": TAXON_TICKS,
    "mosquitoes": TAXON_MOSQUITOES,
    "mosquito": TAXON_MOSQUITOES,
    "culicidae": TAXON_MOSQUITOES,
    "fleas": TAXON_FLEAS,
    "flea": TAXON_FLEAS,
    "siphonaptera": TAXON_FLEAS,
    "rodents": TAXON_RODENTS,
    "rodent": TAXON_RODENTS,
    "rodentia": TAXON_RODENTS,
}


# ---------------------------------------------------------------------------
# Canned observations. ~20 synthetic rows covering the focal taxa in
# AZ, with realistic coordinates inside Arizona's bounding box
# (roughly 31.3 -- 37.0 N, -114.8 -- -109.0 W). Dates are within the
# trailing year ending 2026-05-19 (today, per the project context).
# Every row carries the keys the tools advertise in their return
# contract.
# ---------------------------------------------------------------------------
def _obs(
    obs_id: int,
    observed_on: str,
    lat: float,
    lon: float,
    taxon_id: int,
    taxon_name: str,
    scientific_name: str,
    user_login: str,
    place_guess: str,
    quality_grade: str = "research",
    geoprivacy: str | None = None,
    photo_url: str | None = None,
    identifications_count: int = 2,
    comments_count: int = 0,
) -> dict[str, Any]:
    return {
        "observation_id": obs_id,
        "observed_on": observed_on,
        "lat": lat,
        "lon": lon,
        "geoprivacy": geoprivacy,
        "taxon_id": taxon_id,
        "taxon_name": taxon_name,
        "scientific_name": scientific_name,
        "user_login": user_login,
        "photo_url": photo_url
        or f"https://static.inaturalist.org/photos/{obs_id}/medium.jpg",
        "place_guess": place_guess,
        "quality_grade": quality_grade,
        "identifications_count": identifications_count,
        "comments_count": comments_count,
        "url": f"https://www.inaturalist.org/observations/{obs_id}",
    }


CANNED_OBSERVATIONS: list[dict[str, Any]] = [
    # ---- Ticks (Rhipicephalus sanguineus -- brown dog tick) ----
    _obs(
        201001, "2025-06-04", 32.2226, -110.9747,
        TAXON_RHIPICEPHALUS_SANGUINEUS,
        "Rhipicephalus sanguineus", "Rhipicephalus sanguineus",
        "tucson_hiker", "Tucson, Pima County, AZ",
        identifications_count=3, comments_count=1,
    ),
    _obs(
        201002, "2025-07-22", 33.4484, -112.0740,
        TAXON_RHIPICEPHALUS_SANGUINEUS,
        "Rhipicephalus sanguineus", "Rhipicephalus sanguineus",
        "phx_vet", "Phoenix, Maricopa County, AZ",
        identifications_count=2,
    ),
    _obs(
        201003, "2025-09-10", 31.5455, -110.2773,
        TAXON_RHIPICEPHALUS_SANGUINEUS,
        "Rhipicephalus sanguineus", "Rhipicephalus sanguineus",
        "sky_islands", "Sierra Vista, Cochise County, AZ",
    ),
    # ---- Dermacentor andersoni (Rocky Mountain wood tick) ----
    _obs(
        201004, "2025-05-30", 35.1983, -111.6513,
        TAXON_DERMACENTOR_ANDERSONI,
        "Dermacentor andersoni", "Dermacentor andersoni",
        "flagstaff_ranger", "Flagstaff, Coconino County, AZ",
    ),
    _obs(
        201005, "2025-06-18", 34.5400, -112.4685,
        TAXON_DERMACENTOR_ANDERSONI,
        "Dermacentor andersoni", "Dermacentor andersoni",
        "prescott_walker", "Prescott, Yavapai County, AZ",
    ),
    # ---- Dermacentor variabilis (American dog tick) ----
    _obs(
        201006, "2025-08-02", 32.7095, -114.6277,
        TAXON_DERMACENTOR_VARIABILIS,
        "Dermacentor variabilis", "Dermacentor variabilis",
        "yuma_naturalist", "Yuma, Yuma County, AZ",
    ),
    _obs(
        201007, "2025-09-15", 33.4152, -111.8315,
        TAXON_DERMACENTOR_VARIABILIS,
        "Dermacentor variabilis", "Dermacentor variabilis",
        "tempe_birder", "Tempe, Maricopa County, AZ",
    ),
    # ---- Ixodes pacificus (Western black-legged tick) ----
    _obs(
        201008, "2025-10-04", 35.2244, -114.0186,
        TAXON_IXODES_PACIFICUS,
        "Ixodes pacificus", "Ixodes pacificus",
        "mohave_ent", "Kingman, Mohave County, AZ",
    ),
    # ---- Mosquitoes (Culicidae) ----
    _obs(
        201009, "2025-07-04", 33.4484, -112.0740,
        TAXON_MOSQUITOES,
        "Culicidae", "Culex tarsalis",
        "maricopa_vector", "Phoenix, Maricopa County, AZ",
    ),
    _obs(
        201010, "2025-08-12", 32.2226, -110.9747,
        TAXON_MOSQUITOES,
        "Culicidae", "Aedes aegypti",
        "ua_ent_lab", "Tucson, Pima County, AZ",
        identifications_count=4,
    ),
    _obs(
        201011, "2025-09-01", 33.3062, -111.8413,
        TAXON_MOSQUITOES,
        "Culicidae", "Aedes aegypti",
        "chandler_naturalist", "Chandler, Maricopa County, AZ",
    ),
    # ---- Fleas (Siphonaptera) ----
    _obs(
        201012, "2025-07-30", 35.1983, -111.6513,
        TAXON_FLEAS,
        "Siphonaptera", "Oropsylla montana",
        "flagstaff_vet", "Flagstaff, Coconino County, AZ",
        identifications_count=2, comments_count=2,
    ),
    _obs(
        201013, "2025-08-25", 35.7000, -109.0500,
        TAXON_FLEAS,
        "Siphonaptera", "Oropsylla montana",
        "navajo_field", "Window Rock, Apache County, AZ",
        geoprivacy="obscured",
    ),
    # ---- Peromyscus maniculatus (deer mouse, hantavirus reservoir) ----
    _obs(
        201014, "2025-05-15", 35.1983, -111.6513,
        TAXON_PEROMYSCUS_MANICULATUS,
        "Peromyscus maniculatus", "Peromyscus maniculatus",
        "coconino_mammal", "Flagstaff, Coconino County, AZ",
    ),
    _obs(
        201015, "2025-11-02", 34.7445, -111.7888,
        TAXON_PEROMYSCUS_MANICULATUS,
        "Peromyscus maniculatus", "Peromyscus maniculatus",
        "sedona_walker", "Sedona, Yavapai County, AZ",
    ),
    # ---- Cynomys gunnisoni (Gunnison's prairie dog, plague) ----
    _obs(
        201016, "2025-06-10", 35.6870, -109.0606,
        TAXON_CYNOMYS_GUNNISONI,
        "Cynomys gunnisoni", "Cynomys gunnisoni",
        "apache_wildlife", "Apache County, AZ",
    ),
    _obs(
        201017, "2026-04-22", 35.0244, -110.6973,
        TAXON_CYNOMYS_GUNNISONI,
        "Cynomys gunnisoni", "Cynomys gunnisoni",
        "navajo_field", "Navajo County, AZ",
    ),
    # ---- Otospermophilus variegatus (rock squirrel, plague) ----
    _obs(
        201018, "2025-08-19", 32.2226, -110.9747,
        TAXON_OTOSPERMOPHILUS_VARIEGATUS,
        "Otospermophilus variegatus", "Otospermophilus variegatus",
        "saguaro_volunteer", "Saguaro National Park, Pima County, AZ",
    ),
    _obs(
        201019, "2026-03-05", 31.8633, -109.2294,
        TAXON_OTOSPERMOPHILUS_VARIEGATUS,
        "Otospermophilus variegatus", "Otospermophilus variegatus",
        "chiricahua_ranger", "Chiricahua National Monument, Cochise County, AZ",
    ),
    # ---- Sylvilagus audubonii (desert cottontail, tularemia) ----
    _obs(
        201020, "2026-02-14", 33.4484, -112.0740,
        TAXON_SYLVILAGUS_AUDUBONII,
        "Sylvilagus audubonii", "Sylvilagus audubonii",
        "phx_naturalist", "Phoenix, Maricopa County, AZ",
    ),
    _obs(
        201021, "2026-05-01", 32.2226, -110.9747,
        TAXON_SYLVILAGUS_AUDUBONII,
        "Sylvilagus audubonii", "Sylvilagus audubonii",
        "tucson_hiker", "Tucson, Pima County, AZ",
    ),
]


# ---------------------------------------------------------------------------
# AZ county-equivalent place IDs used by `inat_species_summary_az` for
# the county breakdown. (Real iNaturalist county place IDs are stable
# but the actual numeric values are not the point of the offline
# fallback -- the summary tool just needs *something* coherent to
# bucket by. When pointed at the live API the bucket key is the
# observation's ``place_guess`` plus the trailing ", AZ" -- i.e.
# whatever the observer recorded.)
# ---------------------------------------------------------------------------
AZ_COUNTY_HINTS: list[str] = [
    "Maricopa County",
    "Pima County",
    "Coconino County",
    "Yavapai County",
    "Mohave County",
    "Apache County",
    "Navajo County",
    "Cochise County",
    "Santa Cruz County",
    "Yuma County",
    "Pinal County",
    "Graham County",
    "Greenlee County",
    "Gila County",
    "La Paz County",
]


# ---------------------------------------------------------------------------
# Documented rate-limit policy. Sourced from
# https://api.inaturalist.org/v1/docs/ and
# https://www.inaturalist.org/pages/api+recommended+practices --
# briefly: ~100 requests/minute (with the project asking nicely that
# clients stay well below) and ~10,000 requests/day per IP address.
# A meaningful User-Agent is mandatory.
# ---------------------------------------------------------------------------
RATE_LIMIT_POLICY: str = (
    "iNaturalist public API rate limits (per IP, as documented at\n"
    "  https://api.inaturalist.org/v1/docs/\n"
    "  https://www.inaturalist.org/pages/api+recommended+practices ):\n"
    "\n"
    "  - ~100 requests per minute (the API asks clients to stay well "
    "below this).\n"
    "  - ~10,000 requests per day.\n"
    "  - Maximum page size of 200 observations; deeper paging beyond "
    "10,000 results requires the /observations endpoint with id-based "
    "cursors (id_above / order_by=id).\n"
    "  - A meaningful User-Agent is REQUIRED on every request "
    "(via INAT_USER_AGENT). Anonymous traffic is throttled or "
    "blocked.\n"
    "  - 429 responses include a Retry-After header; honor it.\n"
    "\n"
    "This server enforces the User-Agent requirement at startup and "
    "honors Retry-After on 429s."
)
