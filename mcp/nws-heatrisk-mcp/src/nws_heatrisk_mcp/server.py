"""FastMCP server exposing the NWS public API + WPC HeatRisk product.

Designed for EpiHack Arizona 2026's heat-health focus group. An LLM
client (Claude Desktop, Claude Code, ...) can answer questions like:

    "What's the HeatRisk category and active heat warnings for the
    block I'm standing on right now?"

by calling:

  1. nws_heatrisk(lat, lon, today)           -> Magenta / Extreme
  2. nws_alert_zones_for_point(lat, lon)     -> ['AZZ540', 'AZC013']
  3. nws_active_heat_alerts('AZ', 'AZZ540')  -> any open warnings
  4. nws_current_conditions(lat, lon)        -> T / RH / wind for context
  5. nws_heat_index(T, RH)                   -> apparent temperature

The server also exposes textual MCP resources documenting the
HeatRisk colour bands and the API base URL / User-Agent in use.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from . import heatrisk as hr
from .client import DEFAULT_BASE_URL, HEAT_EVENTS, NWSClient
from .heat_index import heat_index_category, heat_index_f


mcp = FastMCP(
    "nws-heatrisk",
    instructions=(
        "Programmatic access to the U.S. National Weather Service public "
        "API (api.weather.gov: gridpoint forecasts, station observations, "
        "active alerts) and the WPC HeatRisk daily gridded product. "
        "Designed for heat-health work: start with `nws_heatrisk` for a "
        "point's daily risk category, `nws_active_heat_alerts` for any "
        "open watch/warning, and `nws_current_conditions` + "
        "`nws_heat_index` for live apparent temperature. The NWS API "
        "requires a descriptive User-Agent; set `NWS_USER_AGENT` in env."
    ),
)


_client: NWSClient | None = None


def _get_client() -> NWSClient:
    global _client
    if _client is None:
        _client = NWSClient()
    return _client


# ----------------------------------------------------------------- HeatRisk
@mcp.tool()
async def nws_heatrisk(
    lat: Annotated[float, Field(description="Latitude, decimal degrees.")],
    lon: Annotated[float, Field(description="Longitude, decimal degrees.")],
    date: Annotated[
        str | None,
        Field(description="ISO date 'YYYY-MM-DD'. Defaults to today."),
    ] = None,
) -> dict:
    """Daily NWS HeatRisk for a point.

    Returns the numeric value (0-4), the colour label (Green / Yellow /
    Orange / Red / Magenta), a one-line description, and the source date.

    NOTE: HeatRisk's gridded feed is experimental and currently
    delivered as a CONUS-wide product, not per-point. This tool
    fetches the feed and returns the daily category from the feed;
    a future revision will perform a true point lookup once NWS
    publishes a per-coordinate endpoint.
    """
    client = _get_client()
    feed = await client.get_heatrisk_feed()
    rows = hr.extract_daily(feed)
    target = date or hr.today_iso()
    row = hr.pick_for_date(rows, target)
    if row is None:
        return {
            "lat": lat,
            "lon": lon,
            "date": target,
            "category": hr.category(None),
            "note": (
                "No HeatRisk row found for the requested date. The feed "
                "may have drifted; check NWS_HEATRISK_URL."
            ),
        }
    return {
        "lat": lat,
        "lon": lon,
        "date": row["date"],
        "category": hr.category(row["value"]),
    }


@mcp.tool()
async def nws_heatrisk_week(
    lat: Annotated[float, Field(description="Latitude, decimal degrees.")],
    lon: Annotated[float, Field(description="Longitude, decimal degrees.")],
) -> dict:
    """7-day NWS HeatRisk outlook for a point."""
    client = _get_client()
    feed = await client.get_heatrisk_feed()
    rows = hr.extract_daily(feed)
    rows = sorted(rows, key=lambda r: r["date"])[:7]
    return {
        "lat": lat,
        "lon": lon,
        "days": [
            {"date": r["date"], "category": hr.category(r["value"])} for r in rows
        ],
    }


# ----------------------------------------------------------------- forecast
@mcp.tool()
async def nws_forecast(
    lat: Annotated[float, Field(description="Latitude, decimal degrees.")],
    lon: Annotated[float, Field(description="Longitude, decimal degrees.")],
    period: Annotated[
        Literal["now", "today", "tonight", "week"],
        Field(
            description=(
                "'now' returns the current hourly forecast period; "
                "'today'/'tonight' pick the named period from the daily "
                "forecast; 'week' returns all daily periods."
            )
        ),
    ] = "today",
) -> dict:
    """Textual NWS forecast for a point.

    Wraps ``GET /points/{lat},{lon}`` and follows the returned
    ``forecast`` or ``forecastHourly`` URL.
    """
    client = _get_client()
    hourly = period == "now"
    data = await client.get_forecast(lat, lon, hourly=hourly)
    periods = ((data or {}).get("properties") or {}).get("periods") or []

    if period == "now":
        picked = periods[:1]
    elif period == "today":
        picked = [p for p in periods if str(p.get("name", "")).lower() in {"today", "this afternoon"}] or periods[:1]
    elif period == "tonight":
        picked = [p for p in periods if "night" in str(p.get("name", "")).lower()][:1]
    else:  # "week"
        picked = periods

    return {
        "lat": lat,
        "lon": lon,
        "period": period,
        "periods": picked,
    }


# ------------------------------------------------------------ observations
@mcp.tool()
async def nws_current_conditions(
    lat: Annotated[float, Field(description="Latitude, decimal degrees.")],
    lon: Annotated[float, Field(description="Longitude, decimal degrees.")],
) -> dict:
    """Latest observation from the NWS station nearest the point.

    Returns temperature (C and F), dew point, relative humidity, and
    wind, plus the station identifier and observation timestamp.
    """
    client = _get_client()
    station_id = await client.get_nearest_station(lat, lon)
    if not station_id:
        return {
            "lat": lat,
            "lon": lon,
            "station_id": None,
            "error": "No NWS observation stations found near this point.",
        }
    obs = await client.get_latest_observation(station_id)
    props = (obs or {}).get("properties") or {}
    temp_c = (props.get("temperature") or {}).get("value")
    dew_c = (props.get("dewpoint") or {}).get("value")
    rh = (props.get("relativeHumidity") or {}).get("value")
    wind_kph = (props.get("windSpeed") or {}).get("value")
    wind_dir = (props.get("windDirection") or {}).get("value")
    return {
        "lat": lat,
        "lon": lon,
        "station_id": station_id,
        "observed_at": props.get("timestamp"),
        "temperature_c": temp_c,
        "temperature_f": (temp_c * 9 / 5 + 32) if temp_c is not None else None,
        "dewpoint_c": dew_c,
        "dewpoint_f": (dew_c * 9 / 5 + 32) if dew_c is not None else None,
        "relative_humidity_percent": rh,
        "wind_speed_kph": wind_kph,
        "wind_direction_deg": wind_dir,
        "raw_text": props.get("textDescription"),
    }


# ----------------------------------------------------------------- math
@mcp.tool()
def nws_heat_index(
    temp_f: Annotated[float, Field(description="Dry-bulb temperature, deg F.")],
    rh_percent: Annotated[float, Field(ge=0, le=100, description="Relative humidity, 0-100.")],
) -> dict:
    """NWS apparent-temperature (heat-index) calculation.

    Pure computation, no network. Uses the Rothfusz regression with
    the standard NWS low- and high-humidity adjustments.
    """
    hi = heat_index_f(temp_f, rh_percent)
    return {
        "temp_f": temp_f,
        "rh_percent": rh_percent,
        "heat_index_f": round(hi, 1),
        "category": heat_index_category(hi),
        "formula": "Rothfusz regression with NWS humidity adjustments",
    }


# ----------------------------------------------------------------- alerts
@mcp.tool()
async def nws_active_heat_alerts(
    state: Annotated[
        str,
        Field(description="Two-letter U.S. state postal code, e.g. 'AZ'."),
    ] = "AZ",
    zone: Annotated[
        str | None,
        Field(description="Optional NWS zone ID (e.g. 'AZZ540') to narrow further."),
    ] = None,
) -> dict:
    """Active NWS heat watches / warnings / advisories for a state.

    Filters ``/alerts/active`` to the standard heat event names:
    Excessive Heat Watch/Warning, Extreme Heat Watch/Warning, and
    Heat Advisory.
    """
    client = _get_client()
    # NWS doesn't accept a multi-event filter in one request; do one
    # request per event name and merge.
    all_features: list[Any] = []
    seen_ids: set[str] = set()
    for event in HEAT_EVENTS:
        data = await client.get_active_alerts(area=state, zone=zone, event=event)
        for feat in (data or {}).get("features") or []:
            fid = feat.get("id") or (feat.get("properties") or {}).get("id")
            if fid and fid in seen_ids:
                continue
            if fid:
                seen_ids.add(fid)
            all_features.append(feat)
    return {
        "state": state,
        "zone": zone,
        "count": len(all_features),
        "alerts": [
            {
                "id": (f.get("properties") or {}).get("id") or f.get("id"),
                "event": (f.get("properties") or {}).get("event"),
                "severity": (f.get("properties") or {}).get("severity"),
                "headline": (f.get("properties") or {}).get("headline"),
                "effective": (f.get("properties") or {}).get("effective"),
                "expires": (f.get("properties") or {}).get("expires"),
                "areaDesc": (f.get("properties") or {}).get("areaDesc"),
                "affectedZones": (f.get("properties") or {}).get("affectedZones"),
            }
            for f in all_features
        ],
    }


@mcp.tool()
async def nws_alert_zones_for_point(
    lat: Annotated[float, Field(description="Latitude, decimal degrees.")],
    lon: Annotated[float, Field(description="Longitude, decimal degrees.")],
) -> dict:
    """Return the NWS alert zones (county, fire, forecast) for a point.

    Useful for matching against ``nws_active_heat_alerts`` output: an
    alert applies to a point if any of the alert's ``affectedZones``
    appears in this list.
    """
    client = _get_client()
    point = await client.get_point(lat, lon)
    props = (point or {}).get("properties") or {}
    out: dict[str, list[str] | str | None] = {
        "lat": lat,
        "lon": lon,
        "forecast_zone": props.get("forecastZone"),
        "county_zone": props.get("county"),
        "fire_zone": props.get("fireWeatherZone"),
        "grid_id": props.get("gridId"),
    }
    # Extract just the zone IDs (last path component) for easy matching.
    def _id(url: Any) -> str | None:
        if isinstance(url, str) and "/" in url:
            return url.rstrip("/").rsplit("/", 1)[-1]
        return None
    out["zone_ids"] = [
        z for z in (_id(out["forecast_zone"]), _id(out["county_zone"]), _id(out["fire_zone"])) if z
    ]
    return out


# -------------------------------------------------------- reference resource
@mcp.resource("nws://heatrisk-categories")
def heatrisk_categories() -> str:
    """Reference for the NWS HeatRisk colour bands (HHS heat-health levels)."""
    return hr.reference_text()


@mcp.resource("nws://api-base-url")
def api_base_url() -> str:
    """Current NWS API base URL and User-Agent string in use."""
    # Avoid constructing the client just to read its config; pull
    # straight from the module-level defaults so this resource is
    # always available even if NWS_USER_AGENT is unset (in which case
    # we say so).
    import os

    ua = os.environ.get("NWS_USER_AGENT") or "(not set; server will refuse to start)"
    return (
        f"NWS_BASE_URL    = {DEFAULT_BASE_URL}\n"
        f"NWS_USER_AGENT  = {ua}\n"
        "\n"
        "The api.weather.gov public API requires a descriptive\n"
        "User-Agent identifying the application and a contact.\n"
        "Pattern: '<app-name> (<contact email or URL>)'.\n"
    )
