"""Client for the Maricopa Association of Governments Heat Relief Network.

The HRN is the regional cooling-center / hydration / respite / donation
program operating each summer from **May 1 through September 30** across
Maricopa County (the Phoenix metro). The public storefront --
https://hrn.azmag.gov/ -- is an ArcGIS-powered web map, and the
underlying data is published via a MAG-hosted ArcGIS service at

    https://geo.azmag.gov/arcgis/rest/services/maps/Heat_Relief_Network

That URL has drifted across HRN seasons (the layer index, the map vs.
feature service flavour, even the service name) more than once, so the
default is **mock**: a small canned dataset with a dozen realistic
Phoenix-metro sites lives in this module. Set
``MAG_HRN_FEATURE_SERVICE_URL`` in the environment to flip to live mode.

The expected real-mode URL is something like one of:

    https://geo.azmag.gov/arcgis/rest/services/maps/Heat_Relief_Network/FeatureServer
    https://geo.azmag.gov/arcgis/rest/services/maps/Heat_Relief_Network/MapServer
    https://services.arcgis.com/<org>/arcgis/rest/services/HRN_<year>/FeatureServer

with one layer per service type (cooling / hydration / respite /
donation) -- the client queries layer 0 by default but accepts
``MAG_HRN_FEATURE_LAYER`` if a deployer needs to point at a specific
layer index, and walks all layers when set to ``"all"``.

The supply-status tool is documented separately as **mock-only** until
MAG publishes a real occupancy / supply feed; see ``plan/01`` Heat-Q2
for the gap analysis.
"""

from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from typing import Any, Iterable

import httpx


# ---------------------------------------------------------------------------
# Env-overridable configuration
# ---------------------------------------------------------------------------
#
# When ``MAG_HRN_FEATURE_SERVICE_URL`` is set the client switches from
# the canned dataset to the real ArcGIS service. The URL should point at
# the *service root* (i.e. ending in ``/FeatureServer`` or
# ``/MapServer``); the client appends ``/{layer}/query`` itself.
DEFAULT_FEATURE_SERVICE_URL: str | None = (
    os.environ.get("MAG_HRN_FEATURE_SERVICE_URL") or None
)

# Layer index inside the feature service. The MAG HRN service has used a
# single combined layer plus per-type layers (Cooling Center, Respite
# Center, Hydration, Donation) at varying indices; ``"all"`` walks every
# layer the service advertises.
DEFAULT_FEATURE_LAYER: str = os.environ.get("MAG_HRN_FEATURE_LAYER", "0")

# Optional auth -- the public HRN service is anonymous today but a future
# operator-only feed might require a token.
DEFAULT_API_TOKEN: str | None = os.environ.get("MAG_HRN_API_TOKEN") or None

# Operating season. The HRN runs May 1 -- September 30 each year; outside
# this window the canned dataset returns an empty list. Both bounds are
# inclusive. Overridable for testing.
SEASON_START_MONTH_DAY: tuple[int, int] = (5, 1)
SEASON_END_MONTH_DAY: tuple[int, int] = (9, 30)


# ---------------------------------------------------------------------------
# Service-type vocabulary -- kept tight so callers can filter reliably.
# ---------------------------------------------------------------------------
SERVICE_TYPES: tuple[str, ...] = (
    "cooling",     # indoor cooling-center: air-conditioned space to cool down
    "hydration",   # outdoor or walk-up water-bottle distribution
    "respite",     # cooling center + uninterrupted rest (often overnight-ish)
    "donation",    # drop-off point for water / supplies (not a relief site)
)

# A friendly text description per type, surfaced via the
# ``mag://service-types`` MCP resource.
SERVICE_TYPE_DESCRIPTIONS: dict[str, str] = {
    "cooling": (
        "Indoor cooling center: an air-conditioned indoor space where "
        "people can cool down during operating hours."
    ),
    "hydration": (
        "Hydration station: walk-up distribution of bottled water "
        "(sometimes electrolyte packets / sunscreen / hats); may be "
        "outdoors and may not provide indoor seating."
    ),
    "respite": (
        "Respite center: a cooling center that also allows uninterrupted "
        "rest for an extended period (e.g. sleeping is permitted)."
    ),
    "donation": (
        "Donation drop-off: a site that accepts public donations of "
        "water, sunscreen, hats, and lightweight clothing for the "
        "Heat Relief Network. Not a relief site for those in need."
    ),
}


