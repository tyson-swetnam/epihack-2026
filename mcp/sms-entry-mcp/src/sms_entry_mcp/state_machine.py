"""SMS Intake state machine.

Each phone number has a single :class:`SmsSession`. Each inbound SMS
calls :meth:`SmsStateMachine.step`, which:

* picks a language (English or Spanish) the first time it sees the
  number,
* returns the next outbound SMS body (kept under 160 chars so it ships
  as a single SMS segment),
* mutates session state in place,
* when the conversation reaches ``submit``, attaches a fully populated
  ``MinimumDataset``-shaped dict to the session.

The state machine itself is intentionally dependency-free -- it doesn't
import anything from ``onehealth_agents``. The MCP server hands the
finalised intake dict back to the caller, which is responsible for
calling ``Orchestrator.process()`` (see ``agents/sms_adapter.py``).

State catalogue (single source of truth -- the
:data:`STATE_MACHINE_DIAGRAM` resource is generated from this):

    greet                  -> vertical_select
    vertical_select        -> tick_zip | heat_zip | help_menu
    help_menu              -> vertical_select

    Tick (VBD) branch:
        tick_zip           -> tick_attached_date
        tick_attached_date -> tick_attached_hours
        tick_attached_hours-> tick_bite_location
        tick_bite_location -> tick_photo
        tick_photo         -> tick_confirm
        tick_confirm       -> submit

    Heat branch:
        heat_zip           -> heat_unsheltered
        heat_unsheltered   -> heat_ac
        heat_ac            -> heat_symptoms
        heat_symptoms      -> heat_confirm
        heat_confirm       -> submit
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Languages
# ---------------------------------------------------------------------------
SUPPORTED_LANGUAGES: list[str] = ["en", "es"]

_SPANISH_TRIGGERS = {
    "hola",
    "ayuda",
    "salud",
    "garrapata",  # tick
    "calor",  # heat
    "espanol",
    "español",
    "es",
}

_TICK_TRIGGERS = {"tick", "garrapata"}
_HEAT_TRIGGERS = {"heat", "hot", "calor"}
_HELP_TRIGGERS = {"help", "ayuda", "menu", "menú", "info"}
_YES = {"y", "yes", "si", "sí"}
_NO = {"n", "no", "non"}
_BROKEN = {"broken", "roto", "rota", "dañado", "danado"}


# Prompts (kept <=160 chars each so they fit one SMS segment).
PROMPTS: dict[str, dict[str, str]] = {
    "en": {
        "greet": (
            "OneHealth AZ: reply TICK to report a tick bite, HEAT for a heat "
            "check-in, or HELP for options."
        ),
        "vertical_select": (
            "Reply TICK to mail in a tick, HEAT to report heat illness, or "
            "HELP for more."
        ),
        "help_menu": (
            "Options: TICK (mail-in tick) | HEAT (heat self-report) | "
            "STOP (cancel). Texts are not 911."
        ),
        # Tick branch
        "tick_zip": "Tick report: what 5-digit ZIP did the bite happen in?",
        "tick_attached_date": (
            "Got it. What date did you notice the tick attached? Reply "
            "YYYY-MM-DD or 'today'."
        ),
        "tick_attached_hours": (
            "About how many hours was the tick attached? Reply a number, "
            "or 'unknown'."
        ),
        "tick_bite_location": (
            "Where on the body was the bite? Reply one: scalp, neck, arm, "
            "leg, torso, beltline, other."
        ),
        "tick_photo": (
            "Optional: text a photo URL of the tick, or reply SKIP."
        ),
        "tick_confirm": (
            "Confirm: tick bite, ZIP {zip}, attached {hours}h. Reply YES "
            "to submit or NO to start over."
        ),
        # Heat branch
        "heat_zip": "Heat check-in: what 5-digit ZIP are you in right now?",
        "heat_unsheltered": (
            "Are you currently unsheltered (no roof / outside)? Reply YES or NO."
        ),
        "heat_ac": (
            "Do you have working AC at home? Reply YES, NO, or BROKEN."
        ),
        "heat_symptoms": (
            "Any symptoms? Reply with words like: confusion, headache, "
            "dizzy, sweating, cramps, none."
        ),
        "heat_confirm": (
            "Confirm: heat check-in, ZIP {zip}, unsheltered={unsheltered}, "
            "AC={ac}. Reply YES to submit."
        ),
        # Terminal
        "submit": (
            "Thanks. Your report is in. A community health worker may "
            "follow up. Reply STOP to opt out."
        ),
        "reset": "Conversation cleared. Reply TICK or HEAT to start again.",
        "fallback": (
            "Sorry, I didn't catch that. Reply TICK, HEAT, or HELP."
        ),
    },
    "es": {
        "greet": (
            "OneHealth AZ: responde GARRAPATA para reportar una garrapata, "
            "CALOR para chequeo de calor, o AYUDA."
        ),
        "vertical_select": (
            "Responde GARRAPATA para enviar una garrapata, CALOR para "
            "reportar enfermedad por calor, o AYUDA."
        ),
        "help_menu": (
            "Opciones: GARRAPATA | CALOR | STOP (cancelar). "
            "Mensajes de texto no son 911."
        ),
        # Tick branch
        "tick_zip": "Reporte de garrapata: ¿en qué código postal (5 dígitos)?",
        "tick_attached_date": (
            "Bien. ¿Qué día notaste la garrapata? Responde YYYY-MM-DD o 'hoy'."
        ),
        "tick_attached_hours": (
            "¿Cuántas horas estuvo pegada la garrapata? Responde número "
            "o 'no se'."
        ),
        "tick_bite_location": (
            "¿Dónde fue la picadura? Responde: cabeza, cuello, brazo, "
            "pierna, torso, cintura, otro."
        ),
        "tick_photo": (
            "Opcional: envía una URL de foto de la garrapata, o "
            "responde OMITIR."
        ),
        "tick_confirm": (
            "Confirma: garrapata, CP {zip}, pegada {hours}h. Responde SI "
            "para enviar o NO para reiniciar."
        ),
        # Heat branch
        "heat_zip": "Chequeo de calor: ¿en qué código postal estás ahora?",
        "heat_unsheltered": (
            "¿Estás sin techo / afuera ahora? Responde SI o NO."
        ),
        "heat_ac": (
            "¿Tienes aire acondicionado que funciona? Responde SI, NO o ROTO."
        ),
        "heat_symptoms": (
            "¿Síntomas? Responde con palabras: confusión, dolor de cabeza, "
            "mareo, sudor, calambres, ninguno."
        ),
        "heat_confirm": (
            "Confirma: chequeo calor, CP {zip}, sin techo={unsheltered}, "
            "AC={ac}. Responde SI para enviar."
        ),
        # Terminal
        "submit": (
            "Gracias. Tu reporte fue recibido. Un trabajador de salud "
            "puede contactarte. Responde STOP para salir."
        ),
        "reset": "Conversación borrada. Responde GARRAPATA o CALOR para empezar.",
        "fallback": (
            "No entendí. Responde GARRAPATA, CALOR, o AYUDA."
        ),
    },
}


# All known states (including terminal). Used by the resource.
ALL_STATES: list[str] = [
    "greet",
    "vertical_select",
    "help_menu",
    # Tick
    "tick_zip",
    "tick_attached_date",
    "tick_attached_hours",
    "tick_bite_location",
    "tick_photo",
    "tick_confirm",
    # Heat
    "heat_zip",
    "heat_unsheltered",
    "heat_ac",
    "heat_symptoms",
    "heat_confirm",
    # Terminal
    "submit",
    "reset",
]


# Heat-symptom keyword extraction (kept in sync with onehealth_agents
# HumanClass field names).
_HEAT_SYMPTOM_KEYWORDS: dict[str, str] = {
    "confus": "confusion",
    "altered": "confusion",
    "confusión": "confusion",
    "headache": "headache",
    "dolor de cabeza": "headache",
    "head ache": "headache",
    "dizzy": "dizziness",
    "dizziness": "dizziness",
    "faint": "dizziness",
    "mareo": "dizziness",
    "sweat": "heavy_sweating",
    "sudor": "heavy_sweating",
    "cramp": "muscle_cramps",
    "calambre": "muscle_cramps",
    "fever": "fever",
    "fiebre": "fever",
    "hot dry skin": "hot_dry_skin",
    "piel seca": "hot_dry_skin",
    "nausea": "nausea_vomiting",
    "vomit": "nausea_vomiting",
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass
class ConversationState:
    """The serialisable shape of one phone number's session."""

    state: str = "greet"
    lang: str = "en"
    vertical: Optional[str] = None  # 'tick' or 'heat'
    answers: dict[str, Any] = field(default_factory=dict)
    consent_profile: Optional[str] = None
    outbound_log: list[str] = field(default_factory=list)
    inbound_log: list[str] = field(default_factory=list)
    last_updated: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "lang": self.lang,
            "vertical": self.vertical,
            "answers": dict(self.answers),
            "consent_profile": self.consent_profile,
            "outbound_log": list(self.outbound_log),
            "inbound_log": list(self.inbound_log),
            "last_updated": self.last_updated,
        }


