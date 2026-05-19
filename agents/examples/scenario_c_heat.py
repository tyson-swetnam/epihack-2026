"""Runnable example: Scenario C -- CHW heat check-in for an unsheltered resident.

Run::

    python -m examples.scenario_c_heat
"""

from __future__ import annotations

import asyncio
import json

from onehealth_agents import (
    Channel,
    ConsentProfile,
    FakeMCPClient,
    Kind,
    Orchestrator,
    Vertical,
)


SCENARIO_C_INPUT = {
    "channel": Channel.CHW_TABLET.value,
    "vertical": Vertical.HEAT.value,
    "kind": Kind.REPORT.value,
    "consent_profile": ConsentProfile.ANONYMOUS_HEAT.value,
    "general": {
        "age": 47,
        "sex": "M",
        "postal_code": "85003",
        "lat": 33.451,
        "lon": -112.073,
        "unique_id": "outreach-c-1",
    },
    "human": {
        "heavy_sweating": True,
        "headache": True,
    },
    "exposure": {
        "sheltered_status": "unsheltered",
        "ac_access": "no",
        "outdoor_time_24h_hours": 8.0,
        "transport_access": "none",
    },
    "environmental": {
        "nws_heatrisk_level": "Magenta",
        "ambient_temp_f": 115.0,
    },
}


async def main() -> None:
    orch = Orchestrator(mcp=FakeMCPClient.with_default_handlers())
    obs = await orch.process(SCENARIO_C_INPUT)
    print(json.dumps(obs.model_dump(mode="json"), indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
