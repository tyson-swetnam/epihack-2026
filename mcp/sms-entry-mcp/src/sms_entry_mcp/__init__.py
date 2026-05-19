"""SMS-only entry-point MCP server.

A Twilio-compatible Model Context Protocol server that walks a user
without a smartphone through the same Minimum-Dataset intake the mobile
app drives. Mock-by-default so callers can exercise the full state
machine offline; flip ``SMS_MODE=twilio`` and supply
``SMS_TWILIO_AUTH_TOKEN`` to wire it to a real Twilio webhook.

Built for EpiHack Arizona 2026, Phase 2 of
``plan/05-roadmap.md`` (SMS-only flow for users with no smartphone).
"""

__version__ = "0.1.0"

from .state_machine import (
    ConversationState,
    SmsSession,
    SmsStateMachine,
    SUPPORTED_LANGUAGES,
    STATE_MACHINE_DIAGRAM,
)
from .signatures import verify_twilio_signature

__all__ = [
    "__version__",
    "ConversationState",
    "SmsSession",
    "SmsStateMachine",
    "SUPPORTED_LANGUAGES",
    "STATE_MACHINE_DIAGRAM",
    "verify_twilio_signature",
]
