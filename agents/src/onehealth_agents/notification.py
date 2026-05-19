"""NotificationAgent -- chooses channel + audience, doesn't actually send.

Per ``plan/03``:
* User-facing notification fires first *except* for life-threatening
  triage classes (``tc.call_911``, lab-confirmed-positive outbreak).
* Localization falls back to English; production swaps in the user
  language preference (en / es / nv / ood).
"""

from __future__ import annotations

from typing import Iterable

from .contracts import (
    Channel,
    Notification,
    Observation,
    TriageClass,
    Vertical,
)


_LIFE_THREATENING: frozenset[TriageClass] = frozenset({TriageClass.CALL_911})


class NotificationAgent:
    name = "notification"

    def run(self, observation: Observation) -> list[Notification]:
        triage = observation.triage
        if triage is None:
            return []
        user_first = triage.triage_class not in _LIFE_THREATENING
        notes: list[Notification] = []
        builders = [
            self._user_note(observation),
            self._chw_note(observation),
            self._agency_note(observation),
        ]
        for n in builders:
            if n is not None:
                notes.append(n)
        if not user_first:
            # Life-threatening: agency / 911 first, then the user-facing
            # confirmation. We re-order existing entries in place.
            notes.sort(key=lambda n: 0 if n.audience != "user" else 1)
        return notes

    # ------------------------------------------------------------------
    def _user_note(self, observation: Observation) -> Notification | None:
        triage = observation.triage
        assert triage is not None
        tc = triage.triage_class

        if tc == TriageClass.CALL_911:
            return Notification(
                audience="user",
                channel="app_push",
                priority="critical",
                headline="Call 911 now",
                body=(
                    "Your reported symptoms suggest a life-threatening condition. "
                    "Tap to call 911 or your local emergency number."
                ),
                cta_links=[{"label": "Call 911", "url": "tel:911"}],
            )
        if tc == TriageClass.MAIL_TO_WALKER_LAB:
            label = _first_payload_url(
                observation.enrichments.records, "mailing_label_pdf"
            )
            return Notification(
                audience="user",
                channel="app_push",
                priority="normal",
                headline="Mail in your tick",
                body=(
                    "Print the mailing label below and send the tick to the "
                    "University of Arizona Walker Lab. Watch for fever or rash for 14 days."
                ),
                cta_links=(
                    [{"label": "Mailing label", "url": label}] if label else []
                ),
            )
        if tc == TriageClass.GO_TO_COOLING_CENTER:
            center = _first_payload_field(
                observation.enrichments.records, "centers"
            )
            first = (center or [{}])[0]
            return Notification(
                audience="user",
                channel="app_push",
                priority="high",
                headline=f"Nearest cooling center: {first.get('name', 'see map')}",
                body=(
                    "Go to the nearest cooling center. "
                    f"{first.get('address', '')} (open now)."
                ),
                cta_links=[
                    {
                        "label": "Open in map",
                        "url": f"geo:0,0?q={first.get('address', '')}",
                    }
                ],
            )
        if tc == TriageClass.DISPATCH_CHW:
            return Notification(
                audience="user",
                channel="app_push",
                priority="high",
                headline="A community health worker is on the way",
                body="Stay in a shaded area. Sip water if available.",
            )
        if tc == TriageClass.URGENT_CARE:
            return Notification(
                audience="user",
                channel="app_push",
                priority="high",
                headline="Go to urgent care today",
                body=(
                    f"Triage: {tc.value}. Given current local conditions, please "
                    "be seen today."
                ),
            )
        if tc == TriageClass.SEE_CLINICIAN:
            return Notification(
                audience="user",
                channel="app_push",
                priority="normal",
                headline="See a clinician within 24-48h",
                body="Book a primary-care or tele-health appointment soon.",
            )
        if tc == TriageClass.DRINK_WATER_ADVISORY:
            return Notification(
                audience="user",
                channel="app_push",
                priority="low",
                headline="Drink water",
                body="It's hot; drink a glass of water every 30 minutes.",
            )
        if tc in {TriageClass.CHECK_IN_ONLY, TriageClass.SELF_CARE}:
            return Notification(
                audience="user",
                channel="app_push",
                priority="low",
                headline="We logged your check-in",
                body="Reach back out if anything changes.",
            )
        return None

    def _chw_note(self, observation: Observation) -> Notification | None:
        # CHW gets a copy when the report came in over a CHW tablet
        # (Scenario C) or when transport dispatch is part of the secondary actions.
        triage = observation.triage
        if triage is None:
            return None
        if observation.source != Channel.CHW_TABLET and (
            "dispatch-CHW-transport" not in (triage.secondary_actions or [])
            and triage.triage_class != TriageClass.DISPATCH_CHW
        ):
            return None
        return Notification(
            audience="chw",
            channel="app_push",
            priority="high" if triage.triage_class != TriageClass.CHECK_IN_ONLY else "normal",
            headline="Field action required",
            body=(
                f"Triage: {triage.triage_class.value}. "
                f"Rationale: {triage.rationale}"
            ),
            cta_links=[{"label": "Open observation", "url": f"/obs/{observation.observation_id}"}],
        )

    def _agency_note(self, observation: Observation) -> Notification | None:
        triage = observation.triage
        if triage is None:
            return None
        # Agency dashboard pin for anything moderate or above, or for VBD
        # cases (which feed surveillance).
        if observation.vertical == Vertical.VBD or triage.triage_class in {
            TriageClass.URGENT_CARE,
            TriageClass.CALL_911,
            TriageClass.GO_TO_COOLING_CENTER,
            TriageClass.DISPATCH_CHW,
        }:
            return Notification(
                audience="agency_analyst",
                channel="dashboard_pin",
                priority="normal",
                headline=(
                    f"New {observation.vertical.value} observation: "
                    f"{triage.triage_class.value}"
                ),
                body=triage.rationale,
            )
        return None


def _first_payload_url(records: Iterable, key: str) -> str | None:
    for r in records:
        url = r.payload.get(key)
        if isinstance(url, str):
            return url
    return None


def _first_payload_field(records: Iterable, key: str):
    for r in records:
        val = r.payload.get(key)
        if val is not None:
            return val
    return None


__all__ = ["NotificationAgent"]