@dataclass
class SmsSession:
    from_number: str
    state: ConversationState = field(default_factory=ConversationState)
    minimum_dataset: Optional[dict[str, Any]] = None  # populated at 'submit'


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------
class SmsStateMachine:
    """In-memory state machine, one session per ``from_number``."""

    def __init__(self) -> None:
        self.sessions: dict[str, SmsSession] = {}

    # ---- session helpers ----
    def get(self, from_number: str) -> SmsSession:
        if from_number not in self.sessions:
            self.sessions[from_number] = SmsSession(from_number=from_number)
        return self.sessions[from_number]

    def reset(self, from_number: str) -> None:
        self.sessions.pop(from_number, None)

    def set_consent(self, from_number: str, profile: str) -> None:
        sess = self.get(from_number)
        sess.state.consent_profile = profile

    # ---- main driver ----
    def step(
        self,
        from_number: str,
        body: str,
        lang_hint: Optional[str] = None,
    ) -> dict[str, Any]:
        """Advance the state machine by one inbound SMS.

        Returns a dict with::

            {
              "outbound": "<the text to send back>",
              "state": "<new state>",
              "vertical": "tick" | "heat" | None,
              "minimum_dataset": <dict|None>,   # populated at submit
              "lang": "en" | "es",
            }
        """
        sess = self.get(from_number)
        st = sess.state
        text_raw = (body or "").strip()
        text = text_raw.lower()
        st.inbound_log.append(text_raw)

        # Language detection on first inbound message
        if lang_hint in SUPPORTED_LANGUAGES:
            st.lang = lang_hint
        elif st.state == "greet" and _looks_spanish(text):
            st.lang = "es"

        # Universal commands
        if text in {"stop", "stopall", "cancel", "alto", "salir", "fin"}:
            self.reset(from_number)
            return _bundle(from_number, "reset", st.lang, body=PROMPTS[st.lang]["reset"])

        # If we're at greet, the first inbound message advances us
        # straight to vertical_select, but if the body already names a
        # vertical we skip the intermediate prompt.
        new_state, outbound, md = self._transition(st, text)
        st.state = new_state
        st.last_updated = datetime.now(timezone.utc).isoformat()
        st.outbound_log.append(outbound)
        if md is not None:
            sess.minimum_dataset = md
        return _bundle(
            from_number,
            new_state,
            st.lang,
            body=outbound,
            vertical=st.vertical,
            minimum_dataset=sess.minimum_dataset,
        )

    # ---- transitions ----
    def _transition(
        self, st: ConversationState, text: str
    ) -> tuple[str, str, Optional[dict[str, Any]]]:
        p = PROMPTS[st.lang]
        cur = st.state

        if cur == "greet":
            return self._from_greet(st, text)

        if cur == "vertical_select":
            return self._from_vertical_select(st, text)

        if cur == "help_menu":
            # Any input bounces back to vertical_select.
            return ("vertical_select", p["vertical_select"], None)

        # Tick branch ---------------------------------------------------
        if cur == "tick_zip":
            zip5 = _extract_zip(text)
            if zip5 is None:
                return (cur, p["tick_zip"], None)
            st.answers["postal_code"] = zip5
            return ("tick_attached_date", p["tick_attached_date"], None)

        if cur == "tick_attached_date":
            date_iso = _extract_date(text)
            if date_iso is None:
                return (cur, p["tick_attached_date"], None)
            st.answers["date_attached"] = date_iso
            return ("tick_attached_hours", p["tick_attached_hours"], None)

        if cur == "tick_attached_hours":
            if text in {"unknown", "no se", "no sé", "ns"}:
                st.answers["attached_duration_hours"] = None
            else:
                try:
                    st.answers["attached_duration_hours"] = float(text.split()[0])
                except (ValueError, IndexError):
                    return (cur, p["tick_attached_hours"], None)
            return ("tick_bite_location", p["tick_bite_location"], None)

        if cur == "tick_bite_location":
            loc = _normalise_bite_location(text)
            if loc is None:
                return (cur, p["tick_bite_location"], None)
            st.answers["bite_location"] = loc
            return ("tick_photo", p["tick_photo"], None)

        if cur == "tick_photo":
            if text in {"skip", "omitir", "no", "n"}:
                st.answers["photo_url"] = None
            elif text.startswith("http"):
                st.answers["photo_url"] = text_first_token(text)
            else:
                # treat as skip; SMS might mangle URLs
                st.answers["photo_url"] = None
            confirm = p["tick_confirm"].format(
                zip=st.answers.get("postal_code", "?"),
                hours=_fmt_hours(st.answers.get("attached_duration_hours")),
            )
            return ("tick_confirm", confirm, None)

        if cur == "tick_confirm":
            if text in _YES:
                md = self._build_tick_dataset(st)
                return ("submit", p["submit"], md)
            if text in _NO:
                st.answers.clear()
                st.vertical = None
                return ("vertical_select", p["vertical_select"], None)
            return (cur, p["fallback"], None)

        # Heat branch ---------------------------------------------------
        if cur == "heat_zip":
            zip5 = _extract_zip(text)
            if zip5 is None:
                return (cur, p["heat_zip"], None)
            st.answers["postal_code"] = zip5
            return ("heat_unsheltered", p["heat_unsheltered"], None)

        if cur == "heat_unsheltered":
            if text in _YES:
                st.answers["sheltered_status"] = "unsheltered"
            elif text in _NO:
                st.answers["sheltered_status"] = "sheltered"
            else:
                return (cur, p["heat_unsheltered"], None)
            return ("heat_ac", p["heat_ac"], None)

        if cur == "heat_ac":
            if text in _YES:
                st.answers["ac_access"] = "yes"
            elif text in _NO:
                st.answers["ac_access"] = "no"
            elif text in _BROKEN:
                st.answers["ac_access"] = "yes_broken"
            else:
                return (cur, p["heat_ac"], None)
            return ("heat_symptoms", p["heat_symptoms"], None)

        if cur == "heat_symptoms":
            st.answers["symptoms"] = _extract_heat_symptoms(text)
            confirm = p["heat_confirm"].format(
                zip=st.answers.get("postal_code", "?"),
                unsheltered="yes" if st.answers.get("sheltered_status") == "unsheltered" else "no",
                ac=st.answers.get("ac_access", "?"),
            )
            return ("heat_confirm", confirm, None)

        if cur == "heat_confirm":
            if text in _YES:
                md = self._build_heat_dataset(st)
                return ("submit", p["submit"], md)
            if text in _NO:
                st.answers.clear()
                st.vertical = None
                return ("vertical_select", p["vertical_select"], None)
            return (cur, p["fallback"], None)

        # Terminal states bounce the user back to greet on any new input.
        if cur in {"submit", "reset"}:
            self_reset_no_keep = ConversationState(lang=st.lang)
            st.state = self_reset_no_keep.state
            st.vertical = None
            st.answers.clear()
            return self._from_greet(st, text)

        return ("vertical_select", p["fallback"], None)

    # ---- greet/help helpers ----
    def _from_greet(
        self, st: ConversationState, text: str
    ) -> tuple[str, str, Optional[dict[str, Any]]]:
        # If the first text already names a vertical, skip vertical_select.
        if any(t in text for t in _TICK_TRIGGERS):
            st.vertical = "tick"
            if st.consent_profile is None:
                st.consent_profile = "consent.tick_mailin"
            return ("tick_zip", PROMPTS[st.lang]["tick_zip"], None)
        if any(t in text for t in _HEAT_TRIGGERS):
            st.vertical = "heat"
            if st.consent_profile is None:
                st.consent_profile = "consent.anonymous_heat"
            return ("heat_zip", PROMPTS[st.lang]["heat_zip"], None)
        if any(t in text for t in _HELP_TRIGGERS):
            return ("help_menu", PROMPTS[st.lang]["help_menu"], None)
        return ("vertical_select", PROMPTS[st.lang]["vertical_select"], None)

    def _from_vertical_select(
        self, st: ConversationState, text: str
    ) -> tuple[str, str, Optional[dict[str, Any]]]:
        return self._from_greet(st, text)

    # ---- final dataset builders ----
    def _build_tick_dataset(self, st: ConversationState) -> dict[str, Any]:
        a = st.answers
        general = {
            "postal_code": a.get("postal_code"),
            "coord_precision": "zip",
            "reported_at": datetime.now(timezone.utc).isoformat(),
        }
        exposure = {"tick_insect_bite": True}
        if a.get("attached_duration_hours") is not None:
            exposure["attached_duration_hours"] = a["attached_duration_hours"]
        if a.get("bite_location"):
            exposure["bite_location"] = a["bite_location"]
        auxiliary: dict[str, Any] = {}
        if a.get("photo_url"):
            auxiliary["photo_url"] = a["photo_url"]
        env: dict[str, Any] = {}
        if a.get("date_attached"):
            env["date_env_incident"] = a["date_attached"]
        return {
            "channel": "sms",
            "vertical": "vbd",
            "consent_profile": st.consent_profile or "consent.tick_mailin",
            "general": general,
            "exposure": exposure,
            "auxiliary": auxiliary,
            "environmental": env,
        }

    def _build_heat_dataset(self, st: ConversationState) -> dict[str, Any]:
        a = st.answers
        general = {
            "postal_code": a.get("postal_code"),
            "coord_precision": "zip",
            "reported_at": datetime.now(timezone.utc).isoformat(),
        }
        exposure: dict[str, Any] = {}
        if a.get("sheltered_status"):
            exposure["sheltered_status"] = a["sheltered_status"]
        if a.get("ac_access"):
            exposure["ac_access"] = a["ac_access"]
        human: dict[str, Any] = {}
        for sym in a.get("symptoms") or []:
            human[sym] = True
        if not human:
            human["no_symptoms"] = True
        return {
            "channel": "sms",
            "vertical": "heat",
            "consent_profile": st.consent_profile or "consent.anonymous_heat",
            "general": general,
            "exposure": exposure,
            "human": human,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _bundle(
    from_number: str,
    state: str,
    lang: str,
    *,
    body: str,
    vertical: Optional[str] = None,
    minimum_dataset: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return {
        "from_number": from_number,
        "state": state,
        "lang": lang,
        "vertical": vertical,
        "outbound": body,
        "minimum_dataset": minimum_dataset,
    }


def text_first_token(text: str) -> str:
    return text.split()[0] if text.split() else text


def _looks_spanish(text: str) -> bool:
    for t in _SPANISH_TRIGGERS:
        if t in text:
            return True
    return False


def _extract_zip(text: str) -> Optional[str]:
    for chunk in text.split():
        digits = "".join(c for c in chunk if c.isdigit())
        if len(digits) == 5:
            return digits
    return None


def _extract_date(text: str) -> Optional[str]:
    text = text.strip().lower()
    if text in {"today", "hoy"}:
        return datetime.now(timezone.utc).date().isoformat()
    if text in {"yesterday", "ayer"}:
        d = datetime.now(timezone.utc).date()
        return d.replace(day=max(1, d.day - 1)).isoformat()
    # YYYY-MM-DD anywhere in the body
    for chunk in text.split():
        try:
            datetime.strptime(chunk, "%Y-%m-%d")
            return chunk
        except ValueError:
            continue
    return None


_BITE_LOCATIONS = {
    "scalp": "scalp",
    "cabeza": "scalp",
    "head": "scalp",
    "behind_ear": "behind_ear",
    "ear": "behind_ear",
    "neck": "neck",
    "cuello": "neck",
    "arm": "arm",
    "brazo": "arm",
    "leg": "leg",
    "pierna": "leg",
    "torso": "torso",
    "beltline": "beltline",
    "cintura": "beltline",
    "waist": "beltline",
    "other": "other",
    "otro": "other",
}


def _normalise_bite_location(text: str) -> Optional[str]:
    for key, val in _BITE_LOCATIONS.items():
        if key in text:
            return val
    return None


def _extract_heat_symptoms(text: str) -> list[str]:
    if any(t in text for t in {"none", "ninguno", "nada"}):
        return []
    found: list[str] = []
    for fragment, field_name in _HEAT_SYMPTOM_KEYWORDS.items():
        if fragment in text and field_name not in found:
            found.append(field_name)
    return found


def _fmt_hours(h: Optional[float]) -> str:
    if h is None:
        return "unknown"
    if float(h).is_integer():
        return str(int(h))
    return str(h)


# ---------------------------------------------------------------------------
# State-machine diagram (resource body)
# ---------------------------------------------------------------------------
STATE_MACHINE_DIAGRAM = """\
SMS Intake state machine
========================

Languages: en, es. Picked from first inbound message OR ``lang`` arg.

States:
  greet -> vertical_select | tick_zip | heat_zip | help_menu
  vertical_select -> tick_zip | heat_zip | help_menu
  help_menu -> vertical_select

  Tick (VBD) branch  [consent.tick_mailin default]
    tick_zip -> tick_attached_date    (input: 5-digit ZIP)
    tick_attached_date -> tick_attached_hours  (YYYY-MM-DD or 'today')
    tick_attached_hours -> tick_bite_location  (number or 'unknown')
    tick_bite_location -> tick_photo  (scalp|neck|arm|leg|torso|beltline|other)
    tick_photo -> tick_confirm        (URL or 'skip')
    tick_confirm -> submit            (YES / NO)

  Heat branch  [consent.anonymous_heat default]
    heat_zip -> heat_unsheltered      (5-digit ZIP)
    heat_unsheltered -> heat_ac       (YES/NO)
    heat_ac -> heat_symptoms          (YES/NO/BROKEN)
    heat_symptoms -> heat_confirm     (free-text symptoms)
    heat_confirm -> submit            (YES / NO)

Universal:
  STOP / CANCEL / ALTO  -> reset
  Unknown input on a question state -> re-prompt the same question.

Terminal:
  submit  - emits a MinimumDataset dict; downstream caller hands it
            to Orchestrator.process().
  reset   - clears session; next inbound returns to greet.
"""


__all__ = [
    "ConversationState",
    "SmsSession",
    "SmsStateMachine",
    "SUPPORTED_LANGUAGES",
    "ALL_STATES",
    "PROMPTS",
    "STATE_MACHINE_DIAGRAM",
]
