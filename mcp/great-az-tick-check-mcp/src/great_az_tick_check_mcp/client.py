"""Client for the Great Arizona Tick Check submission tracker.

There is **no public REST API** for the Great Arizona Tick Check
today; submissions are mailed in to Dr. Kathleen Walker's lab in
Forbes 410 at the University of Arizona. To let the rest of the
EpiHack stack treat the program as just another MCP-wrapped data
source, this client ships an **in-memory mock backend** by default.

Set ``GATTC_BACKEND_URL`` in the environment to swap the mock for a
real HTTP backend once the Walker lab (or whoever inherits the
program) ships one. The client deliberately keeps its mock and HTTP
paths behind a single ``GreatAZTickCheckClient`` facade so callers
(the FastMCP tools in ``server.py``) don't have to care which is
active.

The static mailing address comes from ``wildlife/resources.md``:

    Dr. Kathleen Walker, Forbes 410, Department of Entomology,
    P.O. Box 210036, University of Arizona, Tucson, AZ 85721.

The list of pathogens screened comes from
``schema/deep/pathogens.sql`` and the matching ICD-10 codes from
``schema/deep/standards.sql`` (with the secondary tick-borne codes
that the Walker lab routinely screens for but aren't yet seeded in
``standards.sql`` -- A69.20 Lyme, A77.49 ehrlichiosis/anaplasmosis,
B60.0 babesiosis, A77.40 ehrlichiosis unspecified -- carried inline
so the tool returns a complete reference list).
"""

from __future__ import annotations

import os
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx


# ---------------------------------------------------------------------------
# Constants — overridable via env so the server can be retargeted without a
# code change once a real backend ships.
# ---------------------------------------------------------------------------
DEFAULT_BACKEND_URL: str | None = os.environ.get("GATTC_BACKEND_URL") or None
DEFAULT_API_TOKEN: str | None = os.environ.get("GATTC_API_TOKEN") or None

DEFAULT_LABEL_BASE: str = os.environ.get(
    "GATTC_LABEL_BASE", "https://great-arizona-tick-check.example/labels"
)
DEFAULT_STATUS_BASE: str = os.environ.get(
    "GATTC_STATUS_BASE", "https://great-arizona-tick-check.example/submissions"
)
DEFAULT_TURNAROUND_DAYS: int = int(os.environ.get("GATTC_TURNAROUND_DAYS", "21"))

# Verbatim from wildlife/resources.md. Do not localize -- this is the
# real shipping address public submitters use.
WALKER_LAB_MAILING_ADDRESS: str = (
    "Dr. Kathleen Walker\n"
    "Forbes 410, Department of Entomology\n"
    "P.O. Box 210036\n"
    "University of Arizona\n"
    "Tucson, AZ 85721"
)

# Hard-coded short list of Arizona-relevant tick species, used by both
# `gattc_species_identification_from_photo` and the mock complete-status
# step. Keep this list small; the lab's authoritative ID always wins.
AZ_TICK_SPECIES: list[dict[str, str]] = [
    {
        "common_name": "Brown dog tick",
        "scientific_name": "Rhipicephalus sanguineus",
        "notes": (
            "Dominant statewide species; the principal Rocky Mountain spotted "
            "fever (RMSF) vector in Arizona, especially in tribal-community "
            "clusters where free-roaming dogs amplify transmission."
        ),
    },
    {
        "common_name": "Western black-legged tick",
        "scientific_name": "Ixodes pacificus",
        "notes": (
            "Vector of Borrelia burgdorferi (Lyme disease) and Anaplasma "
            "phagocytophilum. Documented in Mohave County by the Great Arizona "
            "Tick Check; rare in AZ outside higher-elevation forested areas."
        ),
    },
    {
        "common_name": "Gulf Coast tick",
        "scientific_name": "Amblyomma maculatum",
        "notes": (
            "Vector of Rickettsia parkeri (a milder spotted fever group "
            "rickettsiosis). Range-expanding; identified by the Walker lab in "
            "Cochise and Santa Cruz counties."
        ),
    },
    {
        "common_name": "Rocky Mountain wood tick",
        "scientific_name": "Dermacentor andersoni",
        "notes": (
            "Vector of Colorado tick fever, RMSF, and tularemia. Found at "
            "higher elevations in northern Arizona."
        ),
    },
    {
        "common_name": "American dog tick",
        "scientific_name": "Dermacentor variabilis",
        "notes": (
            "Historically the primary RMSF vector in the eastern US; in AZ it "
            "co-occurs with the brown dog tick. Also implicated in tularemia."
        ),
    },
]

