"""HTTP client + offline fallback for the iNaturalist public API.

The iNaturalist API documentation lives at
https://api.inaturalist.org/v1/docs/. Read-only endpoints are
unauthenticated, but every client MUST send a meaningful
``User-Agent`` header (see
https://www.inaturalist.org/pages/api+recommended+practices) -- the
server refuses to start if ``INAT_USER_AGENT`` is unset.

Design choices baked into this client:

* **Async ``httpx.AsyncClient`` with 30s timeout**, matching the rest
  of the EpiHack MCP servers.
* **Honor ``Retry-After`` on 429.** iNat returns 429 when an IP burns
  through its rate-limit budget; the client sleeps the recommended
  interval (capped at 60s) and retries once.
* **Mock-by-default fallback.** Set ``INAT_OFFLINE=1`` to bypass the
  network entirely. On any ``httpx.ConnectError`` / ``ReadError``
  the client also transparently falls back to the canned dataset so
  the build sandbox can run tests without a network connection.
* **Bounding-box + radius filtering** are computed in Python on top
  of either the live API response *or* the canned rows -- so the
  same code path covers both.

All paths, place IDs, and taxon IDs are env-overridable. Defaults
verified against api.inaturalist.org (see ``canned_data.py``).
"""

from __future__ import annotations

import asyncio
import math
import os
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable

import httpx

from . import canned_data as cd


# ---------------------------------------------------------------------------
# Env-driven constants.
# ---------------------------------------------------------------------------
DEFAULT_BASE_URL: str = os.environ.get(
    "INAT_BASE_URL", "https://api.inaturalist.org/v1"
).rstrip("/")

PATHS: dict[str, str] = {
    "observations":       os.environ.get("INAT_PATH_OBSERVATIONS",       "/observations"),
    "taxa":               os.environ.get("INAT_PATH_TAXA",               "/taxa"),
    "taxa_autocomplete":  os.environ.get("INAT_PATH_TAXA_AUTOCOMPLETE",  "/taxa/autocomplete"),
    "places":             os.environ.get("INAT_PATH_PLACES",             "/places"),
}


