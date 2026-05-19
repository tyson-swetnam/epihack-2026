"""ClusterDetectionAgent -- multi-tier space-time scan calibrated to AZ history.

Replaces the original SaTScan-flavoured stub with a real, calibrated
detector. See ``plan/CLUSTER-CALIBRATION.md`` and
``agents/tests/test_cluster_calibration.py`` for the calibration record.

Design
------

**Tier 1 -- fast deterministic Poisson scan** (runs every cycle).

A sliding spatio-temporal window keyed by:

* ``(vertical, zcta, iso_week)`` for VBD (and any non-heat default).
* ``(vertical, zcta, 2-hour bucket)`` for Heat **during heat season**
  (``HEAT_SEASON_MONTHS`` -- Apr through Oct, inclusive).
* Outside heat season Heat falls back to ``(vertical, zcta, iso_week)``
  so the daily cadence in Plan 03 still applies.

For each bucket we compute:

    O = observed count in the bucket
    E = expected count, computed as the *state-level* baseline rate
        over the trailing 4 weeks, scaled to the bucket's duration.

A state-level baseline is used so a single hot county is not washed out
by a quiet rest-of-state (the failure mode of the 2021 Maricopa WNV
outbreak: county-level signal was strong, statewide signal looked dim
because Maricopa dominates the denominator).

Tier 1 fires when ``O / E >= theta`` **and** ``O >= k``. Defaults:

* VBD:  ``theta=3.0``, ``k=5``
* Heat: ``theta=2.0``, ``k=4``

**Tier 2 -- refined Bayesian scan** (runs only when Tier 1 fires).

Gamma-Poisson conjugate model on the relative risk ``RR``:

    RR ~ Gamma(alpha=2, beta=2)               # prior
    O  | RR ~ Poisson(RR * E)                 # likelihood
    RR | O ~ Gamma(alpha + O, beta + E)        # posterior

The ``Gamma(2, 2)`` prior is weakly informative with mean 1 and variance
0.5 -- expressing "no signal" as the modal expectation while still
allowing the data to dominate even at small ``E``. (A flat / Jeffreys
prior would give too much weight to spurious ratios when ``E`` is tiny,
which is exactly the small-denominator failure mode VectorSurv pool
counts exhibit in early-season ZCTAs.)

We emit a ``ClusterAlert`` only when

    P(RR > 1.5 | data) >= posterior_threshold

with the threshold pinned per vertical:

* VBD:  ``0.95``
* Heat: ``0.90``  (heat is more time-sensitive, lower bar for action)

**Tier A -- single-case high-CFR alert.**
Each pathogen flagged ``single_case_alertable`` in
``schema/deep/cluster_followups.sql`` triggers a ``ClusterAlert`` with
``cluster_kind='single_case'`` and ``rule_tripped='single_case_high_cfr'``
on **any** confirmed observation in the trailing 30-day window. Bypasses
the count and posterior thresholds. Closes ``coconino_plague_2025`` and
provides defence-in-depth for hantavirus / RMSF / rabies / tularaemia.

**Tier B -- county x week Poisson scan.**
The same Tier-1 / Tier-2 logic as the ZCTA-week scan, re-bucketed at
county granularity with looser thresholds (``theta_county=2.0``,
``k_county=3``). Catches small-denominator multi-county clusters that
disperse below the ZCTA-week ``k=5`` floor: hantavirus 2023/2024
(spread across northern AZ counties), WNV 2003 emergence.

**Tier C -- chronic-baseline drift detector.**
For pathogens with documented chronic endemic baselines (currently only
``pathogen.rickettsia_rickettsii`` / RMSF), compare the trailing
12-month rate against the historical 10-year rate. Emit
``cluster_kind='endemic_drift'`` when trailing exceeds
``CHRONIC_DRIFT_MULTIPLIER`` (1.25x) of the historical baseline. The
tribal-data suppression rules in Plan 02 cap detector sensitivity on
reservations even where a true drift exists -- the alert is best-effort,
not exhaustive.

**Travel-import cluster.**
When >= 5 confirmed observations in the trailing 30-day window list
``exposure.history_of_travel=True`` and share a candidate pathogen (the
operational stand-in for "shared destination country" given the current
``ExposureClass`` shape), emit ``cluster_kind='travel_import_cluster'``.
Catches the 2014 chikungunya scatter.

**Audit fields** -- each emitted ``ClusterAlert`` carries the Tier-1
score, the Tier-2 posterior, the baseline-window start/end, the rule
label that tripped (e.g. ``vbd/zcta-week/theta3.0/k5/posterior0.95``),
the pathogen hint, and a back-reference to the closest historical AZ
outbreak (by pathogen + geography, within 5 years and 200 km, otherwise
``None``). The ``cluster_kind`` enum on ``ClusterAlert`` discriminates
which tier fired.

Vertical scoping
----------------

VBD and Heat clusters are *never* merged (per Plan 03). Observations
with ``vertical=both`` are counted into both vertical-scoped scans.
``vertical=neither`` rows are ignored.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from .contracts import ClusterAlert, Observation, Vertical


# ---------------------------------------------------------------------------
# Tunable defaults (pinned per plan/CLUSTER-CALIBRATION.md)
# ---------------------------------------------------------------------------
HEAT_SEASON_MONTHS = frozenset({4, 5, 6, 7, 8, 9, 10})

# Prior on the relative-risk RR for the Gamma-Poisson posterior.
PRIOR_ALPHA = 2.0
PRIOR_BETA = 2.0

# Effect size we care about: "is RR materially above baseline?"
EFFECT_SIZE_RR = 1.5


@dataclass(frozen=True)
class TuningProfile:
    """Per-vertical thresholds. The defaults are the calibrated values."""

    theta: float                       # tier-1 O/E ratio threshold
    k: int                             # tier-1 minimum O
    posterior_threshold: float         # tier-2 P(RR > 1.5) cutoff
    bucket: str                        # "week" or "2h"


VBD_PROFILE = TuningProfile(theta=3.0, k=5, posterior_threshold=0.95, bucket="week")
HEAT_PROFILE = TuningProfile(theta=2.0, k=4, posterior_threshold=0.90, bucket="2h")

# Tier B -- county-level scan: looser thresholds because the geographic
# universe is much smaller (15 AZ counties vs ~400 ZCTAs in scope) and the
# per-cell counts are correspondingly larger, but small-denominator
# pathogens spread across multiple counties stay invisible at ZCTA-week.
VBD_COUNTY_PROFILE = TuningProfile(theta=2.0, k=3, posterior_threshold=0.90, bucket="week")

# Tier A -- single-case high-CFR alert window. Any confirmed observation
# whose pathogen hint is flagged ``single_case_alertable`` in
# ``schema/deep/cluster_followups.sql`` and whose timestamp falls inside
# this trailing window emits a ClusterAlert.
SINGLE_CASE_WINDOW_DAYS = 30

# Tier C -- chronic-baseline drift. Trailing-12-month rate must exceed
# CHRONIC_DRIFT_MULTIPLIER x historical 10-year rate to fire. 1.25x is the
# "noticeably elevated" threshold used in CDC NNDSS endemic-disease alerts.
CHRONIC_DRIFT_MULTIPLIER = 1.25
CHRONIC_TRAILING_DAYS = 365
CHRONIC_HISTORICAL_DAYS = 365 * 10

# Travel-import cluster threshold. The brief specifies >=5 observations
# in a 30-day trailing window sharing a destination; we use shared
# candidate-pathogen as the operational stand-in (no destination field on
# ExposureClass yet).
TRAVEL_CLUSTER_MIN_OBS = 5
TRAVEL_CLUSTER_WINDOW_DAYS = 30


# Alias map: outbreaks.sql + legacy MCP payloads use shorter slugs than the
# canonical schema/deep/pathogens.sql nodes. The detector normalises both
# directions so a Triage candidate slug from either provenance matches the
# single_case_alertable seed.
_PATHOGEN_ALIASES: dict[str, str] = {
    "pathogen.y_pestis":      "pathogen.yersinia_pestis",
    "pathogen.sin_nombre":    "pathogen.snv",
    "pathogen.h5n1":          "pathogen.hpai_h5n1",
}


def _normalise_pathogen(pid: Optional[str]) -> Optional[str]:
    if pid is None:
        return None
    return _PATHOGEN_ALIASES.get(pid, pid)


# Pathogens with a documented chronic endemic baseline in AZ. Tier C
# (chronic-baseline drift) only runs for these.  Historical rate is the
# 10-year empirical mean derived from outbreaks.sql + ADHS surveillance.
CHRONIC_BASELINE_PATHOGENS: dict[str, float] = {
    # RMSF tribal AZ: ~500 cases / 22 yrs through 2024 = ~22.7 cases/yr.
    # Stored as the per-day historical rate so the trailing-vs-historical
    # comparison is unit-consistent. (~22.7 / 365)
    "pathogen.rickettsia_rickettsii": 22.7 / 365.0,
}


# ---------------------------------------------------------------------------
# Historical outbreaks (parsed at import time from schema/deep/outbreaks.sql)
# ---------------------------------------------------------------------------
# Approximate centroid for each AZ county / region we touch. Used for the
# 200-km nearest-neighbour back-reference. Coords pulled from US Census
# county centroids (rounded to 2 dp).
_COUNTY_CENTROIDS: dict[str, tuple[float, float]] = {
    "county.apache":     (35.39, -109.49),
    "county.cochise":    (31.88, -109.75),
    "county.coconino":   (35.84, -111.77),
    "county.gila":       (33.80, -110.81),
    "county.graham":     (32.93, -109.89),
    "county.greenlee":   (33.22, -109.24),
    "county.la_paz":     (33.73, -113.97),
    "county.maricopa":   (33.35, -112.49),
    "county.mohave":     (35.70, -113.75),
    "county.navajo":     (35.40, -110.32),
    "county.pima":       (32.10, -111.78),
    "county.pinal":      (32.90, -111.34),
    "county.santa_cruz": (31.52, -110.85),
    "county.yavapai":    (34.60, -112.55),
    "county.yuma":       (32.77, -113.91),
}

# ZCTAs we know about in tests / scenarios -> approximate centroid + county.
# The test harness uses the synthesised ZCTAs to drive the detector; keeping
# the table local means the unit tests don't depend on a Geo-Enrichment MCP.
_ZCTA_CENTROIDS: dict[str, tuple[float, float, str]] = {
    "85003": (33.45, -112.07, "county.maricopa"),
    "85009": (33.45, -112.13, "county.maricopa"),
    "85033": (33.49, -112.21, "county.maricopa"),
    "85040": (33.39, -112.05, "county.maricopa"),
    "85201": (33.43, -111.84, "county.maricopa"),
    "85301": (33.54, -112.18, "county.maricopa"),
    "85701": (32.21, -110.97, "county.pima"),
    "85718": (32.31, -110.92, "county.pima"),
    "85364": (32.69, -114.62, "county.yuma"),
    "86001": (35.20, -111.65, "county.coconino"),
    "86040": (36.91, -111.46, "county.coconino"),
    "86503": (35.66, -109.05, "county.apache"),
    "86040b": (35.40, -110.32, "county.navajo"),  # placeholder navajo zcta
    "85624": (31.54, -110.76, "county.santa_cruz"),
    "85501": (33.40, -110.78, "county.gila"),
    "85546": (32.83, -109.71, "county.graham"),
}


@dataclass(frozen=True)
class HistoricalOutbreak:
    slug: str
    start: date
    end: Optional[date]            # None for "ongoing"
    pathogen_id: Optional[str]
    counties: tuple[str, ...]
    is_heat: bool


def _parse_partial_date(s: str) -> Optional[date]:
    """Accept 'YYYY', 'YYYY-MM', 'YYYY-MM-DD', or 'ongoing'."""
    s = s.strip()
    if not s or s.lower() == "ongoing":
        return None
    if re.fullmatch(r"\d{4}", s):
        return date(int(s), 1, 1)
    if re.fullmatch(r"\d{4}-\d{2}", s):
        y, m = (int(x) for x in s.split("-"))
        return date(y, m, 1)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return date.fromisoformat(s)
    return None


def _load_historical_outbreaks(sql_path: str | None = None) -> list[HistoricalOutbreak]:
    """Parse ``schema/deep/outbreaks.sql`` for the calibration corpus.

    Best-effort regex extraction -- avoids a DuckDB dependency at runtime
    (which is what plan/05 phase 3 asks for: a calibrated detector that
    can be invoked from any environment that imports the agents package).
    """
    if sql_path is None:
        # The agents package lives at agents/src/onehealth_agents/cluster.py.
        # Repo root is three parents up.
        from pathlib import Path
        sql_path = str(
            Path(__file__).resolve().parents[3] / "schema" / "deep" / "outbreaks.sql"
        )
    try:
        with open(sql_path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return []

    # Slug from the node insert: ('outbreak.<slug>', ...
    slugs: set[str] = set(re.findall(r"'(outbreak\.[a-z0-9_]+)'", text))

    # Properties keyed by slug.
    props: dict[str, dict[str, str]] = defaultdict(dict)
    for m in re.finditer(
        r"\('(outbreak\.[a-z0-9_]+)',\s*'([a-z_]+)',\s*'([^']*)'\)",
        text,
    ):
        slug, key, value = m.group(1), m.group(2), m.group(3)
        props[slug].setdefault(key, value)

    # Edges: outbreak --occurredIn--> county
    counties_by_slug: dict[str, list[str]] = defaultdict(list)
    occurred_block = re.search(
        r"--occurredIn-->.*?ON CONFLICT DO NOTHING;",
        text,
        re.DOTALL,
    )
    if occurred_block:
        for m in re.finditer(
            r"\('(outbreak\.[a-z0-9_]+)',\s*'(county\.[a-z_]+)'\)",
            occurred_block.group(0),
        ):
            counties_by_slug[m.group(1)].append(m.group(2))

    out: list[HistoricalOutbreak] = []
    for slug in sorted(slugs):
        p = props.get(slug, {})
        start = _parse_partial_date(p.get("start_date", ""))
        if start is None:
            continue
        end = _parse_partial_date(p.get("end_date", ""))
        pid = p.get("pathogen_id")
        out.append(
            HistoricalOutbreak(
                slug=slug,
                start=start,
                end=end,
                pathogen_id=pid,
                counties=tuple(counties_by_slug.get(slug, ())),
                is_heat=(pid == "pathogen.heat"),
            )
        )
    return out


HISTORICAL_OUTBREAKS: list[HistoricalOutbreak] = _load_historical_outbreaks()


def _load_single_case_alertable(sql_path: str | None = None) -> frozenset[str]:
    """Parse ``schema/deep/cluster_followups.sql`` for the seed
    ``single_case_alertable`` flag. Returns the set of pathogen.* slugs
    that should fire Tier A on a single confirmed observation.

    Falls back to a hard-coded set (the five pathogens in the committed
    seed) if the SQL file is unavailable -- the detector should never
    silently lose Tier A coverage just because the file moved.
    """
    fallback = frozenset({
        "pathogen.yersinia_pestis",
        "pathogen.snv",
        "pathogen.rabies_lyssavirus",
        "pathogen.francisella_tularensis",
        "pathogen.rickettsia_rickettsii",
    })
    if sql_path is None:
        from pathlib import Path
        candidate = Path(__file__).resolve().parents[3] / "schema" / "deep" / "cluster_followups.sql"
        sql_path = str(candidate)
    try:
        with open(sql_path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return fallback
    found: set[str] = set()
    # Match lines of the form  ('pathogen.<slug>', 'single_case_alertable', 1)
    for m in re.finditer(
        r"\('(pathogen\.[a-z0-9_]+)',\s*'single_case_alertable',\s*1\s*\)",
        text,
    ):
        found.add(m.group(1))
    return frozenset(found) if found else fallback


SINGLE_CASE_ALERTABLE: frozenset[str] = _load_single_case_alertable()


# ---------------------------------------------------------------------------
# Geo / time helpers
# ---------------------------------------------------------------------------
def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance in km between (lat, lon) pairs."""
    lat1, lon1 = a
    lat2, lon2 = b
    r = 6371.0088
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _zcta_to_county(zcta: str) -> Optional[str]:
    entry = _ZCTA_CENTROIDS.get(zcta)
    return entry[2] if entry else None