# Pathogens the Walker lab screens submitted ticks for. ICD-10 codes
# for Rickettsia rickettsii (A77.0) come directly from
# schema/deep/standards.sql; the others come from schema/deep/pathogens.sql
# (and standard CDC tick-borne disease references for codes
# standards.sql doesn't yet seed).
PATHOGENS_SCREENED: list[dict[str, Any]] = [
    {
        "pathogen_id": "pathogen.rickettsia_rickettsii",
        "scientific_name": "Rickettsia rickettsii",
        "disease": "Rocky Mountain spotted fever (RMSF)",
        "icd10": "A77.0",
        "icd10_description": "Spotted fever due to Rickettsia rickettsii",
        "primary_vector": "Rhipicephalus sanguineus (brown dog tick)",
    },
    {
        "pathogen_id": "pathogen.rickettsia_parkeri",
        "scientific_name": "Rickettsia parkeri",
        "disease": "R. parkeri rickettsiosis (mild spotted fever)",
        "icd10": "A77.8",
        "icd10_description": "Other spotted fevers",
        "primary_vector": "Amblyomma maculatum (Gulf Coast tick)",
    },
    {
        "pathogen_id": "pathogen.borrelia_burgdorferi",
        "scientific_name": "Borrelia burgdorferi",
        "disease": "Lyme disease",
        "icd10": "A69.20",
        "icd10_description": "Lyme disease, unspecified",
        "primary_vector": "Ixodes pacificus (Western black-legged tick) in AZ",
    },
    {
        "pathogen_id": "pathogen.anaplasma_phagocytophilum",
        "scientific_name": "Anaplasma phagocytophilum",
        "disease": "Anaplasmosis",
        "icd10": "A77.49",
        "icd10_description": "Other ehrlichiosis (incl. anaplasmosis)",
        "primary_vector": "Ixodes pacificus",
    },
    {
        "pathogen_id": "pathogen.babesia_microti",
        "scientific_name": "Babesia microti",
        "disease": "Babesiosis",
        "icd10": "B60.0",
        "icd10_description": "Babesiosis",
        "primary_vector": "Ixodes pacificus (rare in AZ; mostly travel-acquired)",
    },
    {
        "pathogen_id": "pathogen.ehrlichia_chaffeensis",
        "scientific_name": "Ehrlichia chaffeensis",
        "disease": "Human monocytic ehrlichiosis",
        "icd10": "A77.40",
        "icd10_description": "Ehrlichiosis, unspecified",
        "primary_vector": "Amblyomma americanum (lone star tick) — not endemic AZ",
    },
]


# ---------------------------------------------------------------------------
# In-memory submission record
# ---------------------------------------------------------------------------
@dataclass
class Submission:
    """A single tick submission tracked by the mock backend."""

    submission_id: str
    submitter_email: str
    submitter_name: str
    county: str
    zip_code: str
    tick_date: str
    attachment_duration_hours: float | None
    host: str
    body_location: str | None
    photo_url: str | None
    consent_to_research_use: bool
    created_at: str
    status: str = "received"
    species: dict[str, Any] | None = None
    pathogens_tested: list[dict[str, Any]] = field(default_factory=list)
    notes: str | None = None

    def as_public_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# ID + URL helpers
# ---------------------------------------------------------------------------
def _new_submission_id() -> str:
    """Short, human-typable submission ID.

    `secrets.token_hex(6)` -> 12 lowercase hex chars (e.g. ``a3f81b4c9d22``).
    Avoids pulling a ULID dep; collision probability for hackathon-scale
    use is negligible. The mock backend additionally rejects collisions.
    """
    return secrets.token_hex(6)


def _status_url(submission_id: str, base: str = DEFAULT_STATUS_BASE) -> str:
    return f"{base.rstrip('/')}/{submission_id}"


def _label_url(submission_id: str, fmt: str = "pdf",
               base: str = DEFAULT_LABEL_BASE) -> str:
    fmt = fmt.lower()
    if fmt not in ("pdf", "png"):
        raise ValueError(f"Unsupported label format: {fmt!r} (expected 'pdf' or 'png')")
    return f"{base.rstrip('/')}/{submission_id}.{fmt}"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Backend implementations
