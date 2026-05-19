"""Summary + alert-rule calculations for the wearable MCP server.

Kept deterministic and offline so the Triage Agent can ask the same
"is this user in tachycardia right now?" question and get a stable
answer that doesn't depend on an LLM's interpretation of a chart.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Mapping, Sequence

from .mock_data import Reading


_OPS = {
    ">":  lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<":  lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def summary_24h(readings: Sequence[Reading], now: datetime | None = None) -> dict:
    """min / max / mean / count for the last 24h."""
    if now is None:
        now = datetime.now(tz=timezone.utc)
    cutoff = now - timedelta(hours=24)
    vals: list[float] = []
    last_ts: str | None = None
    for r in readings:
        rt = datetime.fromisoformat(r.recorded_at.replace("Z", "+00:00"))
        if rt < cutoff:
            continue
        vals.append(float(r.value))
        last_ts = r.recorded_at
    if not vals:
        return {
            "count": 0, "min": None, "max": None, "mean": None,
            "unit": None, "loinc_code": readings[0].loinc_code if readings else None,
            "last_recorded_at": None,
        }
    return {
        "count":            len(vals),
        "min":              min(vals),
        "max":              max(vals),
        "mean":             sum(vals) / len(vals),
        "unit":             readings[0].unit,
        "loinc_code":       readings[0].loinc_code,
        "last_recorded_at": last_ts,
    }


@dataclass(frozen=True)
class AlertRule:
    metric:     str   # LOINC
    op:         str   # one of _OPS keys
    value:      float
    window_min: int   # minutes back from "now" the rule looks at

    @classmethod
    def from_mapping(cls, m: Mapping) -> "AlertRule":
        return cls(
            metric=str(m["metric"]),
            op=str(m["op"]),
            value=float(m["value"]),
            window_min=int(m.get("window_min") or m.get("window") or 5),
        )


def evaluate_rules(
    rules: Iterable[Mapping],
    readings_by_metric: Mapping[str, Sequence[Reading]],
    now: datetime | None = None,
) -> list[dict]:
    """For each rule, report whether it currently fires.

    A rule fires iff EVERY reading inside the ``window_min`` window
    satisfies the comparison. (We want "is this user in tachycardia
    *right now*?" not "did they ever hit it?".) If the window contains
    no readings, the rule reports ``fired=False`` with a clear reason.
    """
    if now is None:
        now = datetime.now(tz=timezone.utc)
    out: list[dict] = []
    for raw in rules:
        try:
            rule = AlertRule.from_mapping(raw)
        except (KeyError, ValueError) as exc:
            out.append({"rule": raw, "fired": False, "reason": f"invalid rule: {exc}"})
            continue
        if rule.op not in _OPS:
            out.append({"rule": raw, "fired": False, "reason": f"invalid op: {rule.op!r}"})
            continue
        readings = readings_by_metric.get(rule.metric, [])
        cutoff = now - timedelta(minutes=rule.window_min)
        windowed = [
            r for r in readings
            if datetime.fromisoformat(r.recorded_at.replace("Z", "+00:00")) >= cutoff
        ]
        if not windowed:
            out.append({
                "rule": raw,
                "fired": False,
                "reason": "no readings in window",
                "samples": 0,
            })
            continue
        cmp = _OPS[rule.op]
        all_match = all(cmp(float(r.value), rule.value) for r in windowed)
        any_match = any(cmp(float(r.value), rule.value) for r in windowed)
        out.append({
            "rule":             raw,
            "fired":            all_match,
            "any_match":        any_match,
            "samples":          len(windowed),
            "window_min":       rule.window_min,
            "latest_value":     float(windowed[-1].value),
            "latest_recorded_at": windowed[-1].recorded_at,
        })
    return out
