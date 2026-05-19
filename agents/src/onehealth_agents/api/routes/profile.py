"""PATCH /v1/reports/{id}/profile.

Attaches a (per-report) profile to an anonymous observation. Auth
is via the one-time claim token, not the user JWT — this is the
anonymous-first path.
"""

from __future__ import annotations

from fastapi import APIRouter

from ..deps import ClaimTokenDep
from ..models import ProfilePatch, ReportStatus

router = APIRouter(prefix="/reports", tags=["profile"])


@router.patch(
    "/{observation_id}/profile",
    response_model=ReportStatus,
    summary="Attach an optional profile to a previously-submitted report",
)
async def attach_profile(
    observation_id: str,
    profile: ProfilePatch,
    claim_token: str = ClaimTokenDep,
) -> ReportStatus:
    # Stub: real implementation validates the claim token, then updates
    # the observation row with the per-field consent toggles flipped on
    # only for the fields actually supplied.
    _ = profile, claim_token
    return ReportStatus(
        observation_id=observation_id,
        state="triaged",
        profile_attached=True,
    )
