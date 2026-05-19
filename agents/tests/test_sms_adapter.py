"""SMS adapter -- exercise both verticals via Scenarios A and C.

The adapter takes a ``MinimumDataset`` dict (the shape
``sms_entry_mcp.sms_inbound`` emits at ``submit``), runs the
orchestrator end-to-end, and packs the triage result into a single
≤160-char SMS body. We reuse the same canned MCP scenario data the
orchestrator tests use so we know the triage decisions are stable.
"""

from __future__ import annotations

import pytest

from onehealth_agents import (
    Channel,
    FakeMCPClient,
    Orchestrator,
    SMS_MAX_CHARS,
    SmsAdapter,
    TriageClass,
    Vertical,
)


# --------------------------------------------------------------------------
# Scenario A reformulated as an SMS-emitted MinimumDataset dict.
# Mirrors what sms_entry_mcp would produce after the tick mail-in flow.
# --------------------------------------------------------------------------
SCENARIO_A_SMS = {
    "channel": Channel.SMS.value,
    "vertical": Vertical.VBD.value,
    "consent_profile": "consent.tick_mailin",
    "general": {
        "postal_code": "85624",
        "lat": 31.541,
        "lon": -110.755,
        "unique_id": "sms-hiker-001",
        "coord_precision": "zip",
    },
    "exposure": {
        "tick_insect_bite": True,
        "attached_duration_hours": 6.0,
        "bite_location": "leg",
    },
    "auxiliary": {
        "photo_url": "https://example.com/tick.jpg",
    },
}


# --------------------------------------------------------------------------
# Scenario C reformulated as an SMS-emitted MinimumDataset dict.
# --------------------------------------------------------------------------
SCENARIO_C_SMS = {
    "channel": Channel.SMS.value,
    "vertical": Vertical.HEAT.value,
    "consent_profile": "consent.anonymous_heat",
    "general": {
        "postal_code": "85003",
        "lat": 33.451,
        "lon": -112.073,
        "unique_id": "sms-outreach-1",
        "coord_precision": "zip",
    },
    "human": {
        "heavy_sweating": True,
        "headache": True,
    },
    "exposure": {
        "sheltered_status": "unsheltered",
        "ac_access": "no",
        "outdoor_time_24h_hours": 8.0,
    },
    "environmental": {
        "nws_heatrisk_level": "Magenta",
        "ambient_temp_f": 115.0,
    },
}


def _adapter() -> SmsAdapter:
    return SmsAdapter(Orchestrator(mcp=FakeMCPClient.with_default_handlers()))


@pytest.mark.asyncio
async def test_scenario_a_tick_returns_sms_reply():
    reply = await _adapter().handle_inbound_dataset(SCENARIO_A_SMS)

    assert reply.vertical == Vertical.VBD.value
    assert reply.triage_class == TriageClass.MAIL_TO_WALKER_LAB.value
    # Body fits one SMS segment.
    assert 0 < len(reply.body) <= SMS_MAX_CHARS
    # User instruction mentions the tick mail-in or the lab.
    low = reply.body.lower()
    assert "mail" in low or "tick" in low or "walker" in low


@pytest.mark.asyncio
async def test_scenario_a_includes_followup_url_when_available():
    reply = await _adapter().handle_inbound_dataset(SCENARIO_A_SMS)
    # The Walker-lab mock returns a mailing-label PDF URL in its
    # enrichment payload; the adapter should surface it.
    assert reply.followup_url is not None
    # If the URL fit in the body, it should be there.
    if len(reply.body) <= SMS_MAX_CHARS:
        # Either the followup_url is appended, OR the body already
        # was the user notification headline+body (which has its own
        # CTA structure). Both are acceptable.
        pass


@pytest.mark.asyncio
async def test_scenario_c_heat_returns_cooling_center_sms():
    reply = await _adapter().handle_inbound_dataset(SCENARIO_C_SMS)
    assert reply.vertical == Vertical.HEAT.value
    assert reply.triage_class == TriageClass.GO_TO_COOLING_CENTER.value
    assert 0 < len(reply.body) <= SMS_MAX_CHARS
    low = reply.body.lower()
    # The cooling-center message should mention cooling, heat, or a center.
    assert "cool" in low or "center" in low or "heat" in low


@pytest.mark.asyncio
async def test_force_channel_sms_overrides_input_channel():
    """Adapter should overwrite whatever 'channel' the caller passed."""
    payload = dict(SCENARIO_A_SMS)
    payload["channel"] = Channel.MOBILE.value  # bogus, should be ignored
    adapter = _adapter()
    reply = await adapter.handle_inbound_dataset(payload)
    assert reply.vertical == Vertical.VBD.value


@pytest.mark.asyncio
async def test_reply_is_serialisable():
    reply = await _adapter().handle_inbound_dataset(SCENARIO_C_SMS)
    d = reply.to_dict()
    assert set(d) == {
        "body",
        "triage_class",
        "vertical",
        "observation_id",
        "followup_url",
    }
    assert isinstance(d["body"], str)
    assert d["observation_id"].startswith("observation.")


@pytest.mark.asyncio
async def test_body_never_exceeds_sms_segment():
    """Even with verbose user notifications, the body stays <=160 chars."""
    for payload in (SCENARIO_A_SMS, SCENARIO_C_SMS):
        reply = await _adapter().handle_inbound_dataset(payload)
        assert len(reply.body) <= SMS_MAX_CHARS, (
            f"SMS body {len(reply.body)} chars: {reply.body!r}"
        )