# ---------------------------------------------------------------------------
class _MockBackend:
    """In-memory submission store -- the default backend.

    Submissions persist for the lifetime of the MCP-server process, so
    an LLM can chain `gattc_create_submission` -> `gattc_submission_status`
    -> `gattc_mailing_label` in a single session and get coherent results.

    Status auto-advances on each `get_submission` call to simulate a
    real lab workflow: received -> identifying -> testing -> complete.
    Production code should override this whole class to talk to the
    real backend.
    """

    def __init__(self) -> None:
        self._submissions: dict[str, Submission] = {}
        # call counts per ID drive the deterministic status progression
        self._poll_counts: dict[str, int] = {}

    # -- create -----------------------------------------------------------
    def create(self, **kwargs: Any) -> Submission:
        sid = _new_submission_id()
        while sid in self._submissions:  # essentially never; defensive
            sid = _new_submission_id()
        sub = Submission(
            submission_id=sid,
            created_at=_utcnow_iso(),
            **kwargs,
        )
        self._submissions[sid] = sub
        self._poll_counts[sid] = 0
        return sub

    # -- read -------------------------------------------------------------
    def get(self, submission_id: str) -> Submission | None:
        sub = self._submissions.get(submission_id)
        if sub is None:
            return None
        # Advance through the workflow deterministically. Real backend
        # would obviously read the real status from a database.
        self._poll_counts[submission_id] = self._poll_counts.get(submission_id, 0) + 1
        polls = self._poll_counts[submission_id]
        progression = ["received", "identifying", "testing", "complete"]
        # Move up one step per poll, capped at "complete".
        idx = min(polls - 1, len(progression) - 1)
        new_status = progression[idx]
        if sub.status != new_status:
            sub.status = new_status
        if sub.status == "complete" and not sub.species:
            # Deterministically pick a species + pathogens tested so the
            # caller can demo the full flow. Real backend returns the
            # Walker lab's actual ID + PCR results here.
            species = AZ_TICK_SPECIES[0]  # brown dog tick — modal AZ species
            sub.species = {
                "common_name": species["common_name"],
                "scientific_name": species["scientific_name"],
                "notes": species["notes"],
                "id_method": "morphological (mock)",
            }
            sub.pathogens_tested = [
                {
                    "scientific_name": p["scientific_name"],
                    "disease": p["disease"],
                    "icd10": p["icd10"],
                    "result": "negative",  # mock — Walker lab returns real PCR
                    "method": "PCR (mock)",
                }
                for p in PATHOGENS_SCREENED
            ]
        return sub

    # -- introspection (test helper) --------------------------------------
    def _reset(self) -> None:
        self._submissions.clear()
        self._poll_counts.clear()