def _zcta_centroid(zcta: str) -> Optional[tuple[float, float]]:
    entry = _ZCTA_CENTROIDS.get(zcta)
    return (entry[0], entry[1]) if entry else None


def _iso_week_key(ts: datetime) -> str:
    iso = ts.isocalendar()
    return f"{iso.year:04d}-W{iso.week:02d}"


def _two_hour_bucket_key(ts: datetime) -> str:
    bucket_start = ts.replace(minute=0, second=0, microsecond=0)
    bucket_start = bucket_start - timedelta(hours=bucket_start.hour % 2)
    return bucket_start.isoformat()


def _bucket_start_end(key: str, bucket: str) -> tuple[datetime, datetime]:
    if bucket == "week":
        year, week = key.split("-W")
        # ISO week date -> Monday of that week.
        d = date.fromisocalendar(int(year), int(week), 1)
        start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
        return start, start + timedelta(days=7)
    # 2-hour
    start = datetime.fromisoformat(key)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    return start, start + timedelta(hours=2)


def _in_heat_season(ts: datetime) -> bool:
    return ts.month in HEAT_SEASON_MONTHS


# ---------------------------------------------------------------------------
# Gamma-Poisson posterior
# ---------------------------------------------------------------------------
def _regularised_lower_gamma(s: float, x: float, *, max_iter: int = 200, eps: float = 1e-12) -> float:
    """Regularised lower incomplete gamma P(s, x) via series + continued
    fraction, mirroring Numerical Recipes 6.2. Pure-stdlib, no scipy.
    """
    if x <= 0 or s <= 0:
        return 0.0
    log_gamma_s = math.lgamma(s)
    if x < s + 1.0:
        # series
        term = 1.0 / s
        total = term
        for n in range(1, max_iter):
            term *= x / (s + n)
            total += term
            if abs(term) < abs(total) * eps:
                break
        return total * math.exp(-x + s * math.log(x) - log_gamma_s)
    # continued fraction for Q, then P = 1 - Q
    b = x + 1.0 - s
    c = 1.0 / 1e-300
    d = 1.0 / b
    h = d
    for i in range(1, max_iter):
        an = -i * (i - s)
        b += 2.0
        d = an * d + b
        if abs(d) < 1e-300:
            d = 1e-300
        c = b + an / c
        if abs(c) < 1e-300:
            c = 1e-300
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    q = math.exp(-x + s * math.log(x) - log_gamma_s) * h
    return max(0.0, min(1.0, 1.0 - q))


