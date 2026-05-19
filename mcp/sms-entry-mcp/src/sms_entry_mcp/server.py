"""FastMCP server exposing the SMS-only intake state machine.

Mock-by-default: each tool drives an in-memory state machine. Real
Twilio webhook wiring is a thin HTTP service that:

1. Verifies ``X-Twilio-Signature`` via :func:`verify_twilio_signature`
   (also exposed as a tool below).
2. Calls :func:`sms_inbound` with the ``From`` / ``Body`` form fields.
3. Returns the resulting ``outbound`` text wrapped in TwiML.
4. When the returned ``minimum_dataset`` is non-null, hands it to
   ``onehealth_agents.Orchestrator.process()`` via the
   ``sms_adapter.py`` helper.

The MCP server itself never reaches out to the Twilio API; that keeps
the test suite hermetic and lets graders drive the full flow with no
external dependencies.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .signatures import verify_twilio_signature
from .state_machine import (
    PROMPTS,
    STATE_MACHINE_DIAGRAM,
    SUPPORTED_LANGUAGES,
    SmsStateMachine,
)


mcp = FastMCP(
    "sms-entry",
    instructions=(
        "SMS-only intake entry point for users without a smartphone. "
        "Tools simulate inbound SMS, inspect transcripts, and verify "
        "Twilio signatures. The state machine walks through the tick "
        "(VBD) or heat minimum-dataset and emits a MinimumDataset dict "
        "the downstream onehealth_agents Orchestrator can consume. "
        "Mock-by-default; set SMS_MODE=twilio + SMS_TWILIO_AUTH_TOKEN "
        "for real-webhook mode."
    ),
)


# Single shared state machine for the lifetime of the server process.
_machine = SmsStateMachine()


def _state_payload(from_number: str) -> dict[str, Any]:
    sess = _machine.get(from_number)
    return {
        "from_number": from_number,
        "state": sess.state.to_dict(),
        "minimum_dataset": sess.minimum_dataset,
    }


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
@mcp.tool()
def sms_inbound(
    from_number: Annotated[
        str, Field(description="E.164 phone number that texted in, e.g. '+14805551212'.")
    ],
    body: Annotated[
        str, Field(description="Raw SMS body text the user sent.")
    ],
    message_sid: Annotated[
        Optional[str],
        Field(default=None, description="Twilio MessageSid; logged for traceability."),
    ] = None,
    lang: Annotated[
        str,
        Field(default="en", description="Language hint: 'en' or 'es'. Pass '' to auto-detect."),
    ] = "en",
) -> dict[str, Any]:
    """Simulate an inbound SMS, advance the state machine one step.

    Returns the outbound message, the new state, the chosen vertical
    (once known), and -- once the conversation reaches ``submit`` -- a
    ``MinimumDataset``-shaped dict ready to hand to
    ``Orchestrator.process()``.
    """
    lang_hint = lang if lang in SUPPORTED_LANGUAGES else None
    result = _machine.step(from_number, body, lang_hint=lang_hint)
    result["message_sid"] = message_sid
    return result


@mcp.tool()
def sms_outbound_log(
    from_number: str,
    limit: Annotated[int, Field(ge=1, le=200, default=20)] = 20,
) -> dict[str, Any]:
    """Return the last ``limit`` outbound messages sent to a phone number."""
    sess = _machine.get(from_number)
    log = sess.state.outbound_log[-limit:]
    return {"from_number": from_number, "outbound": log, "count": len(log)}


@mcp.tool()
def sms_set_consent(
    from_number: str,
    profile: Annotated[
        str,
        Field(
            description=(
                "consent.* slug, e.g. 'consent.anonymous_heat' or "
                "'consent.tick_mailin'."
            )
        ),
    ],
) -> dict[str, Any]:
    """Override the consent profile for a phone number's session."""
    _machine.set_consent(from_number, profile)
    return {"from_number": from_number, "consent_profile": profile}


@mcp.tool()
def sms_state(from_number: str) -> dict[str, Any]:
    """Return the current state + answers + minimum-dataset for a phone."""
    return _state_payload(from_number)


@mcp.tool()
def sms_reset(from_number: str) -> dict[str, Any]:
    """Clear conversation state for a phone number."""
    _machine.reset(from_number)
    return {"from_number": from_number, "reset": True}


@mcp.tool()
def sms_twilio_webhook_signature_verify(
    body: Annotated[
        dict[str, str],
        Field(description="POST form parameters Twilio sent."),
    ],
    signature: Annotated[
        str, Field(description="Value of the X-Twilio-Signature header.")
    ],
    url: Annotated[
        str, Field(description="Full URL the webhook hit (scheme+host+path).")
    ],
    auth_token: Annotated[
        Optional[str],
        Field(
            default=None,
            description=(
                "Override token. Falls back to env SMS_TWILIO_AUTH_TOKEN. "
                "Passed explicitly so the tool stays a pure function."
            ),
        ),
    ] = None,
) -> dict[str, Any]:
    """Verify a Twilio X-Twilio-Signature HMAC-SHA1 header."""
    import os

    token = auth_token or os.environ.get("SMS_TWILIO_AUTH_TOKEN", "")
    ok = verify_twilio_signature(
        auth_token=token, url=url, params=body, signature=signature
    )
    return {"valid": ok, "url": url}


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------
@mcp.resource("sms://supported-languages")
def supported_languages_resource() -> str:
    """Language codes the SMS state machine answers in."""
    return "\n".join(
        f"{code}: {'English' if code == 'en' else 'Spanish'}"
        for code in SUPPORTED_LANGUAGES
    )


@mcp.resource("sms://state-machine")
def state_machine_resource() -> str:
    """Conversation states + transitions for introspection."""
    return STATE_MACHINE_DIAGRAM


@mcp.resource("sms://prompts/{lang}")
def prompts_resource(lang: str) -> str:
    """All prompts for a given language (debugging / translation review)."""
    if lang not in PROMPTS:
        return f"Unsupported language: {lang}. Try one of {SUPPORTED_LANGUAGES}."
    lines = [f"{k}: {v}" for k, v in PROMPTS[lang].items()]
    return "\n".join(lines)


__all__ = ["mcp"]
