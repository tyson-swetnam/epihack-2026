"""HTTP client for the USGS WHISPers service.

Paths are derived from the DRF URL router in
``USGS-WiM/whispersservices`` -> ``whispersapi/urls.py`` and from the
``EventSummaryFilter`` in ``whispersapi/filters.py``. The production
Angular client (``USGS-WiM/whispers``) reaches the service at
``https://whispers.usgs.gov/api/`` (its ``environment.prod.ts``).

Key API conventions:

* **Auth.** Token-based via DRF's standard ``rest_framework.authtoken``
  / DRF login views (``/login/``). All read endpoints filter
  ``queryset.filter(public=True)`` for anonymous callers (see
  ``EventViewSet.get_queryset`` in the upstream views.py), so no
  credentials are needed for the public event-listing tools this MCP
  exposes.
* **Pagination.** Standard DRF page/page_size. ``HistoryViewSet``
  (the base class) honors a ``no_page`` query parameter to return all
  rows in one shot.
* **Filtering.** EventSummary supports ``and_params``, ``complete``,
  ``public``, ``event_type``, ``diagnosis``, ``diagnosis_type``,
  ``species``, ``administrative_level_one`` (state),
  ``administrative_level_two`` (county), ``flyway``, ``country``,
  ``gnis_id``, ``affected_count__gte/__lte``, ``start_date``,
  ``end_date``, ``id``. Multi-value filters accept comma-separated
  IDs.

Spatial bbox filtering is NOT a first-class server-side filter; this
client pulls the broader date-windowed result and applies the bbox
client-side against ``event_locations[].latitude/longitude``.

Mock fallback: if ``WHISPERS_USE_MOCK=1`` is set, or if a live call
raises a network error and ``WHISPERS_DISABLE_FALLBACK`` is not set,
the client returns rows derived from ``canned.CANNED_EVENTS``.
"""

from __future__ import annotations

import asyncio
import os
from datetime import date, timedelta
from typing import Any, Iterable

import httpx

from .canned import CANNED_EVENTS
from .models import CannedEvent, EventDetail, EventRow

DEFAULT_BASE_URL = os.environ.get(
    "WHISPERS_BASE_URL", "https://whispers.usgs.gov/api"
)
PUBLIC_EVENT_BASE = os.environ.get(
    "WHISPERS_PUBLIC_EVENT_BASE", "https://whispers.usgs.gov/event"
)

PATHS = {
    "events":           os.environ.get("WHISPERS_PATH_EVENTS",           "/events"),
    "event_summaries":  os.environ.get("WHISPERS_PATH_EVENT_SUMMARIES",  "/eventsummaries"),
    "event_details":    os.environ.get("WHISPERS_PATH_EVENT_DETAILS",    "/eventdetails"),
    "event_types":      os.environ.get("WHISPERS_PATH_EVENT_TYPES",      "/eventtypes"),
    "event_locations":  os.environ.get("WHISPERS_PATH_EVENT_LOCATIONS",  "/eventlocations"),
    "species":          os.environ.get("WHISPERS_PATH_SPECIES",          "/species"),
    "diagnoses":        os.environ.get("WHISPERS_PATH_DIAGNOSES",        "/diagnoses"),
    "admin_l1":         os.environ.get("WHISPERS_PATH_ADMIN_L1",         "/administrativelevelones"),
    "admin_l2":         os.environ.get("WHISPERS_PATH_ADMIN_L2",         "/administrativeleveltwos"),
}


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _iso_days_ago(days: int) -> str:
    return (date.today() - timedelta(days=days)).isoformat()


def _rows(payload: Any) -> list[dict[str, Any]]:
    """DRF paginated responses are ``{count, next, previous, results}``;
    ``?no_page=true`` flattens to a list. Be tolerant of either."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if "results" in payload and isinstance(payload["results"], list):
            return payload["results"]
        if "rows" in payload and isinstance(payload["rows"], list):
            return payload["rows"]
    return []


# ------------------------------------------------------ projection helpers
def _str_or_name(value: Any) -> str | None:
    """Many WHISPers fields can be either an int FK or an expanded
    dict ``{id, name, ...}``. Normalize to a display string."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("name") or value.get("abbreviation") or value.get("display_name")
    return str(value)


def _first_location_coords(
    eventlocations: list[dict[str, Any]] | None,
) -> tuple[float | None, float | None]:
    for loc in eventlocations or []:
        lat = loc.get("latitude")
        lon = loc.get("longitude")
        if lat is not None and lon is not None:
            try:
                return float(lat), float(lon)
            except (TypeError, ValueError):
                continue
    return None, None


