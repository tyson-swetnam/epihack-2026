"""Canned wearable readings for offline / demo use.

The shapes mirror what we would expect the on-device store -- the one
that ``app/shared/wearable.js`` populates from HealthKit / Health
Connect -- to return. Two distinct profiles are baked in so the demo
can drive both the resting-baseline and the heat-stress paths:

``profile = "rest"``   -- a sedentary morning before the heat ramps
``profile = "heat"``   -- a Phoenix afternoon walking outdoors with
                          rising HR and skin temperature, falling HRV

Both profiles span the most recent 24 h ending at ``anchor`` (default:
the time the server was instantiated, so the test harness can pin a
specific moment).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from .catalog import METRIC_CATALOG


@dataclass(frozen=True)
class Reading:
    value:       float
    unit:        str
    recorded_at: str   # ISO-8601 UTC
    source:      str
    loinc_code:  str

    def to_dict(self) -> dict:
        return {
            "value":       self.value,
            "unit":        self.unit,
            "recorded_at": self.recorded_at,
            "source":      self.source,
            "loinc_code":  self.loinc_code,
        }


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Synthetic series generators.
# ---------------------------------------------------------------------------
def _series_hr(anchor: datetime, profile: str) -> list[Reading]:
    """Heart rate, one sample per 5 min over 24 h (288 samples)."""
    out: list[Reading] = []
    for i in range(288):
        t = anchor - timedelta(minutes=5 * (287 - i))
        # Diurnal baseline ~62 bpm at 3 AM, ~78 at 4 PM (simple cosine).
        hour = t.hour + t.minute / 60.0
        baseline = 70 + 8 * (1 if 12 <= hour <= 20 else -1) * 0.7
        v = baseline
        if profile == "heat":
            # Heat ramp during the last 90 min: +35 bpm over the window.
            ramp_index = i - (288 - 18)   # last 18 readings (~90 min)
            if ramp_index >= 0:
                v += min(35, ramp_index * 2)
        out.append(Reading(
            value=float(round(v, 1)),
            unit="bpm",
            recorded_at=_iso(t),
            source="apple_watch_se",
            loinc_code="8867-4",
        ))
    return out


def _series_skin(anchor: datetime, profile: str) -> list[Reading]:
    """Skin temperature, one sample per 10 min over 24 h (144 samples)."""
    out: list[Reading] = []
    for i in range(144):
        t = anchor - timedelta(minutes=10 * (143 - i))
        v = 33.5  # baseline °C
        if profile == "heat":
            ramp_index = i - (144 - 9)
            if ramp_index >= 0:
                v += min(6.0, ramp_index * 0.7)
        out.append(Reading(
            value=float(round(v, 2)),
            unit="degC",
            recorded_at=_iso(t),
            source="apple_watch_se",
            loinc_code="8328-7",
        ))
    return out


def _series_temp(anchor: datetime, profile: str) -> list[Reading]:
    """Body temperature, sparser series (1 per hour, 24 samples)."""
    out: list[Reading] = []
    for i in range(24):
        t = anchor - timedelta(hours=23 - i)
        v = 36.8
        if profile == "heat" and i >= 22:
            v = 37.4
        out.append(Reading(
            value=float(round(v, 2)),
            unit="degC",
            recorded_at=_iso(t),
            source="oral_thermometer",
            loinc_code="8310-5",
        ))
    return out


def _series_hrv(anchor: datetime, profile: str) -> list[Reading]:
    """HRV SDNN -- one reading per hour."""
    out: list[Reading] = []
    for i in range(24):
        t = anchor - timedelta(hours=23 - i)
        v = 52.0
        if profile == "heat" and i >= 22:
            v = 28.0   # drop under heat stress
        out.append(Reading(
            value=float(round(v, 1)),
            unit="ms",
            recorded_at=_iso(t),
            source="apple_watch_se",
            loinc_code="80404-7",
        ))
    return out


def _series_steps(anchor: datetime, profile: str) -> list[Reading]:
    """Steps -- a single 24-h total stamped at the anchor moment."""
    total = 9_400 if profile == "rest" else 13_200
    return [Reading(
        value=float(total),
        unit="steps",
        recorded_at=_iso(anchor),
        source="iphone_motion",
        loinc_code="41950-7",
    )]


_BUILDERS = {
    "8867-4":  _series_hr,
    "8310-5":  _series_temp,
    "8328-7":  _series_skin,
    "80404-7": _series_hrv,
    "41950-7": _series_steps,
}


def build_canned(
    profile: str = "heat",
    anchor: datetime | None = None,
) -> dict[str, list[Reading]]:
    """Build the full canned series for every supported LOINC.

    Args:
        profile: ``"rest"`` or ``"heat"``.
        anchor:  the "now" reference; defaults to UTC now if omitted.
    """
    if profile not in ("rest", "heat"):
        raise ValueError(f"Unknown profile {profile!r}; expected 'rest' or 'heat'.")
    if anchor is None:
        anchor = datetime.now(tz=timezone.utc)
    result: dict[str, list[Reading]] = {}
    for code in METRIC_CATALOG.keys():
        result[code] = _BUILDERS[code](anchor, profile)
    return result


def filter_since(
    readings: Iterable[Reading],
    since_iso: str | None,
    limit: int | None = None,
) -> list[Reading]:
    """Return readings with ``recorded_at >= since_iso``, capped at ``limit``."""
    if since_iso:
        since_dt = datetime.fromisoformat(since_iso.replace("Z", "+00:00"))
    else:
        since_dt = None
    out: list[Reading] = []
    for r in readings:
        if since_dt is not None:
            rt = datetime.fromisoformat(r.recorded_at.replace("Z", "+00:00"))
            if rt < since_dt:
                continue
        out.append(r)
    if limit is not None and limit >= 0:
        out = out[-limit:] if len(out) > limit else out
    return out
