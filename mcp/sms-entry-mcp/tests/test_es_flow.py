"""Spanish-language SMS flow.

The first inbound message decides the language; subsequent prompts and
the final dataset content are in Spanish-friendly slugs but field names
stay English (they're the kg ``param.*`` slug suffixes from
``schema/knowledge_graph.sql`` so the rest of the pipeline doesn't have
to translate at the contract layer).
"""

from __future__ import annotations

from sms_entry_mcp.state_machine import PROMPTS, SmsStateMachine


PHONE = "+14805550303"


def test_spanish_trigger_switches_prompts():
    sm = SmsStateMachine()
    first = sm.step(PHONE, "hola")
    assert first["lang"] == "es"
    assert first["outbound"] == PROMPTS["es"]["vertical_select"]


def test_spanish_garrapata_kicks_off_tick_flow():
    sm = SmsStateMachine()
    first = sm.step(PHONE, "garrapata")
    assert first["lang"] == "es"
    assert first["state"] == "tick_zip"
    assert first["outbound"] == PROMPTS["es"]["tick_zip"]


def test_spanish_calor_kicks_off_heat_flow_and_completes():
    sm = SmsStateMachine()
    sm.step(PHONE, "calor")  # -> heat_zip in Spanish
    sess = sm.get(PHONE)
    assert sess.state.lang == "es"
    assert sess.state.state == "heat_zip"

    sm.step(PHONE, "85003")
    sm.step(PHONE, "si")  # unsheltered yes
    sm.step(PHONE, "no")  # AC no
    sm.step(PHONE, "mareo y calambres")  # dizzy + cramps
    final = sm.step(PHONE, "si")
    md = final["minimum_dataset"]
    assert md is not None
    assert md["vertical"] == "heat"
    assert md["exposure"]["sheltered_status"] == "unsheltered"
    assert md["human"]["dizziness"] is True
    assert md["human"]["muscle_cramps"] is True


def test_lang_arg_overrides_auto_detection():
    sm = SmsStateMachine()
    first = sm.step(PHONE, "tick", lang_hint="es")
    # Vertical correctly identified, but prompt is Spanish.
    assert first["lang"] == "es"
    assert first["state"] == "tick_zip"
    assert first["outbound"] == PROMPTS["es"]["tick_zip"]
