"""HTTP client for the VectorSurv API.

Paths, query-parameter syntax, and authentication flow are taken from
the OpenAPI 3.0 spec at https://api.vectorsurv.org/openapi
(spec version 1.0.44; snapshot in ../openapi/).

Key API conventions:

* **Auth.** HTTP bearer (JWT). `POST /login` with JSON body
  ``{"username": ..., "password": ...}`` returns a token that expires
  after one hour.
* **Filtering.** Mongoose-style operators in the query string, e.g.
  ``query[collection_date][$gte]=2024-05-01`` or
  ``query[agency][$in][0]=55&query[agency][$in][1]=72``. Don't pass
  flat parameters like ``start_date=...``.
* **Pagination.** ``page`` (1-based) and ``pageSize``. If the server
  returns ``MAX_PAYLOAD_EXCEEDED`` (HTTP 500), reduce ``pageSize``.
* **Sort.** ``sort=field`` or ``sort=-field`` (descending).
* **Eager-load related records.** ``populate[]=field1&populate[]=field2``.
* **Tick vs mosquito.** ``/v1/arthropod/collection`` covers
  mosquito + non-tick arthropod collections; tick collections live at
  ``/v1/tick/collection``. Pools have a unified endpoint
  ``/v1/arthropod/pool`` with a ``type=mosquito|tick|nontick`` filter,
  plus a tick-only ``/v1/tick/pool``.
"""

from __future__ import annotations

import os
import time
from typing import Any, Iterable

import httpx

DEFAULT_BASE_URL = os.environ.get(
    "VECTORSURV_BASE_URL", "https://api.vectorsurv.org"
)

# Paths verified against api.vectorsurv.org/openapi v1.0.44.
# All overridable per env var for forward-compatibility.
PATHS = {
    "login":             os.environ.get("VECTORSURV_PATH_LOGIN",             "/login"),
    "version":           os.environ.get("VECTORSURV_PATH_VERSION",           "/version"),
    "agencies":          os.environ.get("VECTORSURV_PATH_AGENCIES",          "/v1/agency"),
    "agency_region":     os.environ.get("VECTORSURV_PATH_AGENCY_REGION",     "/v1/agency-region-intersect"),
    "sites":             os.environ.get("VECTORSURV_PATH_SITES",             "/v1/site"),
    "regions":           os.environ.get("VECTORSURV_PATH_REGIONS",           "/v1/region"),
    "region_types":      os.environ.get("VECTORSURV_PATH_REGION_TYPES",      "/v1/region/type"),
    "arthro_coll":       os.environ.get("VECTORSURV_PATH_ARTHRO_COLLECTION", "/v1/arthropod/collection"),
    "tick_coll":         os.environ.get("VECTORSURV_PATH_TICK_COLLECTION",   "/v1/tick/collection"),
    "pools":             os.environ.get("VECTORSURV_PATH_POOLS",             "/v1/arthropod/pool"),
    "tick_pools":        os.environ.get("VECTORSURV_PATH_TICK_POOLS",        "/v1/tick/pool"),
    "pool_are_positive": os.environ.get("VECTORSURV_PATH_POOL_ARE_POSITIVE", "/v1/arthropod/pool/are-positive"),
    "abundance_flat":    os.environ.get("VECTORSURV_PATH_ABUNDANCE_FLAT",    "/v1/arthropod/abundance/flat"),
    "case_count":        os.environ.get("VECTORSURV_PATH_CASE_COUNT",        "/v1/case-count"),
    "test_target":       os.environ.get("VECTORSURV_PATH_TEST_TARGET",       "/v1/test/target"),
    "test_method":       os.environ.get("VECTORSURV_PATH_TEST_METHOD",       "/v1/test/method"),
    "tick_calc_abund":   os.environ.get("VECTORSURV_PATH_TICK_CALC_ABUND",   "/v1/tick/calculation/abundance"),
}


class VectorSurvAuthError(RuntimeError):
    """Raised when the VectorSurv API rejects credentials or a token."""


