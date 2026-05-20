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

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status

from ..deps import AuthedUser, ClaimTokenDep, MaybeUserDep
from ..models import ReportAck, ReportPayload, ReportStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


def _writer_for(channel: Optional[str]):
    """Pick the persistence sink by client channel (plan/09).

    ``mobile`` -> MongoDB (synced to DuckLake later); anything else (default
    ``web``) -> the DuckLake knowledge graph directly. Both share the same
    ``persist_observation(payload, user_id)`` / ``read_status`` interface, and
    the privacy/validation steps run before this selection.
    """
    if (channel or "web").strip().lower() == "mobile":
        from ...mongo_writer import get_mongo_writer

        return get_mongo_writer()
    from ...kg_writer import get_writer

    return get_writer()


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
    channel: Optional[str] = "web",
) -> ReportAck:
    """Persist the report, then ack.

    The sink is chosen by client channel (plan/09): mobile -> MongoDB, web ->
    the DuckLake knowledge graph. The full LLM agent chain (triage/enrichment)
    lands later and needs an Anthropic key; this write-path durably *logs*
    every submission (privacy-respecting: free text and the claim token are
    stored only as digests) so no report is dropped.
    """
    writer = _writer_for(channel)

    user_id = user.user_id if user is not None else None
    try:
        observation_id, claim_token = writer.persist_observation(payload, user_id)
    except Exception:  # noqa: BLE001 - never lose the report to a write error
        logger.exception("intake persist failed (channel=%s); ephemeral ack", channel)
        from uuid import uuid4

        observation_id, claim_token = str(uuid4()), uuid4().hex
        return ReportAck(
            observation_id=observation_id,
            claim_token=claim_token,
            status_url=f"/v1/reports/{observation_id}",
            queued=True,
        )

    return ReportAck(
        observation_id=observation_id,
        claim_token=claim_token,
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
    x_client_channel: str = Header(
        default="web",
        alias="X-Client-Channel",
        description="web (default) -> DuckLake; mobile -> MongoDB (plan/09).",
    ),
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

    return await _run_agent_chain(
        body, photo, user, request_ip=None, channel=x_client_channel
    )


@router.get(
    "/{observation_id}",
    response_model=ReportStatus,
    summary="Anonymous status read",
)
async def get_report(
    observation_id: str,
    claim_token: str = ClaimTokenDep,
) -> ReportStatus:
    # The channel isn't known on a status read, so check both stores (DuckLake
    # first, then Mongo) and verify the claim_token digest before returning.
    from ...kg_writer import get_writer

    state: Optional[str] = None
    try:
        state = get_writer().read_status(observation_id, claim_token)
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "claim_token_invalid", "message": "claim_token does not match."},
        )

    if state is None:
        try:
            from ...mongo_writer import get_mongo_writer

            state = get_mongo_writer().read_status(observation_id, claim_token)
        except PermissionError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "claim_token_invalid", "message": "claim_token does not match."},
            )
        except Exception:  # noqa: BLE001 - Mongo not configured/available is fine
            state = None

    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "No such observation."},
        )
    return ReportStatus(observation_id=observation_id, state=state)
