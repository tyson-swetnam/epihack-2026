"""Heat-vertical SMS flow: assert the triage-shaped payload."""

from __future__ import annotations

from sms_entry_mcp.state_machine import SmsStateMachine


PHONE = "+14805550202"


def test_heat_flow_unsheltered_no_ac_with_symptoms():
    sm = SmsStateMachine()
    flow = [
        sm.step(PHONE, "heat"),
        sm.step(PHONE, "85003"),
        sm.step(PHONE, "yes"),  # unsheltered
        sm.step(PHONE, "no"),  # no AC
        sm.step(PHONE, "headache and dizzy, sweating a lot"),
        sm.step(PHONE, "yes"),  # confirm
    ]

    states = [s["state"] for s in flow]
    assert states == [
        "heat_zip",
        "heat_unsheltered",
        "heat_ac",
        "heat_symptoms",
        "heat_confirm",
        "submit",
    ]
    md = flow[-1]["minimum_dataset"]
    assert md is not None
    assert md["channel"] == "sms"
    assert md["vertical"] == "heat"
    assert md["consent_profile"] == "consent.anonymous_heat"
    assert md["general"]["postal_code"] == "85003"
    assert md["exposure"]["sheltered_status"] == "unsheltered"
    assert md["exposure"]["ac_access"] == "no"
    # All three symptoms parsed from free text.
    assert md["human"]["headache"] is True
    assert md["human"]["dizziness"] is True
    assert md["human"]["heavy_sweating"] is True
    # ``no_symptoms`` should NOT be set when symptoms are present.
    assert md["human"].get("no_symptoms") is not True


def test_heat_flow_sheltered_with_broken_ac_no_symptoms():
    sm = SmsStateMachine()
    flow = [
        sm.step(PHONE, "heat"),
        sm.step(PHONE, "85015"),
        sm.step(PHONE, "no"),  # not unsheltered
        sm.step(PHONE, "broken"),  # AC broken
        sm.step(PHONE, "none"),  # no symptoms
        sm.step(PHONE, "yes"),
    ]
    md = flow[-1]["minimum_dataset"]
    assert md is not None
    assert md["exposure"]["sheltered_status"] == "sheltered"
    assert md["exposure"]["ac_access"] == "yes_broken"
    assert md["human"].get("no_symptoms") is True


def test_heat_flow_bad_ac_input_reprompts():
    sm = SmsStateMachine()
    sm.step(PHONE, "heat")
    sm.step(PHONE, "85003")
    sm.step(PHONE, "yes")  # unsheltered
    bad = sm.step(PHONE, "maybe")
    assert bad["state"] == "heat_ac", "unknown AC input should re-prompt"


def test_heat_consent_default_after_greet():
    sm = SmsStateMachine()
    sm.step(PHONE, "heat")
    sess = sm.get(PHONE)
    assert sess.state.consent_profile == "consent.anonymous_heat"


def test_heat_overall_carries_triage_hand_off_fields():
    """Smoke-check that the dataset has every field the Triage Agent's
    Heat branch reads: sheltered_status, ac_access, and symptoms in
    the Human-class section."""
    sm = SmsStateMachine()
    sm.step(PHONE, "heat")
    sm.step(PHONE, "85003")
    sm.step(PHONE, "yes")
    sm.step(PHONE, "no")
    sm.step(PHONE, "confusion")
    md = sm.step(PHONE, "yes")["minimum_dataset"]
    assert md is not None
    assert "sheltered_status" in md["exposure"]
    assert "ac_access" in md["exposure"]
    assert md["human"]["confusion"] is True