# ---------------------------------------------------------------------------
# Canned dataset
# ---------------------------------------------------------------------------
#
# A dozen well-known Phoenix metro sites with plausible coordinates and
# operating hours. **These are not authoritative HRN registrations** --
# they are mock fixtures whose lat/lons and service notes are meant to
# look real enough to demo the multi-MCP join described in
# ``plan/02-mcp-integration.md`` (Heat-Q1) and Scenario C of
# ``plan/04-data-flows.md``. Always defer to https://hrn.azmag.gov/ for
# the real, current network.
#
# Hours are stored as a dict ``day -> [open_iso_local, close_iso_local]``
# in 24h ``HH:MM`` strings, or ``"closed"`` if not open. ``services`` is
# a list of values from ``SERVICE_TYPES`` (one site can do more than one
# -- a library may be both cooling and hydration).
MOCK_CENTERS: list[dict[str, Any]] = [
    {
        "id": "mag.hrn.mock.0001",
        "name": "Burton Barr Central Library",
        "address": "1221 N Central Ave",
        "city": "Phoenix",
        "postal_code": "85004",
        "lat": 33.4734,
        "lon": -112.0740,
        "services": ["cooling", "hydration"],
        "pets_ok": False,
        "hours": {
            "Mon": ["10:00", "20:00"],
            "Tue": ["10:00", "20:00"],
            "Wed": ["10:00", "20:00"],
            "Thu": ["10:00", "20:00"],
            "Fri": ["10:00", "17:00"],
            "Sat": ["10:00", "17:00"],
            "Sun": ["13:00", "17:00"],
        },
        "operator": "City of Phoenix Public Library",
        "notes": (
            "Large air-conditioned reading rooms, water-bottle fill stations, "
            "and seating throughout. Service-animal access only."
        ),
    },
    {
        "id": "mag.hrn.mock.0002",
        "name": "Andre House of Hospitality",
        "address": "213 S 11th Ave",
        "city": "Phoenix",
        "postal_code": "85007",
        "lat": 33.4452,
        "lon": -112.0840,
        "services": ["cooling", "respite", "hydration"],
        "pets_ok": True,
        "hours": {
            "Mon": ["08:00", "20:00"],
            "Tue": ["08:00", "20:00"],
            "Wed": ["08:00", "20:00"],
            "Thu": ["08:00", "20:00"],
            "Fri": ["08:00", "20:00"],
            "Sat": ["08:00", "20:00"],
            "Sun": ["08:00", "20:00"],
        },
        "operator": "Andre House",
        "notes": (
            "Full-service respite for unsheltered residents; meals, showers, "
            "and overnight options off-site. Pet-friendly when leashed."
        ),
    },
    {
        "id": "mag.hrn.mock.0003",
        "name": "Mesa Main Library",
        "address": "64 E 1st St",
        "city": "Mesa",
        "postal_code": "85201",
        "lat": 33.4151,
        "lon": -111.8311,
        "services": ["cooling", "hydration"],
        "pets_ok": False,
        "hours": {
            "Mon": ["09:00", "20:00"],
            "Tue": ["09:00", "20:00"],
            "Wed": ["09:00", "20:00"],
            "Thu": ["09:00", "20:00"],
            "Fri": ["09:00", "17:00"],
            "Sat": ["09:00", "17:00"],
            "Sun": "closed",
        },
        "operator": "City of Mesa Library",
        "notes": "Cooling lobby + reading rooms; water-fountain bottle fill.",
    },
    {
        "id": "mag.hrn.mock.0004",
        "name": "Tempe Public Library",
        "address": "3500 S Rural Rd",
        "city": "Tempe",
        "postal_code": "85282",
        "lat": 33.3870,
        "lon": -111.9263,
        "services": ["cooling", "hydration"],
        "pets_ok": False,
        "hours": {
            "Mon": ["10:00", "21:00"],
            "Tue": ["10:00", "21:00"],
            "Wed": ["10:00", "21:00"],
            "Thu": ["10:00", "21:00"],
            "Fri": ["10:00", "18:00"],
            "Sat": ["10:00", "18:00"],
            "Sun": ["12:00", "18:00"],
        },
        "operator": "City of Tempe",
        "notes": (
            "Large facility within the Tempe Connections complex; popular "
            "extended-hours stop."
        ),
    },
    {
        "id": "mag.hrn.mock.0005",
        "name": "Glendale Main Library",
        "address": "5959 W Brown St",
        "city": "Glendale",
        "postal_code": "85302",
        "lat": 33.5717,
        "lon": -112.1859,
        "services": ["cooling"],
        "pets_ok": False,
        "hours": {
            "Mon": ["10:00", "20:00"],
            "Tue": ["10:00", "20:00"],
            "Wed": ["10:00", "20:00"],
            "Thu": ["10:00", "20:00"],
            "Fri": ["10:00", "17:00"],
            "Sat": ["10:00", "17:00"],
            "Sun": "closed",
        },
        "operator": "City of Glendale",
        "notes": "Cooling lobby and program rooms; no walk-up hydration.",
    },
    {
        "id": "mag.hrn.mock.0006",
        "name": "Scottsdale Civic Center Library",
        "address": "3839 N Drinkwater Blvd",
        "city": "Scottsdale",
        "postal_code": "85251",
        "lat": 33.4928,
        "lon": -111.9249,
        "services": ["cooling", "hydration"],
        "pets_ok": False,
        "hours": {
            "Mon": ["09:00", "20:00"],
            "Tue": ["09:00", "20:00"],
            "Wed": ["09:00", "20:00"],
            "Thu": ["09:00", "20:00"],
            "Fri": ["09:00", "18:00"],
            "Sat": ["09:00", "18:00"],
            "Sun": ["13:00", "17:00"],
        },
        "operator": "Scottsdale Public Library",
        "notes": "Civic-center campus; water-fountain bottle fill.",
    },
    {
        "id": "mag.hrn.mock.0007",
        "name": "First United Methodist Church Phoenix",
        "address": "5510 N Central Ave",
        "city": "Phoenix",
        "postal_code": "85012",
        "lat": 33.5197,
        "lon": -112.0742,
        "services": ["cooling", "hydration", "donation"],
        "pets_ok": True,
        "hours": {
            "Mon": ["09:00", "16:00"],
            "Tue": ["09:00", "16:00"],
            "Wed": ["09:00", "16:00"],
            "Thu": ["09:00", "16:00"],
            "Fri": ["09:00", "16:00"],
            "Sat": "closed",
            "Sun": ["09:00", "13:00"],
        },
        "operator": "First United Methodist Church",
        "notes": (
            "Sanctuary lobby cooled; volunteer-staffed hydration; also a "
            "donation drop-off (bottled water / hats / sunscreen)."
        ),
    },
    {
        "id": "mag.hrn.mock.0008",
        "name": "St. Vincent de Paul Family Dining Room",
        "address": "420 W Watkins Rd",
        "city": "Phoenix",
        "postal_code": "85003",
        "lat": 33.4286,
        "lon": -112.0810,
        "services": ["cooling", "respite", "hydration"],
        "pets_ok": False,
        "hours": {
            "Mon": ["08:00", "18:00"],
            "Tue": ["08:00", "18:00"],
            "Wed": ["08:00", "18:00"],
            "Thu": ["08:00", "18:00"],
            "Fri": ["08:00", "18:00"],
            "Sat": ["08:00", "14:00"],
            "Sun": ["08:00", "14:00"],
        },
        "operator": "Society of St. Vincent de Paul",
        "notes": (
            "Indoor dining/cooling for unsheltered residents; meal service "
            "and hydration. Strict service-animal-only policy."
        ),
    },
    {
        "id": "mag.hrn.mock.0009",
        "name": "Chandler Sunset Library",
        "address": "4930 W Ray Rd",
        "city": "Chandler",
        "postal_code": "85226",
        "lat": 33.3199,
        "lon": -111.9281,
        "services": ["cooling"],
        "pets_ok": False,
        "hours": {
            "Mon": ["10:00", "20:00"],
            "Tue": ["10:00", "20:00"],
            "Wed": ["10:00", "20:00"],
            "Thu": ["10:00", "20:00"],
            "Fri": ["10:00", "18:00"],
            "Sat": ["10:00", "17:00"],
            "Sun": "closed",
        },
        "operator": "City of Chandler",
        "notes": "Standard library cooling lobby.",
    },
    {
        "id": "mag.hrn.mock.0010",
        "name": "Surprise City Hall",
        "address": "16000 N Civic Center Plaza",
        "city": "Surprise",
        "postal_code": "85374",
        "lat": 33.6315,
        "lon": -112.3344,
        "services": ["cooling", "hydration"],
        "pets_ok": False,
        "hours": {
            "Mon": ["08:00", "17:00"],
            "Tue": ["08:00", "17:00"],
            "Wed": ["08:00", "17:00"],
            "Thu": ["08:00", "17:00"],
            "Fri": ["08:00", "17:00"],
            "Sat": "closed",
            "Sun": "closed",
        },
        "operator": "City of Surprise",
        "notes": "City Hall lobby + Council Chambers as overflow.",
    },
    {
        "id": "mag.hrn.mock.0011",
        "name": "Tempe Salvation Army Corps",
        "address": "40 E University Dr",
        "city": "Tempe",
        "postal_code": "85281",
        "lat": 33.4225,
        "lon": -111.9395,
        "services": ["cooling", "hydration", "donation"],
        "pets_ok": True,
        "hours": {
            "Mon": ["09:00", "17:00"],
            "Tue": ["09:00", "17:00"],
            "Wed": ["09:00", "17:00"],
            "Thu": ["09:00", "17:00"],
            "Fri": ["09:00", "17:00"],
            "Sat": ["09:00", "13:00"],
            "Sun": "closed",
        },
        "operator": "The Salvation Army",
        "notes": (
            "Walk-in cooling + hydration; accepts donations of bottled "
            "water and sunscreen during business hours."
        ),
    },
    {
        "id": "mag.hrn.mock.0012",
        "name": "Goodyear Public Library",
        "address": "14455 W Van Buren St",
        "city": "Goodyear",
        "postal_code": "85338",
        "lat": 33.4499,
        "lon": -112.3673,
        "services": ["cooling", "hydration"],
        "pets_ok": False,
        "hours": {
            "Mon": ["10:00", "20:00"],
            "Tue": ["10:00", "20:00"],
            "Wed": ["10:00", "20:00"],
            "Thu": ["10:00", "20:00"],
            "Fri": ["10:00", "17:00"],
            "Sat": ["10:00", "17:00"],
            "Sun": "closed",
        },
        "operator": "City of Goodyear",
        "notes": "Cooling lobby + bottle-fill stations.",
    },
]


