"""Client for the 211 Arizona MCP server.

Mock-by-default. 211 Arizona (Solari Crisis & Human Services) does not
ship a public REST API, so this module's :class:`Az211Client` defaults
to the in-memory :class:`MockBackend` defined here. The ``call``
contract mirrors what we expect a future HTTP backend to expose
(method + path + JSON body), so when a real API ships, only the
:class:`HttpBackend` swap-in needs to learn the wire format.

Dispatch state for ``az211_transport_to_cooling_center`` lives in a
process-local dict on the mock backend, keyed by ``dispatch_id``. Two
tool calls in the same LLM session share the same backend instance and
therefore see the same dispatch state — this is what makes Scenario C
in ``plan/04-data-flows.md`` chain naturally.
"""

from __future__ import annotations

import math
import os
import secrets
from typing import Any

import httpx

from .mock_data import (
    COOLING_CENTERS,
    CRISIS_REFERRALS,
    LANGUAGES_SUPPORTED,
    OPERATOR_HOURS,
    UTILITY_PROVIDERS,
    county_for_zip,
)


SOURCE_MOCK = "mock"
SOURCE_HTTP = "211-arizona-api"


# ---------------------------------------------------------------------------
# Mock backend
# ---------------------------------------------------------------------------
class MockBackend:
    """In-memory mock of the (hypothetical) 211 Arizona backend.

    Holds a process-local ``dispatches`` dict so chained calls in one
    LLM session return consistent state (e.g. retrieve a dispatch that
    was created by an earlier tool call).
    """

    def __init__(self) -> None:
        self.dispatches: dict[str, dict[str, Any]] = {}

    # --- transport ------------------------------------------------------
    def create_transport(
        self,
        postal_code: str,
        urgency: str,
        needs_wheelchair: bool,
        has_pet: bool,
    ) -> dict[str, Any]:
        county = county_for_zip(postal_code)
        eta = _eta_for_urgency(urgency)
        dispatch_id = secrets.token_hex(6)
        record = {
            "dispatch_id": dispatch_id,
            "postal_code": postal_code,
            "county": county,
            "urgency": urgency,
            "eta_minutes": eta,
            "provider": _provider_for_county(county),
            "callback_phone": "1-877-211-8661",
            "needs_wheelchair": needs_wheelchair,
            "has_pet": has_pet,
            "status": "dispatched",
            "source": SOURCE_MOCK,
        }
        self.dispatches[dispatch_id] = record
        return record

    def get_dispatch(self, dispatch_id: str) -> dict[str, Any] | None:
        return self.dispatches.get(dispatch_id)

    # --- utility assistance --------------------------------------------
    def list_utility_assistance(
        self, postal_code: str, kind: str
    ) -> list[dict[str, Any]]:
        county = county_for_zip(postal_code)
        # Same-county providers come first; if a county returns nothing,
        # fall through to the full list so the demo never empties.
        same = [p for p in UTILITY_PROVIDERS if p["county"] == county]
        other = [p for p in UTILITY_PROVIDERS if p["county"] != county]
        ordered = same + other
        if kind != "any":
            ordered = [p for p in ordered if kind in p["services"]]
        # Re-stamp source on each row for traceability.
        return [{**p, "source": SOURCE_MOCK} for p in ordered]

    # --- crisis referrals ----------------------------------------------
    def list_crisis_referrals(
        self, postal_code: str, topic: str
    ) -> list[dict[str, Any]]:
        # Postal code is a soft filter today (the mock data set is
        # statewide / topic-keyed), but accepted so the contract
        # matches a future location-aware backend.
        if topic == "all":
            rows: list[dict[str, Any]] = []
            for t, entries in CRISIS_REFERRALS.items():
                for r in entries:
                    rows.append({**r, "topic": t, "source": SOURCE_MOCK})
            return rows
        entries = CRISIS_REFERRALS.get(topic, [])
        return [{**r, "topic": topic, "source": SOURCE_MOCK} for r in entries]

    # --- cooling-center referral (canned passthrough) ------------------
    def nearby_cooling_centers(
        self, lat: float, lon: float, urgency: str
    ) -> list[dict[str, Any]]:
        scored = []
        for c in COOLING_CENTERS:
            d_km = _haversine_km(lat, lon, c["lat"], c["lon"])
            scored.append({**c, "distance_km": round(d_km, 2)})
        scored.sort(key=lambda r: r["distance_km"])
        # Urgency tightens the radius slightly so a "high" / "emergency"
        # request can't return a center 200 km away.
        radius = {"emergency": 10.0, "high": 25.0, "standard": 80.0}.get(urgency, 80.0)
        scored = [r for r in scored if r["distance_km"] <= radius] or scored[:1]
        return [{**r, "source": SOURCE_MOCK} for r in scored]

    # --- directory of phone lines --------------------------------------
    def operator_directory(self) -> dict[str, Any]:
        return {**OPERATOR_HOURS, "source": SOURCE_MOCK}