def _posterior_p_rr_gt(threshold: float, observed: int, expected: float,
                       alpha: float = PRIOR_ALPHA, beta: float = PRIOR_BETA) -> float:
    """P(RR > threshold | observed, expected) under Gamma(alpha, beta) prior.

    Posterior: RR | data ~ Gamma(alpha + O, beta + E).
    So P(RR > t) = 1 - F_Gamma(t; alpha + O, beta + E)
                 = 1 - P(alpha + O, (beta + E) * t).
    """
    if expected <= 0:
        # Degenerate; treat as no information.
        return 0.0
    shape = alpha + observed
    rate = beta + expected
    return 1.0 - _regularised_lower_gamma(shape, rate * threshold)


def _poisson_log_likelihood_ratio(observed: int, expected: float) -> float:
    """Kulldorff-style scan statistic ratio for one zone (kept for legacy
    log_likelihood field on ClusterAlert)."""
    if observed == 0 or expected <= 0:
        return 0.0
    return observed * math.log(observed / expected) - (observed - expected)


# ---------------------------------------------------------------------------
# Historical match
# ---------------------------------------------------------------------------
def _closest_historical(
    *,
    pathogen_hint: Optional[str],
    is_heat: bool,
    county_id: Optional[str],
    zcta: Optional[str],
    when: datetime,
    max_years: int = 5,
    max_km: float = 200.0,
) -> Optional[str]:
    """Closest historical AZ outbreak by pathogen+geography. None if no
    candidate matches both the 5-year temporal window and the 200-km
    spatial window."""
    if not HISTORICAL_OUTBREAKS:
        return None

    target_centroid: Optional[tuple[float, float]] = None
    if zcta is not None:
        target_centroid = _zcta_centroid(zcta)
    if target_centroid is None and county_id is not None:
        target_centroid = _COUNTY_CENTROIDS.get(county_id)

    best: Optional[tuple[float, str]] = None
    for ob in HISTORICAL_OUTBREAKS:
        # Pathogen / vertical compatibility filter.
        if is_heat:
            if not ob.is_heat:
                continue
        else:
            if ob.is_heat:
                continue
            if pathogen_hint and ob.pathogen_id and ob.pathogen_id != pathogen_hint:
                continue

        # Temporal proximity (5-year window).
        ob_end = ob.end or ob.start.replace(year=min(ob.start.year + 1, 9999))
        delta_days = min(
            abs((when.date() - ob.start).days),
            abs((when.date() - ob_end).days),
        )
        if delta_days > max_years * 365 + 2:
            continue

        # Spatial proximity (200-km window).
        if target_centroid is None or not ob.counties:
            # Without geometry we can still match if pathogen + temporal align.
            score = float(delta_days)
        else:
            best_km = min(
                _haversine_km(target_centroid, _COUNTY_CENTROIDS[c])
                for c in ob.counties
                if c in _COUNTY_CENTROIDS
            ) if any(c in _COUNTY_CENTROIDS for c in ob.counties) else float("inf")
            if best_km > max_km:
                continue
            score = best_km + delta_days * 0.1

        if best is None or score < best[0]:
            best = (score, ob.slug)
    return best[1] if best else None


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------
class ClusterDetectionAgent:
    """Two-tier deterministic + Bayesian space-time cluster detector."""

    name = "cluster_detection"

    def __init__(
        self,
        *,
        vbd: TuningProfile = VBD_PROFILE,
        heat: TuningProfile = HEAT_PROFILE,
        vbd_county: TuningProfile = VBD_COUNTY_PROFILE,
        baseline_weeks: int = 4,
        prior_alpha: float = PRIOR_ALPHA,
        prior_beta: float = PRIOR_BETA,
        effect_size_rr: float = EFFECT_SIZE_RR,
        single_case_alertable: frozenset[str] | None = None,
        chronic_baseline_pathogens: dict[str, float] | None = None,
        chronic_drift_multiplier: float = CHRONIC_DRIFT_MULTIPLIER,
        travel_cluster_min_obs: int = TRAVEL_CLUSTER_MIN_OBS,
        # Legacy keyword args kept for back-compat with the old stub
        # construction sites (e.g. Orchestrator). They are no-ops now but
        # accepted silently so callers don't break.
        window_days: int | None = None,
        baseline_per_zcta_per_day: float | None = None,
        min_observed: int | None = None,
        llr_threshold: float | None = None,
    ) -> None:
        self.vbd = vbd
        self.heat = heat
        self.vbd_county = vbd_county
        self.baseline_weeks = baseline_weeks
        self.prior_alpha = prior_alpha
        self.prior_beta = prior_beta
        self.effect_size_rr = effect_size_rr
        self.single_case_alertable = (
            SINGLE_CASE_ALERTABLE if single_case_alertable is None else single_case_alertable
        )
        self.chronic_baseline_pathogens = (
            dict(CHRONIC_BASELINE_PATHOGENS) if chronic_baseline_pathogens is None
            else dict(chronic_baseline_pathogens)
        )
        self.chronic_drift_multiplier = chronic_drift_multiplier
        self.travel_cluster_min_obs = travel_cluster_min_obs

    # ------------------------------------------------------------------
    def profile_for(self, vertical: Vertical, now: datetime) -> Optional[TuningProfile]:
        """Pick the right tuning profile for a vertical at time ``now``.

        Heat outside heat season runs weekly (Plan 03 cadence)."""
        if vertical is Vertical.VBD:
            return self.vbd
        if vertical is Vertical.HEAT:
            if _in_heat_season(now):
                return self.heat
            # Off-season: still scan Heat, but at weekly granularity.
            return TuningProfile(
                theta=self.heat.theta,
                k=self.heat.k,
                posterior_threshold=self.heat.posterior_threshold,
                bucket="week",
            )
        return None

    # ------------------------------------------------------------------
    def run(
        self,
        observations: Iterable[Observation],
        now: datetime | None = None,
    ) -> list[ClusterAlert]:
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # Materialise into a list; we iterate multiple times.
        obs_list = list(observations)

        # ----------- split by vertical (VBD vs Heat; "both" counts in both) -
        per_vertical: dict[Vertical, list[Observation]] = {
            Vertical.VBD: [],
            Vertical.HEAT: [],
        }
        for o in obs_list:
            if o.vertical is Vertical.VBD or o.vertical is Vertical.BOTH:
                per_vertical[Vertical.VBD].append(o)
            if o.vertical is Vertical.HEAT or o.vertical is Vertical.BOTH:
                per_vertical[Vertical.HEAT].append(o)

        alerts: list[ClusterAlert] = []
        for vertical, vert_obs in per_vertical.items():
            if not vert_obs:
                continue
            profile = self.profile_for(vertical, now)
            if profile is None:
                continue
            # Spatial ZCTA scan (Tier 1 + Tier 2).
            alerts.extend(self._scan_vertical(vertical, profile, vert_obs, now))
            # Tier B -- county x week Poisson scan. Same Tier-1/Tier-2 logic
            # at coarser geography. Only runs for week-bucket scans; the
            # 2-hour bucket is already as fine-grained as the cadence allows.
            if profile.bucket == "week" and vertical is Vertical.VBD:
                alerts.extend(
                    self._scan_county(vertical, self.vbd_county, vert_obs, now)
                )
            # Tier A -- single-case high-CFR alert.
            alerts.extend(self._scan_single_case(vertical, vert_obs, now))
            # Tier C -- chronic-baseline drift detector.
            alerts.extend(self._scan_chronic_drift(vertical, vert_obs, now))
            # Travel-import cluster detector.
            alerts.extend(self._scan_travel_imports(vertical, vert_obs, now))
        return alerts

    # ------------------------------------------------------------------
    def _scan_vertical(
        self,
        vertical: Vertical,
        profile: TuningProfile,
        observations: list[Observation],
        now: datetime,
    ) -> list[ClusterAlert]:
        # Baseline window = the four weeks **immediately preceding** the
        # scan horizon (NOT overlapping it). This is what keeps a
        # rapidly-unfolding outbreak from polluting its own denominator:
        # the outbreak's reports land in the scan horizon, not in the
        # baseline window.
        scan_horizon = _scan_horizon(profile.bucket)
        scan_start = now - scan_horizon
        baseline_end = scan_start
        baseline_start = baseline_end - timedelta(weeks=self.baseline_weeks)

        # -- Bucket the observations: (zcta, bucket_key) -> [obs] --
        # Every (zcta, bucket) cell whose timestamp falls within the scan
        # horizon is a candidate hot cell. Older observations contribute
        # to the baseline.
        cell_obs: dict[tuple[str, str], list[Observation]] = defaultdict(list)
        # Statewide baseline tallied per ZCTA (so we can compute a
        # leave-one-out rate that drops the candidate's own contribution).
        baseline_by_zcta: dict[str, int] = defaultdict(int)

        for obs in observations:
            ts = _parse_obs_ts(obs.received_at)
            if ts is None:
                continue
            zcta = _obs_zcta(obs)
            if not zcta:
                continue
            if scan_start <= ts <= now:
                key = _bucket_key(ts, profile.bucket)
                cell_obs[(zcta, key)].append(obs)
            elif baseline_start <= ts < baseline_end:
                baseline_by_zcta[zcta] += 1

        if not cell_obs:
            return []

        # -- State-level baseline rate (events per ZCTA per bucket) --
        # "Active" universe = every ZCTA we have seen in either the
        # baseline OR the current window. This gives us a stable
        # denominator across cycles.
        active_zctas = set(baseline_by_zcta) | {z for z, _ in cell_obs}
        n_zctas = max(1, len(active_zctas))
        baseline_window_days = self.baseline_weeks * 7
        if baseline_window_days <= 0:
            return []
        baseline_total = sum(baseline_by_zcta.values())

        if profile.bucket == "week":
            bucket_days = 7.0
        else:
            bucket_days = 2.0 / 24.0

        alerts: list[ClusterAlert] = []
        seen_dupes: set[tuple[str, str]] = set()
        for (zcta, key), obs_in_cell in cell_obs.items():
            observed = len(obs_in_cell)
            if observed < profile.k:
                continue
            # Leave-one-out: subtract the candidate ZCTA's baseline
            # contribution so a chronic hot-spot doesn't anchor its own
            # expectation. ``n_other`` is the remaining ZCTA universe.
            other_total = baseline_total - baseline_by_zcta.get(zcta, 0)
            n_other = max(1, n_zctas - 1)
            rate_per_zcta_per_day = other_total / (n_other * baseline_window_days)
            expected_per_bucket = max(
                rate_per_zcta_per_day * bucket_days,
                _floor_expectation(profile.bucket),
            )
            tier1 = observed / expected_per_bucket
            if tier1 < profile.theta:
                continue
            # Tier 2 -- Gamma-Poisson posterior.
            posterior = _posterior_p_rr_gt(
                self.effect_size_rr,
                observed,
                expected_per_bucket,
                alpha=self.prior_alpha,
                beta=self.prior_beta,
            )
            if posterior < profile.posterior_threshold:
                continue
            if (zcta, key) in seen_dupes:
                continue
            seen_dupes.add((zcta, key))

            bucket_start, bucket_end = _bucket_start_end(key, profile.bucket)
            pathogen_hint = _dominant_pathogen_hint(obs_in_cell)
            county_id = _zcta_to_county(zcta)
            historical = _closest_historical(
                pathogen_hint=pathogen_hint,
                is_heat=(vertical is Vertical.HEAT),
                county_id=county_id,
                zcta=zcta,
                when=bucket_start,
            )
            rule = (
                f"{vertical.value}/zcta-{profile.bucket}/"
                f"theta{profile.theta}/k{profile.k}/"
                f"posterior{profile.posterior_threshold}"
            )
            llr = _poisson_log_likelihood_ratio(observed, expected_per_bucket)
            alerts.append(
                ClusterAlert(
                    vertical=vertical,
                    zcta=zcta,
                    county_id=county_id,
                    observation_ids=[o.observation_id for o in obs_in_cell],
                    window_start=bucket_start.isoformat(),
                    window_end=bucket_end.isoformat(),
                    expected=expected_per_bucket,
                    observed=observed,
                    log_likelihood=llr,
                    tier1_score=tier1,
                    tier2_posterior=posterior,
                    baseline_window_start=baseline_start.isoformat(),
                    baseline_window_end=now.isoformat(),
                    rule_tripped=rule,
                    pathogen_hint=pathogen_hint,
                    historical_match=historical,
                    cluster_kind="spatial",
                )
            )
        return alerts

    # ------------------------------------------------------------------
    # Tier B -- county x week Poisson scan
    # ------------------------------------------------------------------
    def _scan_county(
        self,
        vertical: Vertical,
        profile: TuningProfile,
        observations: list[Observation],
        now: datetime,
    ) -> list[ClusterAlert]:
        """Coarse-grained county x week scan. Catches multi-county clusters
        that disperse below the ZCTA-week ``k=5`` floor (hantavirus 23/24,
        WNV 2003 emergence)."""
        scan_horizon = _scan_horizon(profile.bucket)
        scan_start = now - scan_horizon
        baseline_end = scan_start
        baseline_start = baseline_end - timedelta(weeks=self.baseline_weeks)

        cell_obs: dict[tuple[str, str], list[Observation]] = defaultdict(list)
        baseline_by_county: dict[str, int] = defaultdict(int)

        for obs in observations:
            ts = _parse_obs_ts(obs.received_at)
            if ts is None:
                continue
            zcta = _obs_zcta(obs)
            county = _obs_county(obs) or (_zcta_to_county(zcta) if zcta else None)
            if not county:
                continue
            if scan_start <= ts <= now:
                key = _bucket_key(ts, profile.bucket)
                cell_obs[(county, key)].append(obs)
            elif baseline_start <= ts < baseline_end:
                baseline_by_county[county] += 1

        if not cell_obs:
            return []

        active = set(baseline_by_county) | {c for c, _ in cell_obs}
        n_counties = max(1, len(active))
        baseline_window_days = self.baseline_weeks * 7
        baseline_total = sum(baseline_by_county.values())
        bucket_days = 7.0 if profile.bucket == "week" else (2.0 / 24.0)

        alerts: list[ClusterAlert] = []
        seen: set[tuple[str, str]] = set()
        for (county, key), obs_in_cell in cell_obs.items():
            observed = len(obs_in_cell)
            if observed < profile.k:
                continue
            other_total = baseline_total - baseline_by_county.get(county, 0)
            n_other = max(1, n_counties - 1)
            rate_per_day = other_total / (n_other * baseline_window_days)
            expected = max(
                rate_per_day * bucket_days,
                _floor_expectation(profile.bucket),
            )
            tier1 = observed / expected
            if tier1 < profile.theta:
                continue
            posterior = _posterior_p_rr_gt(
                self.effect_size_rr, observed, expected,
                alpha=self.prior_alpha, beta=self.prior_beta,
            )
            if posterior < profile.posterior_threshold:
                continue
            if (county, key) in seen:
                continue
            seen.add((county, key))
            bucket_start, bucket_end = _bucket_start_end(key, profile.bucket)
            pathogen_hint = _dominant_pathogen_hint(obs_in_cell)
            historical = _closest_historical(
                pathogen_hint=pathogen_hint,
                is_heat=(vertical is Vertical.HEAT),
                county_id=county,
                zcta=None,
                when=bucket_start,
            )
            rule = (
                f"{vertical.value}/county-{profile.bucket}/"
                f"theta{profile.theta}/k{profile.k}/"
                f"posterior{profile.posterior_threshold}"
            )
            llr = _poisson_log_likelihood_ratio(observed, expected)
            alerts.append(
                ClusterAlert(
                    vertical=vertical,
                    zcta=None,
                    county_id=county,
                    observation_ids=[o.observation_id for o in obs_in_cell],
                    window_start=bucket_start.isoformat(),
                    window_end=bucket_end.isoformat(),
                    expected=expected,
                    observed=observed,
                    log_likelihood=llr,
                    tier1_score=tier1,
                    tier2_posterior=posterior,
                    baseline_window_start=baseline_start.isoformat(),
                    baseline_window_end=now.isoformat(),
                    rule_tripped=rule,
                    pathogen_hint=pathogen_hint,
                    historical_match=historical,
                    cluster_kind="spatial",
                )
            )
        return alerts

    # ------------------------------------------------------------------
    # Tier A -- single-case high-CFR alert
    # ------------------------------------------------------------------
    def _scan_single_case(
        self,
        vertical: Vertical,
        observations: list[Observation],
        now: datetime,
    ) -> list[ClusterAlert]:
        """Emit one ClusterAlert per (zcta, pathogen) for any confirmed
        observation in the trailing 30-day window whose pathogen hint is
        flagged ``single_case_alertable``.

        "Confirmed" is interpreted as: the observation has a triage
        decision OR an explicit ``auxiliary.diagnostic_lab`` value (raw
        ``mcp_pull`` payloads from public lab feeds), AND the validation
        agent did not REJECT it.
        """
        if not self.single_case_alertable:
            return []
        window_start = now - timedelta(days=SINGLE_CASE_WINDOW_DAYS)
        alerts: list[ClusterAlert] = []
        seen: set[tuple[str, str]] = set()
        for obs in observations:
            ts = _parse_obs_ts(obs.received_at)
            if ts is None or not (window_start <= ts <= now):
                continue
            if not _is_confirmed(obs):
                continue
            for pid in _candidate_pathogen_ids(obs):
                norm = _normalise_pathogen(pid)
                if norm not in self.single_case_alertable:
                    continue
                zcta = _obs_zcta(obs) or ""
                key = (zcta, norm)
                if key in seen:
                    continue
                seen.add(key)
                county_id = _obs_county(obs) or _zcta_to_county(zcta)
                historical = _closest_historical(
                    pathogen_hint=norm,
                    is_heat=False,
                    county_id=county_id,
                    zcta=zcta or None,
                    when=ts,
                )
                alerts.append(
                    ClusterAlert(
                        vertical=vertical,
                        zcta=zcta or None,
                        county_id=county_id,
                        observation_ids=[obs.observation_id],
                        window_start=ts.isoformat(),
                        window_end=ts.isoformat(),
                        expected=0.0,
                        observed=1,
                        log_likelihood=0.0,
                        tier1_score=None,
                        tier2_posterior=None,
                        baseline_window_start=window_start.isoformat(),
                        baseline_window_end=now.isoformat(),
                        rule_tripped="single_case_high_cfr",
                        pathogen_hint=norm,
                        historical_match=historical,
                        cluster_kind="single_case",
                    )
                )
        return alerts

    # ------------------------------------------------------------------
    # Tier C -- chronic-baseline drift
    # ------------------------------------------------------------------
    def _scan_chronic_drift(
        self,
        vertical: Vertical,
        observations: list[Observation],
        now: datetime,
    ) -> list[ClusterAlert]:
        """Detect raised endemic-pathogen rates against a 10-year baseline.

        Per Plan 02 tribal-data-suppression rules, observations originating
        from tribal lands may be aggregated at the county level or
        suppressed entirely; the detector will under-report on
        reservations. This is the canonical RMSF-tribal limitation and
        is *by design* of the data-sovereignty contract.
        """
        if not self.chronic_baseline_pathogens or vertical is Vertical.HEAT:
            return []
        trailing_start = now - timedelta(days=CHRONIC_TRAILING_DAYS)
        # Count observations per (pathogen, county) in trailing 12 months.
        tally: dict[tuple[str, Optional[str]], list[Observation]] = defaultdict(list)
        for obs in observations:
            ts = _parse_obs_ts(obs.received_at)
            if ts is None or not (trailing_start <= ts <= now):
                continue
            if not _is_confirmed(obs):
                continue
            zcta = _obs_zcta(obs)
            county = _obs_county(obs) or (_zcta_to_county(zcta) if zcta else None)
            for pid in _candidate_pathogen_ids(obs):
                norm = _normalise_pathogen(pid)
                if norm in self.chronic_baseline_pathogens:
                    tally[(norm, county)].append(obs)

        # Roll county-level tallies up to a statewide total so we don't
        # under-count a chronic-disease footprint spread across multiple
        # counties. We emit at the statewide grain (county_id=None) when
        # the rollup exceeds threshold, and at the county grain when a
        # single county does so on its own (the more localised, actionable
        # signal).
        statewide: dict[str, list[Observation]] = defaultdict(list)
        for (pid, _county), obs_list in tally.items():
            statewide[pid].extend(obs_list)

        alerts: list[ClusterAlert] = []
        emitted: set[tuple[str, Optional[str]]] = set()

        def _emit(pid: str, county_id: Optional[str],
                  obs_list: list[Observation]) -> None:
            trailing_count = len(obs_list)
            historical_rate_per_day = self.chronic_baseline_pathogens[pid]
            expected_trailing = historical_rate_per_day * CHRONIC_TRAILING_DAYS
            if expected_trailing <= 0:
                return
            if trailing_count < self.chronic_drift_multiplier * expected_trailing:
                return
            key = (pid, county_id)
            if key in emitted:
                return
            emitted.add(key)
            ts_when = max(_parse_obs_ts(o.received_at) or now for o in obs_list)
            alerts.append(
                ClusterAlert(
                    vertical=vertical,
                    zcta=None,
                    county_id=county_id,
                    observation_ids=[o.observation_id for o in obs_list],
                    window_start=trailing_start.isoformat(),
                    window_end=now.isoformat(),
                    expected=expected_trailing,
                    observed=trailing_count,
                    log_likelihood=_poisson_log_likelihood_ratio(
                        trailing_count, expected_trailing,
                    ),
                    tier1_score=trailing_count / expected_trailing,
                    tier2_posterior=None,
                    baseline_window_start=(
                        now - timedelta(days=CHRONIC_HISTORICAL_DAYS)
                    ).isoformat(),
                    baseline_window_end=trailing_start.isoformat(),
                    rule_tripped=(
                        f"chronic_baseline_drift/x{self.chronic_drift_multiplier}"
                    ),
                    pathogen_hint=pid,
                    historical_match=_closest_historical(
                        pathogen_hint=pid, is_heat=False,
                        county_id=county_id, zcta=None, when=ts_when,
                    ),
                    cluster_kind="endemic_drift",
                )
            )

        for pid, obs_list in statewide.items():
            _emit(pid, None, obs_list)
        for (pid, county), obs_list in tally.items():
            _emit(pid, county, obs_list)
        return alerts

    # ------------------------------------------------------------------
    # Travel-import cluster
    # ------------------------------------------------------------------
    def _scan_travel_imports(
        self,
        vertical: Vertical,
        observations: list[Observation],
        now: datetime,
    ) -> list[ClusterAlert]:
        """When >= ``travel_cluster_min_obs`` confirmed observations in a
        trailing 30-day window list ``exposure.history_of_travel=True`` and
        share a candidate pathogen (operational stand-in for "shared
        destination" given ExposureClass has no destination field yet),
        emit ``cluster_kind='travel_import_cluster'``.
        """
        if vertical is Vertical.HEAT:
            return []
        window_start = now - timedelta(days=TRAVEL_CLUSTER_WINDOW_DAYS)
        by_pathogen: dict[str, list[Observation]] = defaultdict(list)
        for obs in observations:
            ts = _parse_obs_ts(obs.received_at)
            if ts is None or not (window_start <= ts <= now):
                continue
            if not _has_travel_exposure(obs):
                continue
            if not _is_confirmed(obs):
                continue
            for pid in _candidate_pathogen_ids(obs):
                norm = _normalise_pathogen(pid)
                if norm is None:
                    continue
                by_pathogen[norm].append(obs)

        alerts: list[ClusterAlert] = []
        for pid, obs_list in by_pathogen.items():
            if len(obs_list) < self.travel_cluster_min_obs:
                continue
            counties = sorted({
                _obs_county(o) or _zcta_to_county(_obs_zcta(o) or "") or "unknown"
                for o in obs_list
            })
            county_id = counties[0] if len(counties) == 1 else None
            ts_when = max(_parse_obs_ts(o.received_at) or now for o in obs_list)
            historical = _closest_historical(
                pathogen_hint=pid, is_heat=False,
                county_id=county_id, zcta=None, when=ts_when,
            )
            alerts.append(
                ClusterAlert(
                    vertical=vertical,
                    zcta=None,
                    county_id=county_id,
                    observation_ids=[o.observation_id for o in obs_list],
                    window_start=window_start.isoformat(),
                    window_end=now.isoformat(),
                    expected=0.0,
                    observed=len(obs_list),
                    log_likelihood=0.0,
                    tier1_score=None,
                    tier2_posterior=None,
                    baseline_window_start=window_start.isoformat(),
                    baseline_window_end=now.isoformat(),
                    rule_tripped=(
                        f"travel_import_cluster/n>={self.travel_cluster_min_obs}/"
                        f"win{TRAVEL_CLUSTER_WINDOW_DAYS}d"
                    ),
                    pathogen_hint=pid,
                    historical_match=historical,
                    cluster_kind="travel_import_cluster",
                )
            )
        return alerts


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------
def _parse_obs_ts(s: str) -> Optional[datetime]:
    try:
        ts = datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def _obs_zcta(obs: Observation) -> Optional[str]:
    if obs.geo and obs.geo.zcta:
        return obs.geo.zcta
    return obs.dataset.general.postal_code


