"""GET/PATCH/DELETE /v1/auth/me, POST /v1/auth/sign-out, POST /v1/auth/claim.

Account endpoints on top of Supabase Auth. The OAuth dance (Google,
Facebook, Apple) and email/password flows are all client-side via
the Supabase JS SDK; this module covers only the surface that *our*
backend serves.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, status

from ..deps import AuthedUser, CurrentUserDep
from ..models import AccountProfile, ClaimAttachRequest, CurrentUser

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get(
    "/me",
    response_model=CurrentUser,
    summary="Return the current user and their profile",
)
async def get_me(user: AuthedUser = CurrentUserDep) -> CurrentUser:
    # Stub: real implementation reads the public.profile row joined
    # against auth.users. Until that's wired we synthesise a minimal
    # CurrentUser from the JWT claims so the React app's session
    # check can resolve end-to-end.
    return CurrentUser(
        user_id=user.user_id,
        email=user.email,
        email_verified=True,
        provider=user.provider,  # type: ignore[arg-type]
        created_at=datetime.now(timezone.utc),
        profile=AccountProfile(),
    )


@router.patch(
    "/me",
    response_model=CurrentUser,
    summary="Update the authenticated user's profile",
)
async def update_me(
    profile: AccountProfile,
    user: AuthedUser = CurrentUserDep,
) -> CurrentUser:
    # Stub: real implementation upserts public.profile and returns the
    # joined row.
    return CurrentUser(
        user_id=user.user_id,
        email=user.email,
        email_verified=True,
        provider=user.provider,  # type: ignore[arg-type]
        created_at=datetime.now(timezone.utc),
        profile=profile,
    )


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Right to erasure",
)
async def delete_me(user: AuthedUser = CurrentUserDep) -> None:
    # Stub: real implementation
    #   1) UPDATE public.observation SET user_id = NULL WHERE user_id = $1;
    #   2) DELETE FROM auth.users WHERE id = $1;  (CASCADE drops profile)
    #   3) write a privacy-audit row.
    _ = user
    return None


@router.post(
    "/sign-out",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Record a sign-out event",
)
async def sign_out(user: AuthedUser = CurrentUserDep) -> None:
    # Stub: write to the audit log. The client clears its session via
    # the Supabase JS SDK before/after this call.
    _ = user
    return None


@router.post(
    "/claim",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Attach an anonymous report to the current account",
)
async def claim_report(
    req: ClaimAttachRequest,
    user: AuthedUser = CurrentUserDep,
) -> None:
    # Stub: real implementation looks up the observation by claim_token,
    # verifies it isn't already attached to a different user, then
    #   UPDATE public.observation SET user_id = $1 WHERE id = $2.
    _ = req, user
    return None