# ---------------------------------------------------------------------------
# HTTP backend (skeleton; activated by AZ211_BACKEND_URL).
# ---------------------------------------------------------------------------
class HttpBackend:
    """Skeleton HTTP backend for when a real 211 Arizona API exists.

    Every method is a 1:1 substitute for :class:`MockBackend`. Wire
    formats are TBD; today they raise :class:`NotImplementedError` so
    a misconfiguration is loud rather than silent.
    """

    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._http = httpx.AsyncClient(timeout=15.0)

    async def aclose(self) -> None:
        await self._http.aclose()

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    def create_transport(self, *a: Any, **k: Any) -> dict[str, Any]:
        raise NotImplementedError(
            "211 Arizona HTTP backend wire format is TBD; unset "
            "AZ211_BACKEND_URL to fall back to the mock backend."
        )

    def get_dispatch(self, *a: Any, **k: Any) -> dict[str, Any] | None:
        raise NotImplementedError

    def list_utility_assistance(self, *a: Any, **k: Any) -> list[dict[str, Any]]:
        raise NotImplementedError

    def list_crisis_referrals(self, *a: Any, **k: Any) -> list[dict[str, Any]]:
        raise NotImplementedError

    def nearby_cooling_centers(self, *a: Any, **k: Any) -> list[dict[str, Any]]:
        raise NotImplementedError

    def operator_directory(self) -> dict[str, Any]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Public client
# ---------------------------------------------------------------------------
class Az211Client:
    """211 Arizona MCP client. Selects mock vs HTTP backend at construction.

    Set ``AZ211_BACKEND_URL`` (and optionally ``AZ211_API_KEY``) to
    point at a real backend; leave both unset to use the mock.
    """

    def __init__(
        self,
        backend_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        url = backend_url or os.environ.get("AZ211_BACKEND_URL")
        key = api_key or os.environ.get("AZ211_API_KEY")
        if url:
            self.backend: MockBackend | HttpBackend = HttpBackend(url, key)
            self.is_mock = False
        else:
            self.backend = MockBackend()
            self.is_mock = True

    # --- transport ------------------------------------------------------
    def create_transport(
        self,
        postal_code: str,
        urgency: str = "standard",
        needs_wheelchair: bool = False,
        has_pet: bool = False,
    ) -> dict[str, Any]:
        return self.backend.create_transport(
            postal_code=postal_code,
            urgency=urgency,
            needs_wheelchair=needs_wheelchair,
            has_pet=has_pet,
        )

    def get_dispatch(self, dispatch_id: str) -> dict[str, Any] | None:
        return self.backend.get_dispatch(dispatch_id)

    # --- utility assistance --------------------------------------------
    def list_utility_assistance(
        self, postal_code: str, kind: str = "any"
    ) -> list[dict[str, Any]]:
        return self.backend.list_utility_assistance(postal_code, kind)

    # --- crisis referrals ----------------------------------------------
    def list_crisis_referrals(
        self, postal_code: str, topic: str = "all"
    ) -> list[dict[str, Any]]:
        return self.backend.list_crisis_referrals(postal_code, topic)

    # --- cooling-center referral ---------------------------------------
    def nearby_cooling_centers(
        self, lat: float, lon: float, urgency: str = "standard"
    ) -> list[dict[str, Any]]:
        return self.backend.nearby_cooling_centers(lat, lon, urgency)

    # --- directory of phone lines --------------------------------------
    def operator_directory(self) -> dict[str, Any]:
        return self.backend.operator_directory()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _eta_for_urgency(urgency: str) -> int:
    return {"emergency": 8, "high": 18, "standard": 45}.get(urgency, 45)


def _provider_for_county(county: str) -> str:
    return {
        "Maricopa": "Valley Metro / 211 Arizona heat-relief rideshare",
        "Pima": "Sun Tran on-demand / 211 Arizona heat-relief rideshare",
        "Yuma": "YCAT on-demand / 211 Arizona heat-relief rideshare",
        "Coconino": "Mountain Line on-demand / 211 Arizona heat-relief rideshare",
        "Navajo": "NACOG community transport / 211 Arizona heat-relief rideshare",
    }.get(county, "211 Arizona heat-relief rideshare")


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


__all__ = [
    "Az211Client",
    "HttpBackend",
    "MockBackend",
    "SOURCE_HTTP",
    "SOURCE_MOCK",
]