def _obs_county(obs: Observation) -> Optional[str]:
    if obs.geo and obs.geo.county_id:
        return obs.geo.county_id
    return None


def _candidate_pathogen_ids(obs: Observation) -> list[str]:
    """All candidate pathogen slugs attached to ``obs``.

    Pulls from ``triage.candidate_pathogens`` first (the usual path); also
    surfaces a single inferred ``pathogen.<...>`` slug from
    ``auxiliary.diagnostic_lab`` if it looks like one (e.g. raw mcp_pull
    payloads from public lab feeds that bypass Triage)."""
    out: list[str] = []
    if obs.triage and obs.triage.candidate_pathogens:
        out.extend(c.pathogen_id for c in obs.triage.candidate_pathogens)
    aux = obs.dataset.auxiliary
    lab = (aux.diagnostic_lab or "").strip()
    if lab.startswith("pathogen."):
        out.append(lab)
    return out


def _is_confirmed(obs: Observation) -> bool:
    """A "confirmed" observation for the Tier-A / travel / chronic detectors.

    Anything not explicitly REJECTED by validation counts, provided we can
    attach a pathogen slug. (We deliberately *don't* require the upstream
    validation agent to have run -- raw mcp_pull observations from
    surveillance feeds are confirmed-by-construction at the source.)
    """
    if obs.validation and obs.validation.status.value == "reject":
        return False
    if obs.validation_status and obs.validation_status.value == "reject":
        return False
    return True