def project_event_summary(row: dict[str, Any]) -> EventRow:
    """Project a DRF event-summary row to our flat EventRow shape."""
    event_id = int(row.get("id") or row.get("event") or row.get("event_id") or 0)
    locations = row.get("eventlocations") or row.get("event_locations") or []
    species_set: list[str] = []
    counties: list[str] = []
    states: list[str] = []
    for loc in locations:
        admin2 = _str_or_name(loc.get("administrative_level_two"))
        admin1 = _str_or_name(loc.get("administrative_level_one"))
        if admin2:
            counties.append(admin2)
        if admin1:
            states.append(admin1)
        for sp in loc.get("locationspecies", []) or []:
            name = _str_or_name(sp.get("species"))
            if name:
                species_set.append(name)
    # de-dupe while preserving order
    seen: set[str] = set()
    species = [s for s in species_set if not (s in seen or seen.add(s))]
    diagnoses_raw = (
        row.get("eventdiagnoses")
        or row.get("event_diagnoses")
        or row.get("speciesdiagnoses")
        or []
    )
    diagnoses: list[str] = []
    for d in diagnoses_raw:
        name = _str_or_name(d.get("diagnosis") if isinstance(d, dict) else d)
        if name and name not in diagnoses:
            diagnoses.append(name)
    lat, lon = _first_location_coords(locations)
    location_label: str | None = None
    if counties and states:
        location_label = f"{counties[0]} County, {states[0]}"
    elif states:
        location_label = states[0]
    return EventRow(
        event_id=event_id,
        start_date=row.get("start_date"),
        end_date=row.get("end_date"),
        state=states[0] if states else None,
        county=counties[0] if counties else None,
        location=location_label,
        species=species,
        affected_count=row.get("affected_count"),
        diagnosis=diagnoses,
        event_type=_str_or_name(row.get("event_type")),
        public=bool(row.get("public", True)),
        lat=lat,
        lon=lon,
        public_url=f"{PUBLIC_EVENT_BASE}/{event_id}" if event_id else None,
    )


# -------------------------------------------------------------------- filters
def _matches_state(row: EventRow, state: str | None) -> bool:
    if state is None:
        return True
    return (row.state or "").upper() == state.upper()


def _matches_species(row: EventRow, species: str | None) -> bool:
    if species is None:
        return True
    needle = species.lower()
    return any(needle in (s or "").lower() for s in row.species)


def _matches_diagnosis(row: EventRow, diagnosis: str | None) -> bool:
    if diagnosis is None:
        return True
    needle = diagnosis.lower()
    return any(needle in (d or "").lower() for d in row.diagnosis)


def _matches_bbox(
    row: EventRow,
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
) -> bool:
    if row.lat is None or row.lon is None:
        return False
    return (min_lon <= row.lon <= max_lon) and (min_lat <= row.lat <= max_lat)


def _within_days(row: EventRow, days: int) -> bool:
    if days <= 0:
        return True
    cutoff = _iso_days_ago(days)
    start = row.start_date or ""
    return start >= cutoff


