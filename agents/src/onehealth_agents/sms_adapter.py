"""SMS adapter -- wrap the orchestrator for SMS-only callers.

The ``sms-entry-mcp`` server emits a ``MinimumDataset`` dict the first
time a conversation reaches ``submit``. This module hands that dict to
:class:`onehealth_agents.Orchestrator` and squeezes the resulting
:class:`Observation` into a single SMS-shaped outbound message (≤ 160
characters, the upper bound for a single SMS segment) plus a follow-up
link.

The 160-char cap is deliberate: the gateway should always be able to
fit the reply into one SMS segment so users on metered plans don't pay
for two. When the triage class has no natural follow-up URL we fall
back to a short generic placeholder; the gateway can rewrite it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .contracts import (
    Channel,
    Notification,
    Observation,
    TriageClass,
    Vertical,
)
from .orchestrator import Orchestrator


SMS_MAX_CHARS = 160


# Per-triage-class SMS templates. Each must already be short; the
# adapter appends a follow-up link only when there's room.
_TEMPLATES: dict[TriageClass, str] = {
    TriageClass.CALL_911: (
        "URGENT: call 911 now. Symptoms suggest a life-threatening "
        "condition."
    ),
    TriageClass.URGENT_CARE: (
        "Please go to urgent care today. Report logged."
    ),
    TriageClass.SEE_CLINICIAN: (
        "See a clinician in the next 24-48h. Report logged."
    ),
    TriageClass.MAIL_TO_WALKER_LAB: (
        "Mail the tick to UA Walker Lab. Watch for fever or rash 14 days."
    ),
    TriageClass.GO_TO_COOLING_CENTER: (
        "Heat warning: go to the nearest cooling center now."
    ),
    TriageClass.DISPATCH_CHW: (
        "A community health worker is on the way. Stay in shade, sip water."
    ),
    TriageClass.DRINK_WATER_ADVISORY: (
        "It's hot. Drink a glass of water every 30 min. Report logged."
    ),
    TriageClass.SELF_CARE: "Report logged. Self-care advised; reach out if symptoms change.",
    TriageClass.CHECK_IN_ONLY: "Thanks - we logged your check-in.",
    TriageClass.REPORT_TO_AZGFD: "Reported to AZGFD. Thanks for the wildlife sighting.",
}


# Fallback follow-up URL slug (gateway can rewrite at send time).
_FOLLOWUP_BASE = "epihack.az/o/"


@dataclass
class SmsReply:
    """Structured SMS reply.

    The ``body`` is the literal string the gateway will TwiML back; it
    is guaranteed to be at most ``SMS_MAX_CHARS`` characters.
    """

    body: str
    triage_class: Optional[str]
    vertical: Optional[str]
    observation_id: str
    followup_url: Optional[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "body": self.body,
            "triage_class": self.triage_class,
            "vertical": self.vertical,
            "observation_id": self.observation_id,
            "followup_url": self.followup_url,
        }


class SmsAdapter:
    """Thin wrapper that turns an SMS intake into an SMS reply."""

    def __init__(self, orchestrator: Optional[Orchestrator] = None) -> None:
        self.orchestrator = orchestrator or Orchestrator()

    async def handle_inbound_dataset(
        self, minimum_dataset: dict[str, Any]
    ) -> SmsReply:
        """Run the pipeline against a finished SMS intake.

        ``minimum_dataset`` is the dict emitted by
        ``sms_entry_mcp.sms_inbound`` when the state machine reaches
        ``submit``. We force ``channel = sms`` so the Notification
        Agent can pick an SMS-shaped path on the way back.
        """
        # Force SMS as the source channel regardless of what the caller
        # passed, so downstream agents can branch on it.
        payload = dict(minimum_dataset)
        payload["channel"] = Channel.SMS.value
        observation = await self.orchestrator.process(payload)
        return self.format_reply(observation)

    # ------------------------------------------------------------------
    def format_reply(self, observation: Observation) -> SmsReply:
        triage = observation.triage
        tc = triage.triage_class if triage is not None else None
        vertical = observation.vertical.value if observation.vertical else None

        body = self._body_for(observation)
        followup = self._followup_for(observation)

        # Append the follow-up URL only if it fits in one segment.
        if followup:
            tail = f" {followup}"
            if len(body) + len(tail) <= SMS_MAX_CHARS:
                body = body + tail

        if len(body) > SMS_MAX_CHARS:
            body = body[: SMS_MAX_CHARS - 1].rstrip() + "."

        return SmsReply(
            body=body,
            triage_class=tc.value if tc else None,
            vertical=vertical,
            observation_id=observation.observation_id,
            followup_url=followup,
        )

    # ------------------------------------------------------------------
    def _body_for(self, observation: Observation) -> str:
        # Prefer a user-facing Notification if the agent produced one;
        # it already encodes the headline + body the user should see.
        user_note = _first_user_note(observation.notifications)
        if user_note is not None:
            text = f"{user_note.headline}. {user_note.body}".strip()
            if len(text) <= SMS_MAX_CHARS:
                return text
            # Fall through to the template otherwise.

        if observation.triage is None:
            return "Report received. We'll follow up if anything changes."

        tc = observation.triage.triage_class
        template = _TEMPLATES.get(tc)
        if template:
            return template

        # Unknown class: synthesise a minimal acknowledgement.
        return f"Report received: {tc.value}."

    def _followup_for(self, observation: Observation) -> Optional[str]:
        # Tick mail-in flows almost always carry a mailing-label URL on
        # the enrichment payload; use it when present.
        for r in observation.enrichments.records:
            url = r.payload.get("mailing_label_pdf")
            if isinstance(url, str):
                return url
        # Otherwise fall back to a short observation pointer.
        return f"{_FOLLOWUP_BASE}{observation.observation_id.split('.')[-1][:8]}"


def _first_user_note(notes: list[Notification]) -> Optional[Notification]:
    for n in notes:
        if n.audience == "user":
            return n
    return None


__all__ = [
    "SMS_MAX_CHARS",
    "SmsAdapter",
    "SmsReply",
]
