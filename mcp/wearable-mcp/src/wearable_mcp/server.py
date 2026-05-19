"""FastMCP server exposing wearable readings to LLM clients.

Mock-by-default. The real backend is the on-device store that
``app/shared/wearable.js`` populates from Apple HealthKit or Android
Health Connect after the user grants permission. **This server never
talks to HealthKit / Health Connect directly** -- it is downstream of
consent.

Designed for EpiHack Arizona 2026's Heat focus group. An LLM client
can answer questions like:

    "Is the user currently in tachycardia by the wearable definition
    (>130 bpm, sustained 5+ minutes)?"

by calling::

    wearable_alert_check(rules=[
        {"metric": "8867-4", "op": ">", "value": 130, "window_min": 5}
    ])

The MCP returns a deterministic structured answer so the LLM doesn't
hallucinate the threshold.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .catalog import METRIC_CATALOG, SUPPORTED_LOINC, is_supported, spec_for
from .calculations import evaluate_rules, summary_24h
from .mock_data import Reading, build_canned, filter_since


mcp = FastMCP(
    "wearable",
    instructions=(
        "Read user-consented wearable readings (heart rate, skin "
        "temperature, HRV SDNN, 24-hour step count, body temperature). "
        "LOINC-coded; mock-by-default. Start with "
        "wearable_supported_metrics() to discover the LOINC codes this "
        "build supports, then wearable_recent_readings(metric, since_iso) "
        "or wearable_summary_24h(metric) for raw data, or "
        "wearable_alert_check(rules) to ask deterministic 'is the user "
        "currently in tachycardia / hyperthermia?' style questions. This "
        "server is downstream of user consent: it never talks to "
        "HealthKit / Health Connect directly; the iOS / Android app "
        "shim does the consent dance and stages readings into the "
        "on-device store this server reads."
    ),
)


# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------
# Mock store: keyed by LOINC. Built once at import time so subsequent
# tool calls in the same process see a stable picture (important for
# the "are these two summary calls consistent?" test).
_PROFILE = os.environ.get("WEARABLE_MOCK_PROFILE", "heat")
_CANNED: dict[str, list[Reading]] = build_canned(profile=_PROFILE)


def _store_for(metric: str) -> list[Reading]:
    """The mock store. A future real backend would hit
    ``WEARABLE_BACKEND_URL`` instead; the shape it returns is the
    same list of Reading-shaped dicts."""
    if not is_supported(metric):
        raise ValueError(
            f"Unsupported LOINC code {metric!r}. "
            f"Supported: {', '.join(SUPPORTED_LOINC)}."
        )
    return _CANNED.get(metric, [])


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
@mcp.tool()
def wearable_recent_readings(
    metric: Annotated[str, Field(description="LOINC code (e.g. '8867-4' for heart rate).")],
    since_iso: Annotated[
        str | None,
        Field(description=("ISO-8601 UTC timestamp lower bound (inclusive). "
                           "Omit to default to the last 6 hours."))
    ] = None,
    limit: Annotated[int, Field(ge=1, le=10_000)] = 100,
) -> dict:
    """Recent readings for one LOINC-coded metric.

    Returns ``{"metric": ..., "readings": [Reading, ...], "source": "mock"}``.
    Each Reading has ``value``, ``unit``, ``recorded_at`` (ISO-8601 UTC),
    ``source`` (the device that produced the sample), ``loinc_code``.
    """
    readings = _store_for(metric)
    filtered = filter_since(readings, since_iso, limit=limit)
    return {
        "metric":     metric,
        "name":       spec_for(metric)["name"],
        "unit":       spec_for(metric)["unit"],
        "since_iso":  since_iso,
        "count":      len(filtered),
        "readings":   [r.to_dict() for r in filtered],
        "source":     "mock",
        "profile":    _PROFILE,
    }


@mcp.tool()
def wearable_summary_24h(
    metric: Annotated[str, Field(description="LOINC code.")],
) -> dict:
    """min / max / mean / count for the last 24 h for one metric."""
    readings = _store_for(metric)
    # Use the most recent reading's timestamp as "now" so summaries are
    # stable across calls in the mock harness.
    now = (
        datetime.fromisoformat(readings[-1].recorded_at.replace("Z", "+00:00"))
        if readings else datetime.now(tz=timezone.utc)
    )
    summary = summary_24h(readings, now=now)
    summary["metric"] = metric
    summary["name"]   = spec_for(metric)["name"]
    summary["source"] = "mock"
    return summary


@mcp.tool()
def wearable_alert_check(
    rules: Annotated[
        list[dict],
        Field(
            description=(
                "List of rule dicts. Each rule: "
                "{metric: LOINC, op: '>' '>=' '<' '<=' '==' '!=', "
                "value: number, window_min: int}. "
                "A rule fires iff EVERY reading inside the window satisfies "
                "the comparison."
            ),
        ),
    ],
) -> dict:
    """Evaluate a small rules-spec against the current wearable store.

    Returns ``{"results": [{rule, fired, latest_value, ...}, ...]}``.
    Useful for the Triage Agent to ask 'is this user currently meeting
    a tachycardia threshold?' without re-implementing the math
    LLM-side.
    """
    # Group readings per requested metric so the evaluator doesn't have
    # to re-fetch per rule.
    metrics_needed = {str(r.get("metric")) for r in rules if r.get("metric")}
    bag: dict[str, list[Reading]] = {}
    for code in metrics_needed:
        if is_supported(code):
            bag[code] = _store_for(code)
        else:
            bag[code] = []
    # Use the most-recent reading across the bag as "now" so results
    # are deterministic against the canned data.
    latest_ts = None
    for items in bag.values():
        if items:
            ts = items[-1].recorded_at
            if latest_ts is None or ts > latest_ts:
                latest_ts = ts
    now = (
        datetime.fromisoformat(latest_ts.replace("Z", "+00:00"))
        if latest_ts else datetime.now(tz=timezone.utc)
    )
    results = evaluate_rules(rules, bag, now=now)
    return {"results": results, "source": "mock", "as_of": (latest_ts or now.isoformat())}


@mcp.tool()
def wearable_supported_metrics() -> dict:
    """Which LOINC-coded metrics this build supports + name + unit."""
    return {
        "metrics": [
            {
                "loinc_code": spec["loinc_code"],
                "name":       spec["name"],
                "unit":       spec["unit"],
                "kg_node_id": spec["kg_node_id"],
            }
            for spec in METRIC_CATALOG.values()
        ],
        "source": "mock",
    }


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------
@mcp.resource("wearable://loinc-codes")
def loinc_codes_resource() -> str:
    """Text reference matching the LOINC entries seeded in
    ``schema/deep/followups.sql`` (the ``code.loinc.*`` nodes)."""
    lines = [
        "LOINC codes supported by this wearable-mcp build.",
        "These match the code.loinc.* nodes seeded in "
        "schema/deep/followups.sql.",
        "",
    ]
    for spec in METRIC_CATALOG.values():
        kg = spec["kg_node_id"] or "(no kg node — code present, no wearable_metric node yet)"
        lines.append(
            f"  {spec['loinc_code']:>8}  {spec['name']:<32}  {spec['unit']:<6}  -> {kg}"
        )
    return "\n".join(lines)


@mcp.resource("wearable://privacy-stance")
def privacy_stance_resource() -> str:
    """Explicit text: this MCP never touches HealthKit / Health Connect
    directly; it only reads from a user-consented on-device store."""
    return (
        "PRIVACY STANCE\n"
        "==============\n"
        "\n"
        "This MCP server never talks to Apple HealthKit or Android Health\n"
        "Connect directly. Those data sources require on-device user\n"
        "consent and stay on the user's device.\n"
        "\n"
        "The server is a CONSUMER of the on-device store that\n"
        "app/shared/wearable.js populates after the user grants\n"
        "permission through the webkit.messageHandlers.health bridge\n"
        "(iOS installed PWA) or navigator.healthConnect (Android Origin\n"
        "Trial). The MCP-side picture is therefore read-only and\n"
        "downstream of consent.\n"
        "\n"
        "Until that on-device store exists in production, the server\n"
        "runs mock-by-default. Set WEARABLE_BACKEND_URL to point at a\n"
        "real consented-store proxy when one is available.\n"
        "\n"
        "Consent profile in the kg: consent.wearable_only.\n"
        "See schema/deep/application.sql for the suppression rules.\n"
    )