# ---------------------------------------------------------------------------
# Geo + hours helpers
# ---------------------------------------------------------------------------
_EARTH_RADIUS_KM: float = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in kilometers."""
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2.0) ** 2
    )
    return 2.0 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))


_DAY_NAMES: tuple[str, ...] = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def _day_name_for(dt: datetime) -> str:
    return _DAY_NAMES[dt.weekday()]


def _parse_hhmm(s: str) -> time:
    """Parse an ``HH:MM`` string into a ``datetime.time`` (24h)."""
    m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", s)
    if not m:
        raise ValueError(f"Invalid HH:MM time literal: {s!r}")
    hour, minute = int(m.group(1)), int(m.group(2))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Out-of-range HH:MM time literal: {s!r}")
    return time(hour=hour, minute=minute)


def hours_for_day(
    hours: dict[str, list[str] | str], day_name: str
) -> list[str] | None:
    """Return ``[open, close]`` or ``None`` if closed / missing."""
    raw = hours.get(day_name)
    if raw is None or raw == "closed":
        return None
    if isinstance(raw, list) and len(raw) == 2:
        return list(raw)
    return None


def is_open_at(
    hours: dict[str, list[str] | str], when: datetime
) -> bool:
    """Naive open-now check using the local clock-time portion of ``when``.

    The HRN dataset doesn't carry timezones per row, so we assume the
    caller has already shifted ``when`` into Arizona local time (Phoenix
    does not observe DST). This is plenty for surfacing "currently open"
    in the mock, and a real backend would do the proper TZ math.
    """
    window = hours_for_day(hours, _day_name_for(when))
    if window is None:
        return False
    open_t = _parse_hhmm(window[0])
    close_t = _parse_hhmm(window[1])
    now_t = when.time().replace(microsecond=0)
    if close_t > open_t:
        return open_t <= now_t < close_t
    # Wraps past midnight (rare for HRN but documented).
    return now_t >= open_t or now_t < close_t


def in_operating_season(when: datetime) -> bool:
    """Is ``when`` inside the HRN operating season (May 1 - Sep 30 inclusive)?"""
    sm, sd = SEASON_START_MONTH_DAY
    em, ed = SEASON_END_MONTH_DAY
    start = (sm, sd)
    end = (em, ed)
    here = (when.month, when.day)
    return start <= here <= end


def _now_local_phoenix(now_iso: str | None = None) -> datetime:
    """Pick a local-time datetime to use for open-now checks.

    Phoenix doesn't observe DST, so MST is fine year-round.
    If ``now_iso`` is provided, it's parsed and stripped of tzinfo.
    """
    if now_iso:
        # Strip Z, accept naive or aware.
        s = now_iso.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is not None:
            # Convert to MST (UTC-7) before stripping.
            from datetime import timedelta

            mst = timezone(offset=-1 * timedelta(hours=7))
            dt = dt.astimezone(mst).replace(tzinfo=None)
        return dt
    # `datetime.utcnow()` is deprecated in 3.12; compute MST explicitly.
    from datetime import timedelta

    return datetime.now(timezone.utc).astimezone(
        timezone(offset=-1 * timedelta(hours=7))
    ).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Mock backend
# ---------------------------------------------------------------------------
@dataclass
class _MockBackend:
    """In-memory store backed by ``MOCK_CENTERS``.

    The list is cloned (deep-ish) on first access so callers can mutate
    rows in tests without leaking state across tests in the same process.
    """

    _centers: list[dict[str, Any]] = field(
        default_factory=lambda: [dict(c) for c in MOCK_CENTERS]
    )

    def all_centers(self) -> list[dict[str, Any]]:
        return [dict(c) for c in self._centers]

    def by_id(self, center_id: str) -> dict[str, Any] | None:
        for c in self._centers:
            if c["id"] == center_id:
                return dict(c)
        return None


# ---------------------------------------------------------------------------
# ArcGIS backend (live mode)
# ---------------------------------------------------------------------------
@dataclass
class _ArcGISBackend:
    """Thin async wrapper around the MAG HRN ArcGIS service.

    See module docstring for the URL discussion. The service is assumed
    to expose at least one layer of point features with attributes
    covering name, address, city, ZIP, service type(s), pet-friendliness,
    and hours-of-operation. Real-world MAG feeds vary in their exact
    attribute names year-on-year; the mapping below is best-effort and
    leans on a small alias map. Override
    ``MAG_HRN_FEATURE_SERVICE_URL`` and ``MAG_HRN_FEATURE_LAYER`` to
    point at the active service.
    """

    service_url: str
    layer: str = DEFAULT_FEATURE_LAYER
    token: str | None = DEFAULT_API_TOKEN
    timeout: float = 30.0

    def __post_init__(self) -> None:
        self._http: httpx.AsyncClient = httpx.AsyncClient(timeout=self.timeout)
        self._cache: list[dict[str, Any]] | None = None

    async def aclose(self) -> None:
        await self._http.aclose()

    async def all_centers(self) -> list[dict[str, Any]]:
        if self._cache is not None:
            return [dict(c) for c in self._cache]
        layers: list[str] = (
            await self._list_layer_ids()
            if str(self.layer).lower() == "all"
            else [str(self.layer)]
        )
        merged: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for lid in layers:
            for f in await self._query_layer(lid):
                rec = _arcgis_feature_to_center(f)
                if rec is None:
                    continue
                if rec["id"] in seen_ids:
                    continue
                seen_ids.add(rec["id"])
                merged.append(rec)
        self._cache = merged
        return [dict(c) for c in merged]

    async def by_id(self, center_id: str) -> dict[str, Any] | None:
        for c in await self.all_centers():
            if c["id"] == center_id:
                return dict(c)
        return None

    # ----------------------------------------------------------- helpers
    async def _list_layer_ids(self) -> list[str]:
        url = self.service_url.rstrip("/")
        params: dict[str, Any] = {"f": "json"}
        if self.token:
            params["token"] = self.token
        resp = await self._http.get(url, params=params)
        resp.raise_for_status()
        body = resp.json() or {}
        layers = body.get("layers") or []
        return [str(L.get("id")) for L in layers if "id" in L]

    async def _query_layer(self, layer_id: str) -> list[dict[str, Any]]:
        url = f"{self.service_url.rstrip('/')}/{layer_id}/query"
        params: dict[str, Any] = {
            "where": "1=1",
            "outFields": "*",
            "outSR": "4326",
            "f": "json",
        }
        if self.token:
            params["token"] = self.token
        resp = await self._http.get(url, params=params)
        resp.raise_for_status()
        body = resp.json() or {}
        return list(body.get("features") or [])


# ---------------------------------------------------------------------------
# ArcGIS attribute -> canonical center mapping
# ---------------------------------------------------------------------------
# Real MAG HRN feature-service attribute names have drifted across
# seasons (e.g. ``LocationType``, ``Type``, ``CenterType``;
# ``HoursofOperation``, ``Hours``; ``Pets``, ``PetFriendly``,
# ``Allows_Pets``). Alias maps make this tolerant of those shifts.
_NAME_FIELDS = ("Name", "name", "FACILITY", "facility", "SiteName", "Site")
_ADDR_FIELDS = ("Address", "address", "ADDRESS1", "addr", "Street")
_CITY_FIELDS = ("City", "city", "CITY")
_ZIP_FIELDS = ("Zip", "ZIP", "PostalCode", "postal_code")
_TYPE_FIELDS = ("LocationType", "Type", "CenterType", "Category", "type")
_HOURS_FIELDS = ("Hours", "HoursofOperation", "OperatingHours", "hours")
_PETS_FIELDS = ("Pets", "PetFriendly", "Allows_Pets", "pets_ok", "pets")
_NOTES_FIELDS = ("Notes", "Description", "Comments", "notes")
_OPER_FIELDS = ("Operator", "Sponsor", "Organization", "Org", "operator")


def _first(attrs: dict[str, Any], names: Iterable[str]) -> Any:
    for n in names:
        if n in attrs and attrs[n] not in (None, ""):
            return attrs[n]
    return None


def _arcgis_feature_to_center(feature: dict[str, Any]) -> dict[str, Any] | None:
    """Coerce a raw ArcGIS feature into the canonical center dict.

    Returns ``None`` if the feature is missing essential fields
    (geometry + name); the caller skips those rather than blowing up
    on a partial row.
    """
    attrs = feature.get("attributes") or {}
    geom = feature.get("geometry") or {}
    lat = geom.get("y") if isinstance(geom.get("y"), (int, float)) else None
    lon = geom.get("x") if isinstance(geom.get("x"), (int, float)) else None
    name = _first(attrs, _NAME_FIELDS)
    if lat is None or lon is None or not name:
        return None
    type_raw = _first(attrs, _TYPE_FIELDS) or ""
    services = _normalize_services(type_raw)
    pets_raw = _first(attrs, _PETS_FIELDS)
    pets_ok = _normalize_bool(pets_raw)
    oid = (
        attrs.get("OBJECTID")
        or attrs.get("ObjectId")
        or attrs.get("FID")
        or _slug_id(name)
    )
    return {
        "id": f"mag.hrn.{oid}",
        "name": str(name),
        "address": str(_first(attrs, _ADDR_FIELDS) or ""),
        "city": str(_first(attrs, _CITY_FIELDS) or ""),
        "postal_code": str(_first(attrs, _ZIP_FIELDS) or ""),
        "lat": float(lat),
        "lon": float(lon),
        "services": services,
        "pets_ok": pets_ok,
        # Hours: ArcGIS often serializes a single human-readable string
        # (e.g. "Mon-Fri 9-5"). We pass it through under a "raw" key
        # and leave the structured per-day hours empty -- the LLM can
        # decide what to do with the raw text. A future improvement is
        # a parser, but it's brittle.
        "hours": {},
        "hours_raw": str(_first(attrs, _HOURS_FIELDS) or ""),
        "operator": str(_first(attrs, _OPER_FIELDS) or ""),
        "notes": str(_first(attrs, _NOTES_FIELDS) or ""),
    }


def _normalize_services(raw: Any) -> list[str]:
    """Map a freeform type string onto our 4-value vocabulary."""
    text = str(raw or "").lower()
    out: list[str] = []
    if "cool" in text:
        out.append("cooling")
    if "hydrat" in text or "water" in text:
        out.append("hydration")
    if "respite" in text:
        out.append("respite")
    if "donat" in text or "drop" in text:
        out.append("donation")
    # Sensible default for the most common bare label.
    if not out and "center" in text:
        out.append("cooling")
    return out


def _normalize_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in ("y", "yes", "true", "1", "ok"):
        return True
    if s in ("n", "no", "false", "0"):
        return False
    return None


def _slug_id(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:40]


# ---------------------------------------------------------------------------
# Facade
# ---------------------------------------------------------------------------
class MAGHRNClient:
    """Mock-by-default Heat Relief Network client.

    When ``MAG_HRN_FEATURE_SERVICE_URL`` is set (or ``feature_service_url``
    is passed explicitly), the client switches to the ArcGIS backend and
    every search hits the live service. Otherwise the canned ``MOCK_CENTERS``
    list is the source of truth.
    """

    def __init__(
        self,
        feature_service_url: str | None = None,
        feature_layer: str = DEFAULT_FEATURE_LAYER,
        api_token: str | None = None,
    ) -> None:
        url = (
            feature_service_url
            if feature_service_url is not None
            else DEFAULT_FEATURE_SERVICE_URL
        )
        token = api_token if api_token is not None else DEFAULT_API_TOKEN
        if url:
            self._backend: _MockBackend | _ArcGISBackend = _ArcGISBackend(
                service_url=url, layer=feature_layer, token=token
            )
            self.mode = "feed"
        else:
            self._backend = _MockBackend()
            self.mode = "mock"

    async def aclose(self) -> None:
        if isinstance(self._backend, _ArcGISBackend):
            await self._backend.aclose()

    # ------------------------------------------------------------ data
    async def _all(self) -> list[dict[str, Any]]:
        if isinstance(self._backend, _ArcGISBackend):
            return await self._backend.all_centers()
        return self._backend.all_centers()

    async def _by_id(self, center_id: str) -> dict[str, Any] | None:
        if isinstance(self._backend, _ArcGISBackend):
            return await self._backend.by_id(center_id)
        return self._backend.by_id(center_id)

    # ------------------------------------------------------------ search
    async def search_centers(
        self,
        lat: float,
        lon: float,
        radius_km: float = 5.0,
        open_now: bool = True,
        pets_ok: bool | None = None,
        services: list[str] | None = None,
        limit: int = 50,
        now_iso: str | None = None,
    ) -> dict[str, Any]:
        """Geo + filter search returning the canonical row shape.

        Off-season the dataset is empty regardless of filters -- the HRN
        only operates May 1 -- September 30.
        """
        when = _now_local_phoenix(now_iso)
        if not in_operating_season(when):
            return {
                "mode": self.mode,
                "as_of": when.isoformat(timespec="seconds"),
                "off_season": True,
                "centers": [],
                "season_window": "May 1 - September 30 (inclusive)",
            }

        wanted_services = (
            {s.lower() for s in services} if services else None
        )
        rows: list[dict[str, Any]] = []
        for c in await self._all():
            dist_km = haversine_km(lat, lon, c["lat"], c["lon"])
            if dist_km > radius_km:
                continue
            if wanted_services is not None and not (
                set(c.get("services") or []) & wanted_services
            ):
                continue
            if pets_ok is not None and bool(c.get("pets_ok")) != pets_ok:
                continue
            if open_now and not _is_open_compat(c, when):
                continue
            rows.append(_row_summary(c, dist_km, when))
        rows.sort(key=lambda r: r["distance_km"])
        return {
            "mode": self.mode,
            "as_of": when.isoformat(timespec="seconds"),
            "query": {
                "lat": lat,
                "lon": lon,
                "radius_km": radius_km,
                "open_now": open_now,
                "pets_ok": pets_ok,
                "services": services,
            },
            "total": len(rows),
            "centers": rows[: max(0, int(limit))],
        }

    async def center_detail(self, center_id: str) -> dict[str, Any]:
        rec = await self._by_id(center_id)
        if rec is None:
            return {"id": center_id, "found": False, "mode": self.mode}
        return {
            "id": rec["id"],
            "found": True,
            "mode": self.mode,
            "name": rec.get("name"),
            "address": rec.get("address"),
            "city": rec.get("city"),
            "postal_code": rec.get("postal_code"),
            "lat": rec.get("lat"),
            "lon": rec.get("lon"),
            "services": rec.get("services") or [],
            "pets_ok": rec.get("pets_ok"),
            "operator": rec.get("operator"),
            "notes": rec.get("notes"),
            "hours": rec.get("hours") or {},
            "hours_raw": rec.get("hours_raw") or "",
            "kg_node_id": None,
        }

    async def list_open_now(self, now_iso: str | None = None) -> dict[str, Any]:
        when = _now_local_phoenix(now_iso)
        if not in_operating_season(when):
            return {
                "mode": self.mode,
                "as_of": when.isoformat(timespec="seconds"),
                "off_season": True,
                "centers": [],
                "season_window": "May 1 - September 30 (inclusive)",
            }
        rows: list[dict[str, Any]] = []
        for c in await self._all():
            if _is_open_compat(c, when):
                rows.append(_row_summary(c, None, when))
        rows.sort(key=lambda r: (r["city"] or "", r["name"] or ""))
        return {
            "mode": self.mode,
            "as_of": when.isoformat(timespec="seconds"),
            "total": len(rows),
            "centers": rows,
        }

    async def search_by_text(
        self,
        query: str,
        near: tuple[float, float] | None = None,
        limit: int = 50,
        now_iso: str | None = None,
    ) -> dict[str, Any]:
        when = _now_local_phoenix(now_iso)
        if not in_operating_season(when):
            return {
                "mode": self.mode,
                "as_of": when.isoformat(timespec="seconds"),
                "off_season": True,
                "centers": [],
                "season_window": "May 1 - September 30 (inclusive)",
            }
        tokens = [t for t in re.split(r"\s+", (query or "").strip().lower()) if t]
        rows: list[dict[str, Any]] = []
        for c in await self._all():
            hay = " ".join(
                str(c.get(k, "") or "")
                for k in ("name", "address", "city", "postal_code", "operator", "notes")
            ).lower()
            services_str = " ".join(c.get("services") or [])
            hay = f"{hay} {services_str}".lower()
            if tokens and not all(t in hay for t in tokens):
                continue
            dist_km = (
                haversine_km(near[0], near[1], c["lat"], c["lon"])
                if near
                else None
            )
            rows.append(_row_summary(c, dist_km, when))
        if near is not None:
            rows.sort(key=lambda r: (r.get("distance_km") or float("inf")))
        else:
            rows.sort(key=lambda r: (r["city"] or "", r["name"] or ""))
        return {
            "mode": self.mode,
            "as_of": when.isoformat(timespec="seconds"),
            "query": query,
            "near": list(near) if near else None,
            "total": len(rows),
            "centers": rows[: max(0, int(limit))],
        }

    # --------------------------------------------------- supply (MOCK)
    async def supply_status(self, center_id: str) -> dict[str, Any]:
        """Mock supply / occupancy heads-up.

        **This is mock data.** MAG does not publish a real-time supply
        feed today; closing this gap is Heat-Q2 in
        ``plan/01-parameter-mapping.html``. The shape is the contract:
        callers can depend on the keys regardless of which backend
        ships first.
        """
        rec = await self._by_id(center_id)
        when = _now_local_phoenix()
        if rec is None:
            return {
                "center_id": center_id,
                "found": False,
                "water_status": None,
                "seats_available": None,
                "last_updated_iso": when.isoformat(timespec="seconds"),
                "source": "mock",
                "note": (
                    "Center ID not found. The supply-status feed is mock "
                    "until MAG publishes a real one (plan/01 Heat-Q2)."
                ),
            }
        # Deterministic mock: hash-bucket the id so reps see stable
        # values across calls in the same session.
        h = abs(hash(rec["id"])) % 30
        water = ("ok", "ok", "ok", "low", "out")[h % 5]
        seats = None if "respite" in (rec.get("services") or []) else h
        return {
            "center_id": rec["id"],
            "found": True,
            "name": rec.get("name"),
            "water_status": water,
            "seats_available": seats,
            "last_updated_iso": when.isoformat(timespec="seconds"),
            "source": "mock",
            "note": (
                "MOCK feed. MAG does not yet publish a real-time supply "
                "feed; see plan/01-parameter-mapping.html Heat-Q2."
            ),
        }


# ---------------------------------------------------------------------------
# Row-shaping helpers (private)
# ---------------------------------------------------------------------------
def _is_open_compat(center: dict[str, Any], when: datetime) -> bool:
    """Handle both structured (mock) and raw-string (live) hours."""
    hours = center.get("hours") or {}
    if hours:
        try:
            return is_open_at(hours, when)
        except Exception:
            return False
    raw = (center.get("hours_raw") or "").strip()
    if not raw:
        # No info -> conservatively say not open. Callers can drop the
        # open_now filter to surface unknown-hours rows.
        return False
    # Best-effort: many ArcGIS rows say "Open daily" or "24/7".
    low = raw.lower()
    if "24" in low and "7" in low:
        return True
    if "always" in low or "daily" in low and "closed" not in low:
        return True
    return False


def _hours_today_summary(
    center: dict[str, Any], when: datetime
) -> str:
    """Compact 'open 10:00-20:00' / 'closed' / raw fallback per day."""
    hours = center.get("hours") or {}
    if hours:
        window = hours_for_day(hours, _day_name_for(when))
        if window is None:
            return "closed"
        return f"{window[0]}-{window[1]}"
    raw = (center.get("hours_raw") or "").strip()
    return raw or "unknown"


def _row_summary(
    center: dict[str, Any],
    distance_km: float | None,
    when: datetime,
) -> dict[str, Any]:
    return {
        "id": center["id"],
        "name": center.get("name"),
        "address": center.get("address"),
        "city": center.get("city"),
        "postal_code": center.get("postal_code"),
        "lat": center.get("lat"),
        "lon": center.get("lon"),
        "services": list(center.get("services") or []),
        "hours_today": _hours_today_summary(center, when),
        "pets_ok": center.get("pets_ok"),
        "distance_km": (
            round(distance_km, 3) if isinstance(distance_km, (int, float)) else None
        ),
        # Reserved for the knowledge-graph integration. Populated by the
        # downstream KG MCP when a center has been edged into the graph;
        # the client itself never has to know that ID.
        "kg_node_id": None,
    }
