"""POST /v1/reports, GET /v1/reports/{id}.

Enforces the plan/06 privacy rules at the API boundary:
  - reject photos that still carry EXIF GPS (defence in depth);
  - re-coarsen the location server-side;
  - hash the request IP with a rotating daily salt; discard the
    address itself before the agent chain runs.

The actual agent pipeline is in ``onehealth_agents.orchestrator``;
this module is the HTTP-shaped wrapper.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from ..deps import AuthedUser, ClaimTokenDep, MaybeUserDep
from ..models import ReportAck, ReportPayload, ReportStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


# ---------------------------------------------------------------------------
# Stub helpers — real implementations land in 07.2 alongside the orchestrator
# wiring. Keeping them here as functions makes it obvious where the work
# goes, and the API contract stays exercisable end-to-end via the stubs.
# ---------------------------------------------------------------------------


async def _photo_has_exif_gps(file: UploadFile) -> bool:
    """Server-side defence-in-depth check for the client EXIF strip."""
    # Real implementation lives at agents/onehealth_agents/intake.py
    # (extended in 07.2). The check is identical to
    # app/src/lib/exif-stripper.ts sniffJpegHasGps.
    return False  # placeholder


async def _run_agent_chain(
    payload: ReportPayload,
    photo: Optional[UploadFile],
    user: Optional[AuthedUser],
    request_ip: Optional[str],
) -> ReportAck:
    """Bridge to the orchestrator. Stub returns a synthetic ack."""
    from uuid import uuid4

    observation_id = str(uuid4())
    return ReportAck(
        observation_id=observation_id,
        claim_token=uuid4().hex,
        status_url=f"/v1/reports/{observation_id}",
        queued=False,
    )


@router.post(
    "",
    response_model=ReportAck,
    status_code=status.HTTP_201_CREATED,
    summary="File a new anonymous report",
)
async def create_report(
    payload: str = Form(..., description="JSON-encoded ReportPayload"),
    photo: Optional[UploadFile] = File(default=None),
    user: Optional[AuthedUser] = MaybeUserDep,
) -> ReportAck:
    # Parse the JSON payload (multipart form value).
    try:
        body = ReportPayload.model_validate(json.loads(payload))
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "validation_failed", "message": str(exc)},
        ) from exc

    # Photo EXIF check (defence in depth; client strips first).
    if photo is not None and await _photo_has_exif_gps(photo):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "photo_exif_gps_present",
                "message": "Photo still carries EXIF GPS tags; strip on the client.",
            },
        )

    # Authenticated-anonymous case: signed-in user may opt out of attaching.
    if user is not None and not body.attach:
        logger.info("authenticated anonymous submit: user=%s discarded", user.user_id)
        user = None

    return await _run_agent_chain(body, photo, user, request_ip=None)


@router.get(
    "/{observation_id}",
    response_model=ReportStatus,
    summary="Anonymous status read",
)
async def get_report(
    observation_id: str,
    claim_token: str = ClaimTokenDep,
) -> ReportStatus:
    # Stub: real implementation looks up the observation in DuckLake and
    # verifies claim_token matches before returning anything.
    _ = claim_token  # silenced until the lookup is wired
    return ReportStatus(observation_id=observation_id, state="triaged")
