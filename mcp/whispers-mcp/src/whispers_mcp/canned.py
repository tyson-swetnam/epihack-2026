"""Canned WHISPers dataset for offline development & tests.

These rows are **synthetic but historically grounded** stand-ins for
real WHISPers entries. They exist so that:

  * unit tests don't have to hit the live USGS service;
  * the EnrichmentAgent in ``agents/src/onehealth_agents/enrichment.py``
    has something to wire against during EpiHack hacking, even if
    ``whispers.usgs.gov`` is unreachable from a workshop venue;
  * the AZ summary tool always returns a non-empty result the
    Cluster Detection Agent can benchmark new community reports
    against.

Real WHISPers events are individually addressable at
``https://whispers.usgs.gov/event/<id>`` -- the public_url field
generated from these IDs will 404, which is intentional: they're
clearly canned. If you replace one with a true historical event,
swap in its real id so the link resolves.

Historical reference cases the canned data is modelled on:

  * 1993 Four Corners hantavirus outbreak (Sin Nombre virus, deer
    mice, Navajo Nation).
  * 2022+ HPAI H5N1 wild-bird detections across Arizona flyways.
  * 2025 plague (Yersinia pestis) activity in prairie-dog colonies
    on the Colorado Plateau.

All coordinates are inside Arizona's bounding box; the bbox-filter
test relies on that.
"""

from __future__ import annotations

from .models import CannedEvent


# A small but representative dataset. Coordinates are real localities;
# event IDs are placeholders in the 9_000_000+ band so they don't
# collide with any real WHISPers row.
CANNED_EVENTS: list[CannedEvent] = [
    CannedEvent(
        event_id=9000001,
        event_type="Mortality/Morbidity",
        start_date="1993-05-14",
        end_date="1993-11-30",
        state="AZ",
        county="Navajo",
        lat=36.0640,
        lon=-109.5453,  # Chinle area
        species=["Peromyscus maniculatus"],
        diagnosis=["Hantavirus", "Sin Nombre virus"],
        affected_count=24,
        location_label="Four Corners region, Navajo Nation",
        notes=(
            "Canned stand-in for the 1993 Four Corners hantavirus "
            "outbreak. Deer mouse reservoir; archetypal example of "
            "the Cluster Detection Agent's hantavirus benchmark."
        ),
    ),
    CannedEvent(
        event_id=9000002,
        event_type="Mortality/Morbidity",
        start_date="1993-06-02",
        end_date="1993-09-15",
        state="AZ",
        county="Apache",
        lat=35.5,
        lon=-109.05,
        species=["Peromyscus maniculatus"],
        diagnosis=["Hantavirus"],
        affected_count=12,
        location_label="Apache County, AZ",
        notes="Companion cluster to event 9000001.",
    ),
    CannedEvent(
        event_id=9000003,
        event_type="Surveillance",
        start_date="2022-12-10",
        end_date="2023-02-28",
        state="AZ",
        county="Maricopa",
        lat=33.5,
        lon=-112.0,
        species=["Anas platyrhynchos", "Branta canadensis"],
        diagnosis=["Avian influenza, HPAI", "Influenza A H5N1"],
        affected_count=37,
        location_label="Maricopa County wetlands",
        notes="HPAI H5N1 wild-waterfowl detection along the Pacific Flyway.",
    ),
    CannedEvent(
        event_id=9000004,
        event_type="Surveillance",
        start_date="2023-01-22",
        end_date="2023-03-10",
        state="AZ",
        county="Yuma",
        lat=32.7,
        lon=-114.6,
        species=["Anas platyrhynchos"],
        diagnosis=["Avian influenza, HPAI"],
        affected_count=8,
        location_label="Yuma agricultural area",
        notes="HPAI surveillance positive in mallard, Yuma County.",
    ),
    CannedEvent(
        event_id=9000005,
        event_type="Mortality/Morbidity",
        start_date="2024-08-04",
        end_date="2024-10-20",
        state="AZ",
        county="Coconino",
        lat=35.95,
        lon=-111.65,
        species=["Cynomys gunnisoni"],
        diagnosis=["Yersinia pestis", "Plague"],
        affected_count=140,
        location_label="Gunnison's prairie dog colony die-off, Coconino County",
        notes=(
            "Plague enzootic in Gunnison's prairie dogs; sentinel for "
            "human risk in adjacent communities. Mirrors the 2024-25 "
            "Coconino plague signal."
        ),
    ),
    CannedEvent(
        event_id=9000006,
        event_type="Mortality/Morbidity",
        start_date="2025-04-12",
        end_date=None,
        state="AZ",
        county="Coconino",
        lat=35.20,
        lon=-111.65,
        species=["Cynomys gunnisoni", "Sciurus aberti"],
        diagnosis=["Yersinia pestis"],
        affected_count=58,
        location_label="Flagstaff-area prairie-dog colonies",
        notes=(
            "Active 2025 plague event used by the Triage Agent's "
            "VBD-branch outbreak_check. End date null = still open."
        ),
    ),
    CannedEvent(
        event_id=9000007,
        event_type="Mortality/Morbidity",
        start_date="2024-09-15",
        end_date="2024-12-01",
        state="AZ",
        county="Pima",
        lat=32.22,
        lon=-110.92,
        species=["Corvus brachyrhynchos"],
        diagnosis=["West Nile virus"],
        affected_count=18,
        location_label="Tucson urban corvids",
        notes="Co-occurs with high WNV vector index in Pima during the same window.",
    ),
    CannedEvent(
        event_id=9000008,
        event_type="Surveillance",
        start_date="2025-02-05",
        end_date="2025-04-15",
        state="AZ",
        county="Santa Cruz",
        lat=31.55,
        lon=-110.75,
        species=["Odocoileus hemionus"],
        diagnosis=["Epizootic hemorrhagic disease virus"],
        affected_count=6,
        location_label="Patagonia mule deer",
        notes="EHDV surveillance near the Patagonia hiking corridor in Scenario A.",
    ),
    CannedEvent(
        event_id=9000009,
        event_type="Mortality/Morbidity",
        start_date="2025-03-01",
        end_date="2025-05-01",
        state="NM",
        county="San Juan",
        lat=36.80,
        lon=-108.20,
        species=["Cynomys gunnisoni"],
        diagnosis=["Yersinia pestis"],
        affected_count=22,
        location_label="San Juan County prairie-dog die-off (NM)",
        notes=(
            "Cross-border NM event included to verify bbox filtering "
            "(should be excluded from AZ-only summaries)."
        ),
    ),
    CannedEvent(
        event_id=9000010,
        event_type="Surveillance",
        start_date="2024-11-08",
        end_date="2025-01-30",
        state="CA",
        county="Imperial",
        lat=33.0,
        lon=-115.5,
        species=["Anas platyrhynchos"],
        diagnosis=["Avian influenza, HPAI"],
        affected_count=14,
        location_label="Salton Sea HPAI surveillance",
        notes=(
            "Out-of-state record retained so bbox and state filters "
            "have a negative example to exclude."
        ),
    ),
]


# AZ bbox used to verify spatial filtering. Pulled from the
# state's published extent (roughly).
AZ_BBOX = (-114.82, 31.33, -109.05, 37.00)  # (min_lon, min_lat, max_lon, max_lat)


__all__ = ["CANNED_EVENTS", "AZ_BBOX"]
