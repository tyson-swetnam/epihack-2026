"""HTTP client for the VectorSurv API.

Endpoints inferred from the public R wrapper (`vectorsurvR`,
UCD-DART) and the published authentication docs at
https://docs.api.vectorsurv.org/. The token expires after one hour,
so the client refreshes it lazily.
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

DEFAULT_BASE_URL = os.environ.get(
    "VECTORSURV_BASE_URL", "https://api.vectorsurv.org"
)

# Endpoint paths are inferred from the public vectorsurvR R package and
# search-result snippets citing docs.api.vectorsurv.org; they are *not*
# verified against the live Swagger at https://api.vectorsurv.org/
# because this build environment can't reach that host. Override any
# path via the corresponding env var if the Swagger spec disagrees.
PATHS = {
    "login":       os.environ.get("VECTORSURV_PATH_LOGIN",       "/login"),
    "agencies":    os.environ.get("VECTORSURV_PATH_AGENCIES",    "/agency"),
    "sites":       os.environ.get("VECTORSURV_PATH_SITES",       "/v1/site/"),
    "collections": os.environ.get("VECTORSURV_PATH_COLLECTIONS", "/v1/arthropod/collection"),
    "pools":       os.environ.get("VECTORSURV_PATH_POOLS",       "/v1/arthropod/pool"),
}


class VectorSurvAuthError(RuntimeError):
    """Raised when the VectorSurv API rejects credentials or a token."""


class VectorSurvClient:
    """Thin async client for the VectorSurv REST API."""

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        self.username = username or os.environ.get("VECTORSURV_USERNAME")
        self.password = password or os.environ.get("VECTORSURV_PASSWORD")
        self.base_url = base_url.rstrip("/")
        self._token: str | None = None
        # 1h - 60s safety margin
        self._token_expires_at: float = 0.0
        self._http = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._http.aclose()

    # ------------------------------------------------------------------ auth
    async def _ensure_token(self) -> str:
        if self._token and time.time() < self._token_expires_at:
            return self._token
        if not self.username or not self.password:
            raise VectorSurvAuthError(
                "VECTORSURV_USERNAME and VECTORSURV_PASSWORD must be set "
                "(or passed to VectorSurvClient)."
            )
        resp = await self._http.post(
            f"{self.base_url}{PATHS['login']}",
            params={"username": self.username, "password": self.password},
        )
        if resp.status_code != 200:
            raise VectorSurvAuthError(
                f"VectorSurv login failed ({resp.status_code}): {resp.text[:200]}"
            )
        body = resp.json()
        token = body.get("token") or body.get("access_token")
        if not token:
            raise VectorSurvAuthError(
                f"VectorSurv login response did not contain a token: {body!r}"
            )
        self._token = token
        # Tokens expire after one hour per the published docs.
        self._token_expires_at = time.time() + 3600 - 60
        return token

    # ------------------------------------------------------------------ http
    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        token = await self._ensure_token()
        resp = await self._http.get(
            f"{self.base_url}{path}",
            params=params or {},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------ tools
    async def list_agencies(self) -> Any:
        """Agencies the authenticated user has access to."""
        return await self._get(PATHS["agencies"])

    async def list_sites(
        self,
        agency_ids: list[int] | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> Any:
        """Trap-location bookmarks."""
        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        if agency_ids:
            params["agency_ids"] = ",".join(str(i) for i in agency_ids)
        return await self._get(PATHS["sites"], params=params)

    async def get_collections(
        self,
        start_date: str,
        end_date: str,
        arthropod: str = "mosquito",
        agency_ids: list[int] | None = None,
        page: int = 1,
        page_size: int = 1000,
    ) -> Any:
        """Arthropod collection records."""
        params: dict[str, Any] = {
            "arthropod": arthropod,
            "start_date": start_date,
            "end_date": end_date,
            "page": page,
            "pageSize": page_size,
        }
        if agency_ids:
            params["agency_ids"] = ",".join(str(i) for i in agency_ids)
        return await self._get(PATHS["collections"], params=params)

    async def get_pools(
        self,
        start_date: str,
        end_date: str,
        arthropod: str = "mosquito",
        agency_ids: list[int] | None = None,
        target_acronym: str | None = None,
        page: int = 1,
        page_size: int = 1000,
    ) -> Any:
        """Pooled-test results with arbovirus targets."""
        params: dict[str, Any] = {
            "arthropod": arthropod,
            "start_date": start_date,
            "end_date": end_date,
            "page": page,
            "pageSize": page_size,
        }
        if agency_ids:
            params["agency_ids"] = ",".join(str(i) for i in agency_ids)
        if target_acronym:
            params["target_acronym"] = target_acronym
        return await self._get(PATHS["pools"], params=params)
