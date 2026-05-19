"""Pydantic models for normalized WHISPers rows.

The upstream Django REST Framework responses are deeply nested
(``event -> eventlocations[] -> locationspecies[] -> species`` and
``event -> eventdiagnoses[] -> diagnosis``). We flatten that into one
row per event for the ``recent`` / ``bbox`` / ``by_species`` /
``by_diagnosis`` tools, and pass the full nested record through for
``event_detail``.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ----------------------------------------------------------- flattened
class EventRow(BaseModel):
    """One-row-per-event projection used by list-style tools.

    The fields mirror what `EnrichmentAgent` needs to edge a community
    report to a co-located wildlife mortality signal (see
    ``plan/04-data-flows.md`` Scenario D).
    """

    event_id: int
    start_date: str | None = None
    end_date: str | None = None
    state: str | None = Field(None, description="USPS state code, e.g. 'AZ'.")
    county: str | None = None
    location: str | None = Field(
        None,
        description="Human-readable location string (county + state, or named locality).",
    )
    species: list[str] = Field(default_factory=list)
    affected_count: int | None = None
    diagnosis: list[str] = Field(default_factory=list)
    event_type: str | None = Field(
        None, description='"Mortality/Morbidity" or "Surveillance".'
    )
    public: bool = True
    lat: float | None = None
    lon: float | None = None
    public_url: str | None = Field(
        None, description="Public WHISPers UI permalink for the event."
    )


class EventDetail(BaseModel):
    """Full nested WHISPers event record."""

    event_id: int
    event_type: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    affected_count: int | None = None
    complete: bool | None = None
    public: bool = True
    public_url: str | None = None
    event_locations: list[dict[str, Any]] = Field(default_factory=list)
    event_diagnoses: list[dict[str, Any]] = Field(default_factory=list)
    species_diagnoses: list[dict[str, Any]] = Field(default_factory=list)
    raw: dict[str, Any] = Field(
        default_factory=dict,
        description="Original payload passthrough for clients that need every field.",
    )


class CannedEvent(BaseModel):
    """The shape canned/mock events are stored in inside the package.

    Carries enough geometry + vocabulary for every documented tool's
    filter to do something sensible offline.
    """

    event_id: int
    event_type: str
    start_date: str
    end_date: str | None = None
    state: str
    county: str
    lat: float
    lon: float
    species: list[str]
    diagnosis: list[str]
    affected_count: int | None = None
    location_label: str | None = None
    notes: str = ""

    def to_row(self, public_base: str = "https://whispers.usgs.gov/event") -> EventRow:
        return EventRow(
            event_id=self.event_id,
            start_date=self.start_date,
            end_date=self.end_date,
            state=self.state,
            county=self.county,
            location=self.location_label or f"{self.county} County, {self.state}",
            species=list(self.species),
            affected_count=self.affected_count,
            diagnosis=list(self.diagnosis),
            event_type=self.event_type,
            public=True,
            lat=self.lat,
            lon=self.lon,
            public_url=f"{public_base}/{self.event_id}",
        )

    def to_detail(self, public_base: str = "https://whispers.usgs.gov/event") -> EventDetail:
        return EventDetail(
            event_id=self.event_id,
            event_type=self.event_type,
            start_date=self.start_date,
            end_date=self.end_date,
            affected_count=self.affected_count,
            complete=self.end_date is not None,
            public=True,
            public_url=f"{public_base}/{self.event_id}",
            event_locations=[
                {
                    "administrative_level_one": self.state,
                    "administrative_level_two": self.county,
                    "latitude": self.lat,
                    "longitude": self.lon,
                    "name": self.location_label,
                }
            ],
            event_diagnoses=[{"diagnosis": d} for d in self.diagnosis],
            species_diagnoses=[
                {"species": s, "diagnosis": self.diagnosis[0] if self.diagnosis else None}
                for s in self.species
            ],
            raw={"notes": self.notes, "source": "canned"},
        )


__all__ = ["EventRow", "EventDetail", "CannedEvent"]