class _HttpBackend:
    """Future real backend.

    Kept intentionally thin: the moment the Walker lab (or a partner)
    ships an HTTP submission endpoint, fill in the request bodies and
    response parsing to match. Until then this exists only so the
    facade can flip behaviour based on ``GATTC_BACKEND_URL``.
    """

    def __init__(self, base_url: str, token: str | None = None,
                 timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._http = httpx.AsyncClient(timeout=timeout)

    def _headers(self) -> dict[str, str]:
        h = {"Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def create(self, **kwargs: Any) -> Submission:  # pragma: no cover
        # Stub: the real Walker-lab integration must override this to
        # POST kwargs to whatever endpoint the lab provides and parse
        # the returned submission record into a `Submission`.
        raise NotImplementedError(
            "HTTP backend stub: real Walker-lab API not yet available. "
            "Override _HttpBackend.create() once an endpoint ships."
        )

    def get(self, submission_id: str) -> Submission | None:  # pragma: no cover
        raise NotImplementedError(
            "HTTP backend stub: real Walker-lab API not yet available. "
            "Override _HttpBackend.get() once an endpoint ships."
        )


# ---------------------------------------------------------------------------
# Facade
# ---------------------------------------------------------------------------
class GreatAZTickCheckClient:
    """Mock-by-default client.

    If ``GATTC_BACKEND_URL`` is set, the client routes through the HTTP
    backend stub instead. The stub raises ``NotImplementedError`` until
    a real endpoint exists -- intentional, so a misconfigured deployment
    fails loudly rather than silently looking like the mock is alive.
    """

    def __init__(
        self,
        backend_url: str | None = None,
        api_token: str | None = None,
        label_base: str = DEFAULT_LABEL_BASE,
        status_base: str = DEFAULT_STATUS_BASE,
        turnaround_days: int = DEFAULT_TURNAROUND_DAYS,
    ) -> None:
        url = backend_url if backend_url is not None else DEFAULT_BACKEND_URL
        token = api_token if api_token is not None else DEFAULT_API_TOKEN
        if url:
            self._backend: _MockBackend | _HttpBackend = _HttpBackend(
                base_url=url, token=token
            )
            self.mode = "http"
        else:
            self._backend = _MockBackend()
            self.mode = "mock"
        self.label_base = label_base
        self.status_base = status_base
        self.turnaround_days = turnaround_days

    # -- create -----------------------------------------------------------
    def create_submission(
        self,
        *,
        submitter_email: str,
        submitter_name: str,
        county: str,
        zip_code: str,
        tick_date: str,
        host: str,
        attachment_duration_hours: float | None = None,
        body_location: str | None = None,
        photo_url: str | None = None,
        consent_to_research_use: bool = False,
    ) -> dict[str, Any]:
        if host not in ("human", "pet", "environment"):
            raise ValueError(
                f"host must be one of 'human', 'pet', 'environment'; got {host!r}"
            )
        sub = self._backend.create(
            submitter_email=submitter_email,
            submitter_name=submitter_name,
            county=county,
            zip_code=zip_code,
            tick_date=tick_date,
            attachment_duration_hours=attachment_duration_hours,
            host=host,
            body_location=body_location,
            photo_url=photo_url,
            consent_to_research_use=consent_to_research_use,
        )
        return {
            "submission_id": sub.submission_id,
            "mailing_address": WALKER_LAB_MAILING_ADDRESS,
            "mailing_label_url": _label_url(
                sub.submission_id, fmt="pdf", base=self.label_base
            ),
            "status_url": _status_url(sub.submission_id, base=self.status_base),
            "estimated_turnaround_days": self.turnaround_days,
            "backend_mode": self.mode,
        }

    # -- read -------------------------------------------------------------
    def get_status(self, submission_id: str) -> dict[str, Any]:
        sub = self._backend.get(submission_id)
        if sub is None:
            return {
                "submission_id": submission_id,
                "status": "not_found",
                "status_url": _status_url(submission_id, base=self.status_base),
                "backend_mode": self.mode,
            }
        out: dict[str, Any] = {
            "submission_id": sub.submission_id,
            "status": sub.status,
            "created_at": sub.created_at,
            "status_url": _status_url(sub.submission_id, base=self.status_base),
            "backend_mode": self.mode,
        }
        if sub.species:
            out["species"] = sub.species
        if sub.pathogens_tested:
            out["pathogens_tested"] = sub.pathogens_tested
        return out

    # -- helpers ----------------------------------------------------------
    def mailing_label(self, submission_id: str, fmt: str = "pdf") -> dict[str, Any]:
        return {
            "submission_id": submission_id,
            "format": fmt.lower(),
            "url": _label_url(submission_id, fmt=fmt, base=self.label_base),
            "mailing_address": WALKER_LAB_MAILING_ADDRESS,
            "backend_mode": self.mode,
        }

    def species_guess(
        self,
        photo_url: str,
        lat: float | None = None,
        lon: float | None = None,
    ) -> dict[str, Any]:
        """Mock species identification.

        Returns a single best-guess species plus the full short-list of
        AZ-relevant ticks so the caller can present alternatives. The
        ``verify_with_lab: true`` flag is the contract that says "do
        not act on this as a definitive ID; mail the tick in".
        """
        # Deterministic pick (brown dog tick) keeps tests stable. A
        # real model would consult the photo and the lat/lon.
        primary = AZ_TICK_SPECIES[0]
        return {
            "photo_url": photo_url,
            "lat": lat,
            "lon": lon,
            "best_guess": {
                "common_name": primary["common_name"],
                "scientific_name": primary["scientific_name"],
                "confidence": 0.55,
                "notes": primary["notes"],
            },
            "alternatives": [
                {
                    "common_name": s["common_name"],
                    "scientific_name": s["scientific_name"],
                    "notes": s["notes"],
                }
                for s in AZ_TICK_SPECIES[1:]
            ],
            "verify_with_lab": True,
            "lab_contact": WALKER_LAB_MAILING_ADDRESS,
            "backend_mode": self.mode,
        }
