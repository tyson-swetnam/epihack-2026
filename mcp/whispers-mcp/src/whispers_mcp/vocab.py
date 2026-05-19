"""Cached controlled vocabularies for WHISPers.

These are stand-ins served by the MCP resources so an LLM can answer
"what event types are there?" without a network round-trip. The
authoritative lists live at ``/api/eventtypes/`` and ``/api/diagnoses/``
on the live service; refresh by hitting those endpoints with
``?no_page=true`` and replacing the constants below.
"""

from __future__ import annotations


# From the WHISPers user guide and public UI. WHISPers only distinguishes
# two top-level event types.
EVENT_TYPES: list[dict[str, str]] = [
    {
        "name": "Mortality/Morbidity",
        "description": (
            "A noteworthy occurrence of one or more sick or dead "
            "animals clustered in space and time."
        ),
    },
    {
        "name": "Surveillance",
        "description": (
            "Positive detections of a pathogen during active "
            "surveillance of apparently healthy live animals."
        ),
    },
]


# A representative slice of the WHISPers diagnosis vocabulary (the
# full list has hundreds of entries; this seeds the LLM with the
# common AZ-relevant ones and the names the EnrichmentAgent uses).
# Refresh from /api/diagnoses/?no_page=true for the authoritative set.
DIAGNOSIS_VOCABULARY: list[dict[str, str]] = [
    {"name": "Avian influenza, HPAI", "category": "Viral"},
    {"name": "Avian influenza, LPAI", "category": "Viral"},
    {"name": "Influenza A H5N1", "category": "Viral"},
    {"name": "West Nile virus", "category": "Viral"},
    {"name": "St. Louis encephalitis virus", "category": "Viral"},
    {"name": "Western equine encephalitis virus", "category": "Viral"},
    {"name": "Eastern equine encephalitis virus", "category": "Viral"},
    {"name": "Epizootic hemorrhagic disease virus", "category": "Viral"},
    {"name": "Rabies", "category": "Viral"},
    {"name": "Hantavirus", "category": "Viral"},
    {"name": "Sin Nombre virus", "category": "Viral"},
    {"name": "Yersinia pestis", "category": "Bacterial"},
    {"name": "Plague", "category": "Bacterial"},
    {"name": "Tularemia", "category": "Bacterial"},
    {"name": "Salmonellosis", "category": "Bacterial"},
    {"name": "Avian cholera", "category": "Bacterial"},
    {"name": "Mycoplasmosis", "category": "Bacterial"},
    {"name": "Chronic wasting disease", "category": "Prion"},
    {"name": "Aspergillosis", "category": "Fungal"},
    {"name": "Botulism, type C", "category": "Toxin"},
    {"name": "Lead toxicosis", "category": "Toxin"},
    {"name": "Trauma", "category": "Non-infectious"},
    {"name": "Undetermined", "category": "Unknown"},
    {"name": "Pending", "category": "Unknown"},
]


__all__ = ["EVENT_TYPES", "DIAGNOSIS_VOCABULARY"]