def _has_travel_exposure(obs: Observation) -> bool:
    expo = obs.dataset.exposure
    return bool(expo and expo.history_of_travel)


def _bucket_key(ts: datetime, bucket: str) -> str:
    if bucket == "week":
        return _iso_week_key(ts)
    return _two_hour_bucket_key(ts)


def _bucket_duration(bucket: str) -> timedelta:
    """Width of *one* bucket (week or 2-hour). Used by the audit fields."""
    if bucket == "week":
        return timedelta(days=7)
    return timedelta(hours=2)


def _scan_horizon(bucket: str) -> timedelta:
    """How far back from ``now`` we look for candidate hot cells.

    Wider than one bucket -- the detector evaluates every (zcta, bucket)
    pair in the scan horizon so a hot 2-hour window five hours ago is
    still emitted when ``run()`` is called now. The horizons are pinned
    short enough that buckets older than the trailing baseline are still
    safely excluded.
    """
    if bucket == "week":
        # Trailing 2 ISO weeks (so a Monday-evening run sees Sunday-night
        # data from the bucket that just closed).
        return timedelta(days=14, seconds=60)
    # 24-hour scan horizon -> 12 candidate 2-hour buckets.
    return timedelta(hours=24, seconds=60)


def _floor_expectation(bucket: str) -> float:
    """Small floor on the expected count so a totally-quiet baseline does
    not divide-by-zero the Tier-1 ratio. Hand-picked so a single isolated
    observation never trips the detector on a cold ZCTA.
    """
    if bucket == "week":
        return 0.25
    return 0.05