def _offline_mode_requested() -> bool:
    return os.environ.get("INAT_OFFLINE", "").lower() in {"1", "true", "yes", "on"}


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class INatUserAgentMissing(RuntimeError):
    """Raised when no INAT_USER_AGENT is configured."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_EARTH_KM: float = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two WGS84 points in km."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * _EARTH_KM * math.asin(math.sqrt(a))


def radius_to_bbox(lat: float, lon: float, radius_km: float) -> tuple[float, float, float, float]:
    """Approximate bounding box for a (lat, lon, radius_km) query.

    Returns ``(min_lon, min_lat, max_lon, max_lat)``. Uses a flat-Earth
    approximation; the caller should still apply the haversine filter
    on the returned rows for accuracy at the boundary.
    """
    dlat = radius_km / 111.32  # ~km per degree latitude
    cos_lat = max(math.cos(math.radians(lat)), 1e-6)
    dlon = radius_km / (111.32 * cos_lat)
    return (lon - dlon, lat - dlat, lon + dlon, lat + dlat)


def _resolve_taxon_arg(taxon: str | int | None) -> int | None:
    """Map ``taxon='ticks' | '47119' | 47119`` to a numeric taxon ID.

    Returns ``None`` if ``taxon`` is None / blank; raises ``ValueError``
    if the string is neither a known keyword nor a parseable integer.
    """
    if taxon is None or taxon == "":
        return None
    if isinstance(taxon, int):
        return taxon
    raw = str(taxon).strip().lower()
    if raw in cd.TAXON_KEYWORDS:
        return cd.TAXON_KEYWORDS[raw]
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(
            f"Unrecognized taxon {taxon!r}: not a known keyword "
            f"({sorted(cd.TAXON_KEYWORDS)!r}) and not a numeric taxon ID."
        ) from exc


def _today_utc() -> date:
    return datetime.now(tz=timezone.utc).date()


def _observed_on_after(days: int) -> str:
    cutoff = _today_utc() - timedelta(days=days)
    return cutoff.isoformat()


def _normalize_live_obs(row: dict[str, Any]) -> dict[str, Any]:
    """Map a live iNaturalist /observations row into the project schema."""
    taxon = row.get("taxon") or {}
    user = row.get("user") or {}
    geo = row.get("geojson") or {}
    coords = geo.get("coordinates") or [None, None]
    photos = row.get("photos") or row.get("observation_photos") or []
    photo_url: str | None = None
    if photos:
        first = photos[0] if isinstance(photos[0], dict) else (photos[0] or {})
        photo_url = first.get("url") or (first.get("photo") or {}).get("url")
    return {
        "observation_id": row.get("id"),
        "observed_on": row.get("observed_on") or row.get("observed_on_details", {}).get("date"),
        "lat": row.get("latitude") or coords[1],
        "lon": row.get("longitude") or coords[0],
        "geoprivacy": row.get("geoprivacy"),
        "taxon_id": taxon.get("id"),
        "taxon_name": taxon.get("name"),
        "scientific_name": taxon.get("name"),
        "user_login": user.get("login"),
        "photo_url": photo_url,
        "place_guess": row.get("place_guess"),
        "quality_grade": row.get("quality_grade"),
        "identifications_count": row.get("identifications_count"),
        "comments_count": row.get("comments_count"),
        "url": f"https://www.inaturalist.org/observations/{row.get('id')}",
    }


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------
class INaturalistClient:
    """Async iNaturalist client with offline fallback."""

    def __init__(
        self,
        user_agent: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        offline: bool | None = None,
    ) -> None:
        ua = user_agent if user_agent is not None else os.environ.get("INAT_USER_AGENT")
        if not ua:
            raise INatUserAgentMissing(
                "INAT_USER_AGENT must be set. The iNaturalist API requires "
                "every client to identify itself with a meaningful "
                "User-Agent header. Example: "
                "'epihack-az-2026/0.1 (contact: ops@example.org)'."
            )
        self.user_agent = ua
        self.base_url = base_url.rstrip("/")
        self.offline = _offline_mode_requested() if offline is None else offline
        self._http: httpx.AsyncClient | None = None
        if not self.offline:
            self._http = httpx.AsyncClient(
                timeout=timeout,
                headers={
                    "User-Agent": ua,
                    "Accept": "application/json",
                },
            )

    async def aclose(self) -> None:
        if self._http is not None:
            await self._http.aclose()

    # -------------------------------------------------------------------- http
    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any] | None:
        """GET ``path`` with one retry on 429 + transparent offline fallback.

        Returns ``None`` if the client is in offline mode or the network
        failed -- callers then fall back to the canned dataset.
        """
        if self.offline or self._http is None:
            return None
        url = f"{self.base_url}{path}"
        try:
            resp = await self._http.get(url, params=params)
            if resp.status_code == 429:
                # Honor Retry-After header (RFC 7231); cap the wait.
                raw = resp.headers.get("Retry-After", "1")
                try:
                    wait_s = min(float(raw), 60.0)
                except ValueError:
                    wait_s = 1.0
                await asyncio.sleep(wait_s)
                resp = await self._http.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
        except (httpx.ConnectError, httpx.ReadError, httpx.ConnectTimeout):
            # Network unreachable in the build sandbox -- fall back to
            # the canned dataset silently. The tool layer will mark
            # the response with ``source: "canned"``.
            return None

    # -------------------------------------------------------- observations
    async def observations_bbox(
        self,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        taxon: str | int | None = "ticks",
        days: int = 90,
        quality_grade: str = "research",
        limit: int = 200,
    ) -> dict[str, Any]:
        """Public observations inside a bounding box."""
        taxon_id = _resolve_taxon_arg(taxon)
        d1 = _observed_on_after(days)
        params: dict[str, Any] = {
            "nelat": max_lat,
            "nelng": max_lon,
            "swlat": min_lat,
            "swlng": min_lon,
            "d1": d1,
            "per_page": min(max(limit, 1), 200),
            "order_by": "observed_on",
            "order": "desc",
        }
        if taxon_id is not None:
            params["taxon_id"] = taxon_id
        if quality_grade and quality_grade != "any":
            params["quality_grade"] = quality_grade

        body = await self._get(PATHS["observations"], params)
        if body is not None and isinstance(body.get("results"), list):
            rows = [_normalize_live_obs(r) for r in body["results"][:limit]]
            return {"source": "live", "total": body.get("total_results", len(rows)), "results": rows}

        # Offline / fallback path
        rows = self._canned_bbox_filter(
            min_lon=min_lon, min_lat=min_lat,
            max_lon=max_lon, max_lat=max_lat,
            taxon_id=taxon_id,
            days=days,
            quality_grade=quality_grade,
            limit=limit,
        )
        return {"source": "canned", "total": len(rows), "results": rows}

    async def observations_near(
        self,
        lat: float,
        lon: float,
        radius_km: float = 10.0,
        taxon: str | int | None = "ticks",
        days: int = 90,
        quality_grade: str = "research",
        limit: int = 200,
    ) -> dict[str, Any]:
        """Observations within ``radius_km`` of ``(lat, lon)``."""
        min_lon, min_lat, max_lon, max_lat = radius_to_bbox(lat, lon, radius_km)
        out = await self.observations_bbox(
            min_lon=min_lon, min_lat=min_lat,
            max_lon=max_lon, max_lat=max_lat,
            taxon=taxon,
            days=days,
            quality_grade=quality_grade,
            limit=limit,
        )
        filtered = []
        for r in out["results"]:
            if r.get("lat") is None or r.get("lon") is None:
                continue
            d = haversine_km(lat, lon, r["lat"], r["lon"])
            if d <= radius_km:
                r2 = dict(r)
                r2["distance_km"] = round(d, 3)
                filtered.append(r2)
        filtered.sort(key=lambda r: r.get("distance_km", float("inf")))
        out["results"] = filtered[:limit]
        out["total"] = len(filtered)
        out["center"] = {"lat": lat, "lon": lon, "radius_km": radius_km}
        return out

    async def observations_by_taxon(
        self,
        taxon_id: int,
        place_id: int | None = None,
        days: int = 365,
        quality_grade: str = "research",
        limit: int = 200,
    ) -> dict[str, Any]:
        """Observations of a specific taxon in a place (default: AZ = 53)."""
        place_id = cd.AZ_PLACE_ID if place_id is None else place_id
        params: dict[str, Any] = {
            "taxon_id": taxon_id,
            "place_id": place_id,
            "d1": _observed_on_after(days),
            "per_page": min(max(limit, 1), 200),
            "order_by": "observed_on",
            "order": "desc",
        }
        if quality_grade and quality_grade != "any":
            params["quality_grade"] = quality_grade

        body = await self._get(PATHS["observations"], params)
        if body is not None and isinstance(body.get("results"), list):
            rows = [_normalize_live_obs(r) for r in body["results"][:limit]]
            return {
                "source": "live",
                "total": body.get("total_results", len(rows)),
                "place_id": place_id,
                "taxon_id": taxon_id,
                "results": rows,
            }

        # Offline fallback: canned data is all AZ, so place_id filter
        # is a no-op when place_id matches AZ_PLACE_ID; otherwise return
        # empty (we don't pretend to know other places).
        if place_id != cd.AZ_PLACE_ID:
            return {
                "source": "canned",
                "total": 0,
                "place_id": place_id,
                "taxon_id": taxon_id,
                "results": [],
                "note": (
                    "Canned dataset only covers Arizona "
                    f"(place_id={cd.AZ_PLACE_ID}); requested place_id "
                    f"{place_id} returns empty."
                ),
            }
        rows = self._canned_taxon_filter(
            taxon_id=taxon_id,
            days=days,
            quality_grade=quality_grade,
            limit=limit,
        )
        return {
            "source": "canned",
            "total": len(rows),
            "place_id": place_id,
            "taxon_id": taxon_id,
            "results": rows,
        }

    # ------------------------------------------------------------------ taxa
    async def taxon_lookup(self, name_or_id: str | int) -> dict[str, Any]:
        """Resolve a name (e.g. 'deer mouse') or numeric ID to a taxon record."""
        # Numeric -> GET /taxa/{id}
        as_int: int | None = None
        if isinstance(name_or_id, int):
            as_int = name_or_id
        else:
            s = str(name_or_id).strip()
            if s.isdigit():
                as_int = int(s)

        if as_int is not None:
            body = await self._get(f"{PATHS['taxa']}/{as_int}", {})
            if body is not None and isinstance(body.get("results"), list) and body["results"]:
                return {"source": "live", "results": body["results"]}
            # canned fallback
            match = [t for t in cd.TAXON_REFERENCE if t["id"] == as_int]
            return {"source": "canned", "results": match}

        # String -> /taxa/autocomplete
        q = str(name_or_id).strip()
        body = await self._get(PATHS["taxa_autocomplete"], {"q": q, "per_page": 10})
        if body is not None and isinstance(body.get("results"), list) and body["results"]:
            return {"source": "live", "results": body["results"]}

        # canned fallback -- alias / substring search
        ql = q.lower()
        match = [
            t for t in cd.TAXON_REFERENCE
            if any(ql == a or ql in a for a in t.get("aliases", []))
            or ql in t["name"].lower()
            or ql in (t.get("preferred_common_name") or "").lower()
        ]
        return {"source": "canned", "results": match}

    # ----------------------------------------------------------- summaries
    async def species_summary_az(
        self,
        taxon: str | int,
        days: int = 365,
    ) -> dict[str, Any]:
        """Counts by month and by AZ county-equivalent place for a taxon."""
        taxon_id = _resolve_taxon_arg(taxon)
        if taxon_id is None:
            raise ValueError("species_summary_az: `taxon` must resolve to a taxon_id.")
        out = await self.observations_by_taxon(
            taxon_id=taxon_id,
            place_id=cd.AZ_PLACE_ID,
            days=days,
            quality_grade="research",
            limit=500,
        )
        by_month: dict[str, int] = defaultdict(int)
        by_county: dict[str, int] = defaultdict(int)
        for r in out["results"]:
            d = r.get("observed_on") or ""
            if d and len(d) >= 7:
                by_month[d[:7]] += 1
            pg = r.get("place_guess") or ""
            county = _county_from_place_guess(pg)
            if county:
                by_county[county] += 1
        return {
            "source": out.get("source"),
            "place_id": cd.AZ_PLACE_ID,
            "taxon_id": taxon_id,
            "days": days,
            "total": out.get("total"),
            "by_month": dict(sorted(by_month.items())),
            "by_county": dict(
                sorted(by_county.items(), key=lambda kv: kv[1], reverse=True)
            ),
        }

    # --------------------------------------------------- canned-data helpers
    def _canned_bbox_filter(
        self,
        *,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        taxon_id: int | None,
        days: int,
        quality_grade: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        cutoff = _observed_on_after(days)
        ancestor_lookup = {t["id"]: set(t.get("ancestor_ids", [])) | {t["id"]} for t in cd.TAXON_REFERENCE}
        out: list[dict[str, Any]] = []
        for row in cd.CANNED_OBSERVATIONS:
            if row["lat"] is None or row["lon"] is None:
                continue
            if not (min_lon <= row["lon"] <= max_lon and min_lat <= row["lat"] <= max_lat):
                continue
            if row["observed_on"] < cutoff:
                continue
            if quality_grade and quality_grade != "any" and row["quality_grade"] != quality_grade:
                continue
            if taxon_id is not None:
                ancestors = ancestor_lookup.get(row["taxon_id"], {row["taxon_id"]})
                if taxon_id != row["taxon_id"] and taxon_id not in ancestors:
                    continue
            out.append(dict(row))
        # newest first
        out.sort(key=lambda r: r["observed_on"], reverse=True)
        return out[:limit]

    def _canned_taxon_filter(
        self,
        *,
        taxon_id: int,
        days: int,
        quality_grade: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        # Whole-AZ filter: ignore bbox, just filter by taxon + days + qg.
        return self._canned_bbox_filter(
            min_lon=-180, min_lat=-90, max_lon=180, max_lat=90,
            taxon_id=taxon_id,
            days=days,
            quality_grade=quality_grade,
            limit=limit,
        )


# ---------------------------------------------------------------------------
# Small private helpers (module-level so tests can import them)
# ---------------------------------------------------------------------------
def _county_from_place_guess(place_guess: str) -> str | None:
    """Extract an AZ county name from an iNaturalist ``place_guess`` string.

    iNat ``place_guess`` strings look like
    ``"Tucson, Pima County, AZ"`` -- find the comma-separated chunk
    that ends with ``"County"``.
    """
    if not place_guess:
        return None
    for chunk in (c.strip() for c in place_guess.split(",")):
        if chunk.endswith("County"):
            return chunk
    return None
