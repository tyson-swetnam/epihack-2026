"""Supported LOINC catalog for the wearable MCP server.

Mirrors the shape used by ``app/shared/wearable.js`` so an LLM that
reads from both ends sees a consistent vocabulary. The LOINC codes
themselves match the entries seeded in
``schema/deep/followups.sql`` (the ``code.loinc.*`` nodes).
"""

from __future__ import annotations

from typing import TypedDict


class MetricSpec(TypedDict):
    loinc_code: str
    name: str
    unit: str
    kg_node_id: str | None


METRIC_CATALOG: dict[str, MetricSpec] = {
    "8867-4": {
        "loinc_code": "8867-4",
        "name":       "Heart rate",
        "unit":       "bpm",
        "kg_node_id": "wearable.heart_rate_bpm",
    },
    "8310-5": {
        "loinc_code": "8310-5",
        "name":       "Body temperature",
        "unit":       "degC",
        # No application.sql wearable_metric node for general body temp;
        # we list it because followups.sql defines the LOINC.
        "kg_node_id": None,
    },
    "8328-7": {
        "loinc_code": "8328-7",
        "name":       "Skin temperature",
        "unit":       "degC",
        "kg_node_id": "wearable.skin_temp_c",
    },
    "80404-7": {
        "loinc_code": "80404-7",
        "name":       "Heart rate variability (SDNN)",
        "unit":       "ms",
        "kg_node_id": "wearable.hrv_ms",
    },
    "41950-7": {
        "loinc_code": "41950-7",
        "name":       "Step count (24 h)",
        "unit":       "steps",
        "kg_node_id": "wearable.steps_24h",
    },
}


SUPPORTED_LOINC: tuple[str, ...] = tuple(METRIC_CATALOG.keys())


def is_supported(code: str) -> bool:
    return code in METRIC_CATALOG


def spec_for(code: str) -> MetricSpec:
    try:
        return METRIC_CATALOG[code]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported LOINC code {code!r}. "
            f"Supported: {', '.join(SUPPORTED_LOINC)}."
        ) from exc