# ----------------------------------------------------------------- client
class WhispersClient:
    """Thin async client + mock-fallback wrapper for the WHISPers API."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        use_mock: bool | None = None,
        disable_fallback: bool | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._http = httpx.AsyncClient(
            timeout=timeout,
            headers={"Accept": "application/json"},
        )
        env_use_mock = _truthy(os.environ.get("WHISPERS_USE_MOCK"))
        env_disable_fb = _truthy(os.environ.get("WHISPERS_DISABLE_FALLBACK"))
        self.use_mock: bool = env_use_mock if use_mock is None else use_mock
        self.disable_fallback: bool = (
            env_disable_fb if disable_fallback is None else disable_fallback
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    # --------------------------------------------------------- internal
    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        # Gentle 5xx backoff: retry once after a short sleep.
        url = f"{self.base_url}{path}"
        for attempt in range(2):
            resp = await self._http.get(url, params=params or {})
            if 500 <= resp.status_code < 600 and attempt == 0:
                await asyncio.sleep(0.5)
                continue
            resp.raise_for_status()
            return resp.json()
        # Unreachable, but keeps the type-checker happy.
        raise RuntimeError("retry loop exited without returning")  # pragma: no cover

    async def _fetch_event_summaries(
        self, params: dict[str, Any]
    ) -> list[dict[str, Any]]:
        # Trailing slash is required by Django's APPEND_SLASH default.
        payload = await self._get(
            f"{PATHS['event_summaries']}/", params={**params, "no_page": "true"}
        )
        return _rows(payload)

    # ------------------------------------------------------ public ops
    async def fetch_events(
        self,
        *,
        days: int | None = 90,
        state: str | None = None,
        county_fips: str | None = None,
        species: str | None = None,
        diagnosis: str | None = None,
        limit: int = 100,
    ) -> list[EventRow]:
        """Return up to ``limit`` recent public events, optionally filtered."""
        if self.use_mock:
            return self._mock_events(
                days=days,
                state=state,
                species=species,
                diagnosis=diagnosis,
                limit=limit,
            )
        params: dict[str, Any] = {"public": "true"}
        if days is not None:
            params["start_date"] = _iso_days_ago(days)
        # The upstream uses numeric FK ids for state/species/diagnosis, but
        # we accept names + let the server's text-based search match if
        # callers pass strings. The mock filter handles the readable
        # values; for the live path we pass through and depend on the
        # server's tolerance.
        if state:
            params["administrative_level_one_name"] = state
        if county_fips:
            params["gnis_id"] = county_fips
        try:
            rows = await self._fetch_event_summaries(params)
        except (httpx.HTTPError, httpx.NetworkError) as exc:
            if self.disable_fallback:
                raise RuntimeError(
                    f"WHISPers live fetch failed and fallback disabled: {exc}"
                ) from exc
            return self._mock_events(
                days=days,
                state=state,
                species=species,
                diagnosis=diagnosis,
                limit=limit,
            )
        projected = [project_event_summary(r) for r in rows]
        projected = [
            r
            for r in projected
            if _matches_species(r, species) and _matches_diagnosis(r, diagnosis)
        ]
        return projected[:limit]

    async def fetch_event_detail(self, event_id: int) -> EventDetail:
        if self.use_mock:
            return self._mock_detail(event_id)
        try:
            payload = await self._get(f"{PATHS['event_details']}/{event_id}/")
        except (httpx.HTTPError, httpx.NetworkError) as exc:
            if self.disable_fallback:
                raise RuntimeError(
                    f"WHISPers live fetch failed and fallback disabled: {exc}"
                ) from exc
            return self._mock_detail(event_id)
        if not isinstance(payload, dict):
            raise RuntimeError(f"unexpected event-detail payload: {type(payload)}")
        locations = payload.get("eventlocations") or payload.get("event_locations") or []
        eventdiagnoses = (
            payload.get("eventdiagnoses") or payload.get("event_diagnoses") or []
        )
        speciesdiagnoses = (
            payload.get("speciesdiagnoses") or payload.get("species_diagnoses") or []
        )
        return EventDetail(
            event_id=int(payload.get("id", event_id)),
            event_type=_str_or_name(payload.get("event_type")),
            start_date=payload.get("start_date"),
            end_date=payload.get("end_date"),
            affected_count=payload.get("affected_count"),
            complete=payload.get("complete"),
            public=bool(payload.get("public", True)),
            public_url=f"{PUBLIC_EVENT_BASE}/{event_id}",
            event_locations=locations,
            event_diagnoses=eventdiagnoses,
            species_diagnoses=speciesdiagnoses,
            raw=payload,
        )

    async def fetch_events_bbox(
        self,
        *,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        days: int = 90,
        limit: int = 200,
    ) -> list[EventRow]:
        """Spatial bbox query (client-side filter on a date-windowed pull)."""
        # Pull a generous window and filter locally; bbox isn't a
        # native EventSummary filter parameter.
        rows = await self.fetch_events(
            days=days, limit=max(limit * 4, limit)
        )
        return [
            r
            for r in rows
            if _matches_bbox(r, min_lon, min_lat, max_lon, max_lat)
        ][:limit]

    # ------------------------------------------------------- mock paths
    def _canned_rows(self) -> list[EventRow]:
        return [c.to_row(public_base=PUBLIC_EVENT_BASE) for c in CANNED_EVENTS]

    def _mock_events(
        self,
        *,
        days: int | None,
        state: str | None,
        species: str | None,
        diagnosis: str | None,
        limit: int,
    ) -> list[EventRow]:
        rows = self._canned_rows()
        out = [
            r
            for r in rows
            if (days is None or _within_days_canned(r, days))
            and _matches_state(r, state)
            and _matches_species(r, species)
            and _matches_diagnosis(r, diagnosis)
        ]
        # Most-recent first
        out.sort(key=lambda r: r.start_date or "", reverse=True)
        return out[:limit]

    def _mock_detail(self, event_id: int) -> EventDetail:
        for c in CANNED_EVENTS:
            if c.event_id == event_id:
                return c.to_detail(public_base=PUBLIC_EVENT_BASE)
        raise LookupError(f"event {event_id} not found in canned dataset")


def _within_days_canned(row: EventRow, days: int) -> bool:
    """Slack version of date filter for the canned data.

    Historical canned events (e.g. 1993 hantavirus) intentionally fall
    outside any normal "last N days" window; we still want them
    available to the species/diagnosis filters when the caller is
    asking about that pathogen specifically. So:

      * if ``days`` <= 0, accept everything.
      * if the event is open-ended (``end_date is None``) accept it.
      * otherwise apply the normal cutoff.
    """
    if days <= 0:
        return True
    if not row.end_date:
        return True
    cutoff = _iso_days_ago(days)
    return (row.start_date or "") >= cutoff or row.end_date >= cutoff


__all__ = [
    "WhispersClient",
    "DEFAULT_BASE_URL",
    "PATHS",
    "project_event_summary",
]
