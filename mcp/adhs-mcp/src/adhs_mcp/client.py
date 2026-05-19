"""Client for the ADHS MCP server.

ADHS publishes its arbovirus surveillance summaries and heat-mortality
reports as PDFs, and the Heat Preparedness Network as an ArcGIS
Experience dashboard. There is no public REST API today, so this
client ships with **canned data** sourced from those reports + the
EpiHack knowledge graph (``schema/heat.sql``, ``schema/deep/
standards.sql``, ``heat/04-vulnerable-populations.md``,
``wildlife/resources.md``).

Set ``ADHS_BACKEND_URL`` in the environment to swap the canned data
for a real HTTP backend once one exists. The HTTP path is a thin stub
that raises ``NotImplementedError`` so a misconfigured deployment
fails loudly rather than silently masquerading as the canned data.

The canned constants live in :mod:`adhs_mcp.canned_data` -- contributors
updating numbers from a new ADHS report should only need to touch that
file.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from . import canned_data as CD


# ---------------------------------------------------------------------------
# Environment overrides
# ---------------------------------------------------------------------------
DEFAULT_BACKEND_URL: str | None = os.environ.get("ADHS_BACKEND_URL") or None
DEFAULT_API_TOKEN: str | None = os.environ.get("ADHS_API_TOKEN") or None


# ---------------------------------------------------------------------------
# Filter helpers (shared between mock + future HTTP backend)
# ---------------------------------------------------------------------------
def _norm_county(c: str | None) -> str | None:
    if c is None:
        return None
    return c.strip().lower()


def _norm_pathogen(p: str | None) -> str | None:
    if p is None:
        return None
    return p.strip().upper()


def _filter_cases(
    rows: list[dict[str, Any]],
    *,
    county: str | None,
    surv_year: int | None,
) -> list[dict[str, Any]]:
    """Apply county + year filters to a weekly case-row list.

    Year-matching uses the ISO ``week_of`` prefix (YYYY-MM-DD) rather
    than a separate surv_year column, so callers don't have to keep
    those two fields in sync when updating canned data.
    """
    county_n = _norm_county(county)
    out: list[dict[str, Any]] = []
    for r in rows:
        if county_n is not None and r["county"].lower() != county_n:
            continue
        if surv_year is not None and not r["week_of"].startswith(f"{surv_year}-"):
            continue
        out.append(r)
    return out


def _filter_arbo(
    rows: list[dict[str, Any]],
    *,
    county: str | None,
    surv_year: int | None,
) -> list[dict[str, Any]]:
    county_n = _norm_county(county)
    out: list[dict[str, Any]] = []
    for r in rows:
        if county_n is not None and r["county"].lower() != county_n:
            continue
        if surv_year is not None and r["surv_year"] != surv_year:
            continue
        out.append(r)
    return out


# ---------------------------------------------------------------------------
# Backend implementations
# ---------------------------------------------------------------------------
class _CannedBackend:
    """The default backend -- returns the constants from `canned_data`."""

    def recent_cases(
        self,
        *,
        pathogen: str,
        county: str | None,
        surv_year: int | None,
    ) -> list[dict[str, Any]]:
        key = _norm_pathogen(pathogen)
        if key not in CD.RECENT_CASES:
            return []
        return _filter_cases(
            CD.RECENT_CASES[key], county=county, surv_year=surv_year
        )

    def heat_mortality_summary(
        self, *, year: int | None,
    ) -> list[dict[str, Any]]:
        if year is None:
            return list(CD.HEAT_MORTALITY_SUMMARY)
        return [r for r in CD.HEAT_MORTALITY_SUMMARY if r["year"] == year]

    def arbovirus_surveillance(
        self,
        *,
        surv_year: int | None,
        county: str | None,
    ) -> list[dict[str, Any]]:
        return _filter_arbo(
            CD.ARBOVIRUS_SURVEILLANCE, county=county, surv_year=surv_year,
        )

    def vbzd_program(self) -> dict[str, Any]:
        return dict(CD.VBZD_PROGRAM)

    def heat_preparedness_network(self) -> dict[str, Any]:
        return dict(CD.HEAT_PREPAREDNESS_NETWORK)

    def reportable_conditions(self) -> list[dict[str, Any]]:
        return list(CD.REPORTABLE_CONDITIONS)


class _HttpBackend:
    """Stub HTTP backend -- raises until a real ADHS endpoint exists.

    Kept thin on purpose: the moment ADHS (or a partner) stands up an
    HTTP service, override each method to issue the right request and
    parse the response into the shape the FastMCP tools expect.
    """

    def __init__(
        self, base_url: str, token: str | None = None, timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._http = httpx.AsyncClient(timeout=timeout)

    def _headers(self) -> dict[str, str]:
        h = {"Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _stub(self, method: str) -> None:  # pragma: no cover - defensive
        raise NotImplementedError(
            f"HTTP backend stub: ADHS does not publish a clean REST API "
            f"today. Override _HttpBackend.{method}() once an endpoint "
            f"ships."
        )

    def recent_cases(self, **_: Any) -> list[dict[str, Any]]:  # pragma: no cover
        self._stub("recent_cases")
        return []

    def heat_mortality_summary(self, **_: Any) -> list[dict[str, Any]]:  # pragma: no cover
        self._stub("heat_mortality_summary")
        return []

    def arbovirus_surveillance(self, **_: Any) -> list[dict[str, Any]]:  # pragma: no cover
        self._stub("arbovirus_surveillance")
        return []

    def vbzd_program(self) -> dict[str, Any]:  # pragma: no cover
        self._stub("vbzd_program")
        return {}

    def heat_preparedness_network(self) -> dict[str, Any]:  # pragma: no cover
        self._stub("heat_preparedness_network")
        return {}

    def reportable_conditions(self) -> list[dict[str, Any]]:  # pragma: no cover
        self._stub("reportable_conditions")
        return []


# ---------------------------------------------------------------------------
# Facade
# ---------------------------------------------------------------------------
class ADHSClient:
    """Canned-by-default ADHS client.

    If ``ADHS_BACKEND_URL`` is set, the client routes through
    :class:`_HttpBackend` instead. The stub raises until a real
    endpoint exists -- intentional, so a misconfigured deployment
    fails loudly rather than silently looking like the canned data is
    live.

    All methods return Python ``dict`` / ``list[dict]`` data shaped to
    feed straight into the pydantic models in :mod:`adhs_mcp.server`.
    """

    def __init__(
        self,
        backend_url: str | None = None,
        api_token: str | None = None,
    ) -> None:
        url = backend_url if backend_url is not None else DEFAULT_BACKEND_URL
        token = api_token if api_token is not None else DEFAULT_API_TOKEN
        if url:
            self._backend: _CannedBackend | _HttpBackend = _HttpBackend(
                base_url=url, token=token,
            )
            self.mode = "http"
        else:
            self._backend = _CannedBackend()
            self.mode = "canned"

    # -- recent cases -----------------------------------------------------
    def recent_cases(
        self,
        *,
        pathogen: str,
        county: str | None = None,
        surv_year: int | None = None,
    ) -> list[dict[str, Any]]:
        pn = _norm_pathogen(pathogen)
        if pn not in CD.ACCEPTED_PATHOGENS:
            raise ValueError(
                f"Unknown pathogen {pathogen!r}; expected one of "
                f"{', '.join(CD.ACCEPTED_PATHOGENS)}."
            )
        return self._backend.recent_cases(
            pathogen=pn, county=county, surv_year=surv_year,
        )

    # -- heat mortality ---------------------------------------------------
    def heat_mortality_summary(
        self, *, year: int | None = None,
    ) -> list[dict[str, Any]]:
        return self._backend.heat_mortality_summary(year=year)

    # -- arbovirus surveillance ------------------------------------------
    def arbovirus_surveillance(
        self,
        *,
        surv_year: int | None = None,
        county: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._backend.arbovirus_surveillance(
            surv_year=surv_year, county=county,
        )

    # -- program / network metadata --------------------------------------
    def vbzd_program(self) -> dict[str, Any]:
        return self._backend.vbzd_program()

    def heat_preparedness_network(self) -> dict[str, Any]:
        return self._backend.heat_preparedness_network()

    # -- reportable conditions -------------------------------------------
    def reportable_conditions(self) -> list[dict[str, Any]]:
        return self._backend.reportable_conditions()
