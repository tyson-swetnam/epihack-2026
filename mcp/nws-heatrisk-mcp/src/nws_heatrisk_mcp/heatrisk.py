"""HeatRisk category mapping + lightweight feed parsing.

NWS HeatRisk is a forecast of the heat-related health risk for the
next 7 days, on a 0-4 integer scale, with each value paired with a
descriptive color (Green / Yellow / Orange / Red / Magenta).

Reference:
    https://www.wpc.ncep.noaa.gov/heatrisk/
    https://www.weather.gov/safety/heat-heatrisk

The exact JSON shape of the experimental machine-readable feed has
drifted; this module handles a few common shapes (list of daily dicts,
GeoJSON FeatureCollection, or nested ``properties.values``). If your
deployment hits a different shape, override the parsing here rather
than at the call site.
"""

from __future__ import annotations

from datetime import date as _date
from typing import Any, Iterable


# 0-4 with the NWS-published color names and a one-line description.
CATEGORIES: dict[int, dict[str, str]] = {
    0: {
        "color": "Green",
        "label": "Little to no risk",
        "description": "Little to no risk from expected heat.",
    },
    1: {
        "color": "Yellow",
        "label": "Minor",
        "description": "Minor risk; primarily affects those extremely sensitive to heat, especially when outdoors without effective cooling and/or adequate hydration.",
    },
    2: {
        "color": "Orange",
        "label": "Moderate",
        "description": "Moderate risk; affects most individuals sensitive to heat, especially those without effective cooling and/or adequate hydration. Impacts possible in some health systems and in heat-sensitive industries.",
    },
    3: {
        "color": "Red",
        "label": "Major",
        "description": "Major risk; affects anyone without effective cooling and/or adequate hydration. Impacts likely in some health systems, heat-sensitive industries, and infrastructure.",
    },
    4: {
        "color": "Magenta",
        "label": "Extreme",
        "description": "Extreme risk; rare, long-duration heat with little to no overnight relief. Affects anyone without effective cooling and/or adequate hydration. Impacts likely in most health systems, heat-sensitive industries, and infrastructure.",
    },
}


def category(level: int | float | None) -> dict[str, Any]:
    """Return the {color,label,description,value} dict for an integer level."""
    if level is None:
        return {"value": None, "color": "Unknown", "label": "Unknown", "description": "No HeatRisk data available."}
    lvl = int(round(float(level)))
    lvl = max(0, min(4, lvl))
    entry = CATEGORIES[lvl]
    return {"value": lvl, **entry}


def reference_text() -> str:
    """Human-readable reference for `nws://heatrisk-categories`."""
    lines = [
        "NWS HeatRisk categories (0-4 scale).",
        "Reference: https://www.weather.gov/safety/heat-heatrisk",
        "",
    ]
    for lvl, info in CATEGORIES.items():
        lines.append(f"  {lvl} {info['color']:<7} {info['label']:<18} - {info['description']}")
    return "\n".join(lines)


# ----------------------------------------------------------------- parsing
def _iter_records(feed: Any) -> Iterable[dict[str, Any]]:
    """Yield daily {date, value} dicts from a few common feed shapes.

    Best-effort: HeatRisk's machine-readable layout is experimental and
    has changed before. If the feed is something we don't recognize,
    yield nothing and let the caller report "no data".
    """
    if feed is None:
        return
    if isinstance(feed, list):
        for r in feed:
            if isinstance(r, dict):
                yield r
        return
    if isinstance(feed, dict):
        # GeoJSON FeatureCollection: {features:[{properties:{date,value}}, ...]}
        feats = feed.get("features")
        if isinstance(feats, list):
            for f in feats:
                props = (f or {}).get("properties") or {}
                if isinstance(props, dict):
                    yield props
            return
        # NWS-style envelope: {properties:{values:[{validTime,value}, ...]}}
        props = feed.get("properties") or {}
        if isinstance(props, dict):
            values = props.get("values")
            if isinstance(values, list):
                for v in values:
                    if isinstance(v, dict):
                        yield v
                return
        # Flat dict keyed by ISO date:
        for k, v in feed.items():
            if isinstance(k, str) and len(k) >= 10 and k[4] == "-":
                if isinstance(v, dict):
                    yield {"date": k, **v}
                else:
                    yield {"date": k, "value": v}


def extract_daily(feed: Any) -> list[dict[str, Any]]:
    """Normalize a HeatRisk feed into ``[{date, value}, ...]`` rows.

    Accepts dates under any of: ``date``, ``valid_date``, ``validTime``,
    ``day``; accepts values under any of: ``value``, ``heatrisk``,
    ``level``, ``category``.
    """
    out: list[dict[str, Any]] = []
    for rec in _iter_records(feed):
        d = (
            rec.get("date")
            or rec.get("valid_date")
            or rec.get("validTime")
            or rec.get("day")
        )
        if isinstance(d, str) and "T" in d:
            d = d.split("T", 1)[0]
        v = rec.get("value")
        if v is None:
            v = rec.get("heatrisk")
        if v is None:
            v = rec.get("level")
        if v is None:
            v = rec.get("category")
        if d is None or v is None:
            continue
        try:
            v_int = int(round(float(v)))
        except (TypeError, ValueError):
            continue
        out.append({"date": str(d), "value": v_int})
    return out


def pick_for_date(rows: list[dict[str, Any]], target: str | None) -> dict[str, Any] | None:
    """Return the row matching ``target`` (ISO date), or the earliest if None."""
    if not rows:
        return None
    rows = sorted(rows, key=lambda r: r["date"])
    if target is None:
        return rows[0]
    for r in rows:
        if r["date"][:10] == target[:10]:
            return r
    return None


def today_iso() -> str:
    return _date.today().isoformat()
