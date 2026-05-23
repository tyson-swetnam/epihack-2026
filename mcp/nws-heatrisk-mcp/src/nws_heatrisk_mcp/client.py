"""HTTP client for the U.S. National Weather Service public API and
the WPC HeatRisk gridded product.

NWS API conventions (from
https://www.weather.gov/documentation/services-web-api):

* **No auth token.** The API is open. It *does* require a
  ``User-Agent`` header that identifies the application and gives a
  contact (email or URL). Requests without one are rejected. We refuse
  to start without ``NWS_USER_AGENT`` set, with a clear error.
* **Content type.** The default is ``application/geo+json``; many
  endpoints also offer ``application/ld+json``. We accept the default
  and parse with stdlib json.
* **Gridpoints.** A coordinate is resolved via
  ``GET /points/{lat},{lon}``, which returns the relevant
  ``forecast``, ``forecastHourly``, ``forecastGridData``, and
  ``observationStations`` URLs as absolute strings; the client
  follows those rather than constructing them.
* **Alerts.** ``GET /alerts/active`` accepts ``area`` (state, e.g.
  ``AZ``), ``zone`` (e.g. ``AZZ540``), ``event`` (e.g.
  ``Excessive Heat Warning``), and other filters.
* **Rate-limit/load.** NWS returns 503 under load. We retry 5xx
  responses with a short exponential backoff (3 tries).

HeatRisk:

* The Weather Prediction Center publishes the experimental HeatRisk
  gridded product at https://www.wpc.ncep.noaa.gov/heatrisk/. The
  machine-readable feed URL has moved more than once; the default
  here is the best-known location at build time and is overridable
  via ``NWS_HEATRISK_URL``. If the upstream returns a non-JSON 404
  page, you'll need to update the env var.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx

DEFAULT_BASE_URL = os.environ.get("NWS_BASE_URL", "https://api.weather.gov")

# HeatRisk feed: experimental, drifts. Documented landing:
#   https://www.wpc.ncep.noaa.gov/heatrisk/
# The exact machine-readable URL is uncertain enough that we make it
# env-overridable and tag it in the docstring above so future
# maintainers can patch without a code release.
DEFAULT_HEATRISK_URL = os.environ.get(
    "NWS_HEATRISK_URL",
    "https://www.wpc.ncep.noaa.gov/heatrisk/data/heatrisk.json",
)

# api.weather.gov paths. Every path is env-overridable so the deployed
# server can be corrected without a code release if NWS reorganizes.
PATHS = {
    "points":              os.environ.get("NWS_PATH_POINTS",              "/points/{lat},{lon}"),
    "alerts_active":       os.environ.get("NWS_PATH_ALERTS_ACTIVE",       "/alerts/active"),
    "stations_for_point":  os.environ.get("NWS_PATH_STATIONS_FOR_POINT",  "/points/{lat},{lon}/stations"),
    "station_latest_obs":  os.environ.get("NWS_PATH_STATION_OBSERVATIONS", "/stations/{station_id}/observations/latest"),
    "zone":                os.environ.get("NWS_PATH_ZONE",                "/zones/{zone_type}/{zone_id}"),
}

# NWS heat-event names we care about for `nws_active_heat_alerts`.
# The "Extreme Heat" series replaced the older "Excessive Heat" labels
# as NWS rolled out the new heat-impact wording in 2024-2025; we accept
# both so the server keeps working through any phased rollout.
HEAT_EVENTS = (
    "Excessive Heat Warning",
    "Excessive Heat Watch",
    "Heat Advisory",
    "Extreme Heat Warning",
    "Extreme Heat Watch",
)


class NWSConfigError(RuntimeError):
    """Raised when required env config is missing (e.g. NWS_USER_AGENT)."""


class NWSClient:
    """Thin async client for api.weather.gov + the WPC HeatRisk feed.

    The NWS API requires a descriptive User-Agent. We refuse to
    construct the client without one to surface the requirement as
    early as possible.
    """

    def __init__(
        self,
        user_agent: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        heatrisk_url: str = DEFAULT_HEATRISK_URL,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        ua = user_agent or os.environ.get("NWS_USER_AGENT")
        if not ua:
            raise NWSConfigError(
                "NWS_USER_AGENT must be set. The api.weather.gov public API "
                "requires a descriptive User-Agent header identifying the "
                "application and a contact, e.g.:\n"
                '    NWS_USER_AGENT="epihack-az-2026-sentinel (you@example.org)"'
            )
        self.user_agent = ua
        self.base_url = base_url.rstrip("/")
        self.heatrisk_url = heatrisk_url
        self.max_retries = max(1, int(max_retries))
        self._http = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "User-Agent": ua,
                "Accept": "application/geo+json,application/json;q=0.9,*/*;q=0.5",
            },
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    # ------------------------------------------------------------- http
    async def _get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """GET with gentle exponential backoff on 5xx.

        ``url`` may be absolute (e.g. an NWS-returned ``forecast`` URL)
        or a path relative to ``base_url``.
        """
        if not url.startswith("http"):
            url = f"{self.base_url}{url}"
        delay = 0.5
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                resp = await self._http.get(url, params=params or {})
            except httpx.HTTPError as e:
                last_exc = e
                await asyncio.sleep(delay)
                delay *= 2
                continue
            if 500 <= resp.status_code < 600 and attempt < self.max_retries - 1:
                await asyncio.sleep(delay)
                delay *= 2
                continue
            resp.raise_for_status()
            # api.weather.gov returns application/geo+json; httpx's
            # json() handles any application/*+json content-type.
            return resp.json()
        if last_exc:
            raise last_exc
        raise RuntimeError(f"NWS GET {url} failed after {self.max_retries} attempts")

    # ----------------------------------------------------------- points
    async def get_point(self, lat: float, lon: float) -> Any:
        """Resolve a coordinate to its NWS gridpoint metadata.

        Returns the parsed GeoJSON Feature; ``properties`` contains
        absolute URLs for ``forecast``, ``forecastHourly``,
        ``forecastGridData``, ``observationStations``, and the
        county / fire / forecast zones.
        """
        path = PATHS["points"].format(lat=lat, lon=lon)
        return await self._get(path)

    # -------------------------------------------------------- forecast
    async def get_forecast(self, lat: float, lon: float, hourly: bool = False) -> Any:
        """Return the textual forecast for a point.

        Hits ``/points/{lat},{lon}`` then follows the ``forecast`` or
        ``forecastHourly`` URL it returns.
        """
        point = await self.get_point(lat, lon)
        props = point.get("properties") or {}
        url = props.get("forecastHourly" if hourly else "forecast")
        if not url:
            raise RuntimeError(
                f"NWS /points/{lat},{lon} did not return a forecast URL: {props!r}"
            )
        return await self._get(url)

    # ----------------------------------------------------- observations
    async def get_nearest_station(self, lat: float, lon: float) -> str | None:
        """Return the station ID of the nearest observation station."""
        path = PATHS["stations_for_point"].format(lat=lat, lon=lon)
        data = await self._get(path)
        features = data.get("features") or []
        if not features:
            return None
        # NWS returns them roughly in distance order from the point.
        first = features[0]
        props = first.get("properties") or {}
        return props.get("stationIdentifier") or first.get("id")

    async def get_latest_observation(self, station_id: str) -> Any:
        """Latest observation for a station (temperature, dew point, RH, wind)."""
        path = PATHS["station_latest_obs"].format(station_id=station_id)
        return await self._get(path)

    # ---------------------------------------------------------- alerts
    async def get_active_alerts(
        self,
        area: str | None = None,
        zone: str | None = None,
        event: str | None = None,
    ) -> Any:
        """Active alerts. ``area`` is a 2-letter state, ``zone`` is e.g. ``AZZ540``.

        ``event`` is an exact NWS event name (e.g. ``Excessive Heat Warning``).
        For "any heat event" filtering, prefer the server-side wrapper
        ``nws_active_heat_alerts`` which loops over the known names.
        """
        params: dict[str, Any] = {}
        if area:
            params["area"] = area
        if zone:
            params["zone"] = zone
        if event:
            params["event"] = event
        return await self._get(PATHS["alerts_active"], params=params)

    # ------------------------------------------------------- HeatRisk
    async def get_heatrisk_feed(self) -> Any | None:
        """Fetch the WPC HeatRisk gridded product (experimental).

        The default URL is best-known at build time but the WPC has
        moved this feed before; override with ``NWS_HEATRISK_URL`` if
        you get a 404 or non-JSON response.

        HeatRisk's machine-readable hosting has drifted repeatedly and
        the historic default 404s in production (verified 2026-05-21).
        Rather than let a transport error or 4xx propagate and surface
        as a tool crash, we swallow ``httpx`` errors here and return
        ``None``. The downstream parser (``heatrisk.extract_daily``)
        and the ``nws_heatrisk`` / ``nws_heatrisk_week`` tools already
        treat ``None`` / empty as "no data" and emit a graceful
        Unknown-category payload with a drift note. This keeps the
        server usable (all other NWS tools work) even while the feed
        URL is unresolved.
        """
        try:
            return await self._get(self.heatrisk_url)
        except httpx.HTTPError:
            return None
