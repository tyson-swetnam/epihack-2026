"""FastAPI dependency wiring — current user, claim token, orchestrator handle.

The auth dependency validates a Supabase-issued JWT against
Supabase's published JWKS endpoint. Both real validation and a
``ONEHEALTH_AUTH_MOCK=1`` shortcut for local dev are supported; the
real path is the default in production.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Optional

import httpx
import jwt
from fastapi import Depends, Header, HTTPException, status

# ---------------------------------------------------------------------------
# Authenticated user dependency
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuthedUser:
    """Minimum identity surface the API endpoints need.

    Populated by ``require_user`` from the Supabase JWT claims; pass
    it as a dependency on any endpoint that needs to know who is
    calling.
    """

    user_id: str
    email: Optional[str] = None
    provider: Optional[str] = None


_jwks_cache: dict[str, object] = {"keys": None, "fetched_at": 0.0}
_JWKS_TTL_SECONDS = 60 * 60  # 1 hour; Supabase rotates infrequently


def _supabase_jwks_url() -> str:
    base = os.environ.get("SUPABASE_URL")
    if not base:
        raise RuntimeError("SUPABASE_URL is not configured")
    return base.rstrip("/") + "/auth/v1/jwks"


def _load_jwks() -> dict[str, object]:
    now = time.time()
    cached_keys = _jwks_cache["keys"]
    fetched_at = _jwks_cache["fetched_at"]
    assert isinstance(fetched_at, float)
    if cached_keys is not None and now - fetched_at < _JWKS_TTL_SECONDS:
        return cached_keys  # type: ignore[return-value]
    res = httpx.get(_supabase_jwks_url(), timeout=5.0)
    res.raise_for_status()
    keys = res.json()
    _jwks_cache["keys"] = keys
    _jwks_cache["fetched_at"] = now
    return keys


def _decode_token(token: str) -> dict:
    if os.environ.get("ONEHEALTH_AUTH_MOCK") == "1":
        # Local-dev shortcut: trust the JWT without signature validation.
        return jwt.decode(token, options={"verify_signature": False})
    jwks = _load_jwks()
    signing_key = jwt.PyJWKClient(_supabase_jwks_url()).get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256", "ES256"],
        audience="authenticated",
        options={"require": ["exp", "sub"]},
    )


def require_user(
    authorization: Optional[str] = Header(default=None),
) -> AuthedUser:
    """FastAPI dependency: extract + validate the bearer JWT."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Missing bearer token."},
        )
    token = authorization.split(" ", 1)[1]
    try:
        claims = _decode_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "jwt_expired", "message": "Session expired."},
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "jwt_invalid", "message": str(exc)},
        ) from exc
    sub = claims.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "jwt_invalid", "message": "Missing sub claim."},
        )
    return AuthedUser(
        user_id=str(sub),
        email=claims.get("email"),
        provider=claims.get("app_metadata", {}).get("provider"),
    )


def maybe_user(
    authorization: Optional[str] = Header(default=None),
) -> Optional[AuthedUser]:
    """FastAPI dependency: return the user IF a JWT is present.

    Reports submit endpoint uses this so an authenticated user can
    file an anonymous report (the plan/07 case 3 path); the absence
    of a bearer token is not an error here.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return require_user(authorization=authorization)


# ---------------------------------------------------------------------------
# Claim-token dependency (for anonymous status / profile reads)
# ---------------------------------------------------------------------------


def require_claim_token(
    authorization: Optional[str] = Header(default=None),
) -> str:
    """Parse `Authorization: Claim <token>` for the anonymous read paths."""
    if not authorization or not authorization.lower().startswith("claim "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Missing claim token."},
        )
    return authorization.split(" ", 1)[1]


# ---------------------------------------------------------------------------
# Convenience aliases (mostly for typing on routes)
# ---------------------------------------------------------------------------

CurrentUserDep = Depends(require_user)
MaybeUserDep = Depends(maybe_user)
ClaimTokenDep = Depends(require_claim_token)