# ---------------------------------------------------------------- helpers
def date_range_query(field: str, start: str | None, end: str | None) -> dict[str, Any]:
    """Build Mongoose-style $gte/$lte query parameters for a date field."""
    out: dict[str, Any] = {}
    if start:
        out[f"query[{field}][$gte]"] = start
    if end:
        out[f"query[{field}][$lte]"] = end
    return out


def agency_query(agency_ids: Iterable[int] | None) -> dict[str, Any]:
    """Build ``query[agency]=X`` or ``query[agency][$in][i]=...`` filters."""
    if not agency_ids:
        return {}
    ids = list(agency_ids)
    if len(ids) == 1:
        return {"query[agency]": ids[0]}
    return {f"query[agency][$in][{i}]": v for i, v in enumerate(ids)}


def populate_query(populate: Iterable[str] | None) -> dict[str, Any]:
    if not populate:
        return {}
    return {f"populate[{i}]": v for i, v in enumerate(populate)}


# ------------------------------------------------------------------ client
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
        # 1h token life per spec; refresh 60s early.
        self._token_expires_at: float = 0.0
        self._http = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._http.aclose()

    # ------------------------------------------------------------- auth
    async def _ensure_token(self) -> str:
        if self._token and time.time() < self._token_expires_at:
            return self._token
        if not self.username or not self.password:
            raise VectorSurvAuthError(
                "VECTORSURV_USERNAME and VECTORSURV_PASSWORD must be set."
            )
        resp = await self._http.post(
            f"{self.base_url}{PATHS['login']}",
            json={"username": self.username, "password": self.password},
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
        self._token_expires_at = time.time() + 3600 - 60
        return token

    # ------------------------------------------------------------- http
    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        token = await self._ensure_token()
        resp = await self._http.get(
            f"{self.base_url}{path}",
            params=params or {},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        return resp.json()

    async def _post(self, path: str, json: dict[str, Any] | None = None) -> Any:
        token = await self._ensure_token()
        resp = await self._http.post(
            f"{self.base_url}{path}",
            json=json or {},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        return resp.json()

    # -------------------------------------------------------- discovery
    async def get_version(self) -> Any:
        return await self._get(PATHS["version"])

    async def list_agencies(
        self,
        page: int = 1,
        page_size: int = 100,
        populate: list[str] | None = None,
    ) -> Any:
        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        params.update(populate_query(populate))
        return await self._get(PATHS["agencies"], params=params)

    async def list_regions(
        self,
        page: int = 1,
        page_size: int = 100,
        search: str | None = None,
    ) -> Any:
        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        if search:
            params["search"] = search
        return await self._get(PATHS["regions"], params=params)

    async def agency_region_intersect(
        self, populate_region: bool = True
    ) -> Any:
        """Agencies whose service area intersects each region.

        Useful for finding all VectorSurv agencies reporting from a
        specific state or county (e.g. Arizona, Maricopa).
        """
        params = {"populate": "region"} if populate_region else {}
        return await self._get(PATHS["agency_region"], params=params)

    # ------------------------------------------------------------ sites
    async def list_sites(
        self,
        agency_ids: list[int] | None = None,
        page: int = 1,
        page_size: int = 100,
        populate: list[str] | None = None,
    ) -> Any:
        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        params.update(agency_query(agency_ids))
        params.update(populate_query(populate))
        return await self._get(PATHS["sites"], params=params)

    # ---------------------------------------------------- collections
    async def get_collections(
        self,
        start_date: str,
        end_date: str,
        arthropod: str = "mosquito",
        agency_ids: list[int] | None = None,
        page: int = 1,
        page_size: int = 1000,
        populate: list[str] | None = None,
    ) -> Any:
        """Arthropod or tick collections in a date range.

        ``arthropod="mosquito"`` and ``"nontick"`` hit
        ``/v1/arthropod/collection``; ``"tick"`` hits
        ``/v1/tick/collection``. Dates are filtered as
        ``query[collection_date][$gte]`` / ``[$lte]`` per the spec
        (and ``query[collection_date_start][$gte]`` for tick
        collections, whose date model is start/end rather than a
        single ``collection_date``).
        """
        if arthropod == "tick":
            path = PATHS["tick_coll"]
            params = date_range_query("collection_date_start", start_date, end_date)
        else:
            path = PATHS["arthro_coll"]
            params = date_range_query("collection_date", start_date, end_date)
        params["page"] = page
        params["pageSize"] = page_size
        params.update(agency_query(agency_ids))
        params.update(populate_query(populate))
        return await self._get(path, params=params)

    async def get_collections_flat(
        self,
        agency_ids: list[int] | None = None,
        populate: list[str] | None = None,
    ) -> Any:
        """Pre-flattened arthropod abundance + collection rows.

        Backed by ``GET /v1/arthropod/abundance/flat``. Useful when
        you don't want to walk collection -> arthropod records yourself.
        """
        params: dict[str, Any] = {}
        params.update(agency_query(agency_ids))
        params.update(populate_query(populate))
        return await self._get(PATHS["abundance_flat"], params=params)

    # ----------------------------------------------------------- pools
    async def get_pools(
        self,
        start_date: str,
        end_date: str,
        arthropod: str = "mosquito",
        agency_ids: list[int] | None = None,
        page: int = 1,
        page_size: int = 1000,
        populate: list[str] | None = None,
    ) -> Any:
        """Pooled-test results.

        Hits the unified ``/v1/arthropod/pool`` with ``type=...`` filter;
        ``"tick"`` is acceptable here per spec but a tick-only path is
        also available.
        """
        path = PATHS["pools"]
        params: dict[str, Any] = {
            "type": arthropod,
            "page": page,
            "pageSize": page_size,
        }
        params.update(date_range_query("collection_date", start_date, end_date))
        params.update(agency_query(agency_ids))
        params.update(populate_query(populate))
        return await self._get(path, params=params)

    async def pools_are_positive(
        self,
        pool_ids: list[int],
        pathogen_ids: list[int],
        presumptive: bool = False,
    ) -> Any:
        """Bulk-check which pools have definitive positive results.

        Backed by ``GET /v1/arthropod/pool/are-positive``. Returns
        ``[{pool, pathogenResults: [{pathogen, isPositive}]}]``.
        """
        params: dict[str, Any] = {"presumptive": str(presumptive).lower()}
        for i, p in enumerate(pool_ids):
            params[f"pools[{i}]"] = p
        for i, p in enumerate(pathogen_ids):
            params[f"pathogens[{i}]"] = p
        return await self._get(PATHS["pool_are_positive"], params=params)

    # -------------------------------------------------- case counts
    async def get_case_counts(
        self,
        agency_ids: list[int] | None = None,
        page: int = 1,
        page_size: int = 100,
        search: str | None = None,
    ) -> Any:
        """Human / equine arbovirus case counts by week, month, county."""
        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        params.update(agency_query(agency_ids))
        if search:
            params["search"] = search
        return await self._get(PATHS["case_count"], params=params)

    # -------------------------------------------------- test targets
    async def list_test_targets(
        self, page: int = 1, page_size: int = 200
    ) -> Any:
        """Test targets / pathogens VectorSurv tracks.

        Each row carries ``acronym`` (e.g. ``WNV``), ``vector``
        (``both`` / ``mosquito`` / ``tick``), and ``icd_10``. Useful
        as a reference for the LLM when a user asks about a pathogen.
        """
        return await self._get(
            PATHS["test_target"], params={"page": page, "pageSize": page_size}
        )

    async def list_test_methods(
        self, page: int = 1, page_size: int = 200
    ) -> Any:
        return await self._get(
            PATHS["test_method"], params={"page": page, "pageSize": page_size}
        )

    # -------------------------------- server-side abundance calc (tick)
    async def tick_calculate_abundance(self, payload: dict[str, Any]) -> Any:
        """Create a tick abundance calculation job. Returns ``{id: ...}``.

        The full payload shape is documented in the OpenAPI spec under
        ``POST /v1/tick/calculation/abundance``. Poll
        ``GET /v1/tick/calculation/abundance/{id}`` for results.
        """
        return await self._post(PATHS["tick_calc_abund"], json=payload)

    async def tick_calculation_result(self, job_id: str) -> Any:
        return await self._get(f"{PATHS['tick_calc_abund']}/{job_id}")