def _dominant_pathogen_hint(observations: list[Observation]) -> Optional[str]:
    """Best-effort: pick the most common candidate pathogen across the
    cluster's observations. Falls back to None if nothing scored."""
    tally: dict[str, float] = defaultdict(float)
    for o in observations:
        if not o.triage:
            continue
        for cand in o.triage.candidate_pathogens:
            tally[cand.pathogen_id] += max(cand.score, 1.0)
    if not tally:
        return None
    return max(tally.items(), key=lambda kv: kv[1])[0]


__all__ = [
    "ClusterDetectionAgent",
    "TuningProfile",
    "VBD_PROFILE",
    "HEAT_PROFILE",
    "VBD_COUNTY_PROFILE",
    "HEAT_SEASON_MONTHS",
    "PRIOR_ALPHA",
    "PRIOR_BETA",
    "EFFECT_SIZE_RR",
    "SINGLE_CASE_WINDOW_DAYS",
    "SINGLE_CASE_ALERTABLE",
    "CHRONIC_DRIFT_MULTIPLIER",
    "CHRONIC_TRAILING_DAYS",
    "CHRONIC_HISTORICAL_DAYS",
    "CHRONIC_BASELINE_PATHOGENS",
    "TRAVEL_CLUSTER_MIN_OBS",
    "TRAVEL_CLUSTER_WINDOW_DAYS",
    "HISTORICAL_OUTBREAKS",
    "HistoricalOutbreak",
]
