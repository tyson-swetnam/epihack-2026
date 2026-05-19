"""Runnable example: Scenario A -- hiker mails in a tick.

Run::

    python -m examples.scenario_a_tick

(or `python agents/examples/scenario_a_tick.py` after installing the
package via ``pip install -e agents``).
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


SCENARIO_A_INPUT = {
    "channel": Channel.MOBILE.value,
    "vertical": Vertical.VBD.value,
    "kind": Kind.REPORT.value,
    "consent_profile": ConsentProfile.TICK_MAILIN.value,
    "general": {
        "age": 38,
        "sex": "M",
        "postal_code": "85624",
        "lat": 31.541,
        "lon": -110.755,
        "unique_id": "hiker-001",
    },
    "exposure": {
        "tick_insect_bite": True,
        "attached_duration_hours": 6.0,
        "bite_location": "leg",
    },
    "auxiliary": {
        "photo_url": "https://example.com/tick.jpg",
        "photo_quality_score": 0.85,
    },
}


async def main() -> None:
    orch = Orchestrator(mcp=FakeMCPClient.with_default_handlers())
    obs = await orch.process(SCENARIO_A_INPUT)
    print(json.dumps(obs.model_dump(mode="json"), indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
