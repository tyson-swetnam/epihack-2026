"""Walk a full tick mail-in flow over SMS and assert the final dataset."""

from __future__ import annotations

from sms_entry_mcp.state_machine import SmsStateMachine


PHONE = "+14805550101"


def _drive(machine: SmsStateMachine, messages: list[str]) -> list[dict]:
    """Send messages one-by-one and collect outbound dicts."""
    return [machine.step(PHONE, m) for m in messages]


def test_tick_flow_happy_path():
    sm = SmsStateMachine()
    # The first SMS already names the vertical, so the machine skips
    # vertical_select.
    flow = _drive(
        sm,
        [
            "tick",  # greet -> tick_zip
            "85624",  # tick_zip -> tick_attached_date
            "2025-05-15",  # tick_attached_date -> tick_attached_hours
            "6",  # tick_attached_hours -> tick_bite_location
            "leg",  # tick_bite_location -> tick_photo
            "https://example.com/tick.jpg",  # tick_photo -> tick_confirm
            "yes",  # tick_confirm -> submit
        ],
    )

    states = [step["state"] for step in flow]
    assert states == [
        "tick_zip",
        "tick_attached_date",
        "tick_attached_hours",
        "tick_bite_location",
        "tick_photo",
        "tick_confirm",
        "submit",
    ]
    final = flow[-1]
    md = final["minimum_dataset"]
    assert md is not None, "submit should emit a minimum_dataset"
    assert md["channel"] == "sms"
    assert md["vertical"] == "vbd"
    assert md["consent_profile"] == "consent.tick_mailin"
    assert md["general"]["postal_code"] == "85624"
    assert md["general"]["coord_precision"] == "zip"
    assert md["exposure"]["tick_insect_bite"] is True
    assert md["exposure"]["attached_duration_hours"] == 6.0
    assert md["exposure"]["bite_location"] == "leg"
    assert md["auxiliary"]["photo_url"] == "https://example.com/tick.jpg"
    assert md["environmental"]["date_env_incident"] == "2025-05-15"


def test_tick_flow_unknown_hours_and_skip_photo():
    sm = SmsStateMachine()
    flow = _drive(
        sm,
        [
            "Tick",
            "85003",
            "today",
            "unknown",
            "arm",
            "skip",
            "YES",
        ],
    )
    md = flow[-1]["minimum_dataset"]
    assert md is not None
    assert "attached_duration_hours" not in md["exposure"]
    assert md["exposure"]["bite_location"] == "arm"
    # photo_url skipped -> not in auxiliary
    assert "photo_url" not in md["auxiliary"]


def test_tick_flow_rejects_bad_zip_then_recovers():
    sm = SmsStateMachine()
    sm.step(PHONE, "tick")  # -> tick_zip
    bad = sm.step(PHONE, "not a zip")
    assert bad["state"] == "tick_zip", "bad zip should re-prompt"
    good = sm.step(PHONE, "85003")
    assert good["state"] == "tick_attached_date"


def test_tick_flow_confirm_no_returns_to_vertical_select():
    sm = SmsStateMachine()
    for msg in ("tick", "85003", "today", "5", "leg", "skip"):
        sm.step(PHONE, msg)
    step = sm.step(PHONE, "no")
    assert step["state"] == "vertical_select"
    assert step["minimum_dataset"] is None


def test_tick_consent_default_set_after_greet():
    sm = SmsStateMachine()
    sm.step(PHONE, "tick")
    sess = sm.get(PHONE)
    assert sess.state.consent_profile == "consent.tick_mailin"
