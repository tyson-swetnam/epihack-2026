"""Federated Cluster Detection -- sufficient-statistics exchange.

Per Phase 4 of ``plan/05-roadmap.md``: tribal partners (and other
data-sovereign sites) contribute to the state-wide cluster detector by
exchanging **only aggregated sufficient statistics**, not row-level
observations. The math is identical to a centralised Poisson scan
because the scan statistic is a function of bucket counts alone -- so
summing per-bucket counts across sites is mathematically equivalent to
pooling the underlying line-list and running the centralised detector,
without any line-list ever leaving a site.

See ``plan/FEDERATED.md`` for the protocol description, the privacy
budget table, and the onboarding checklist for a new site.

Design summary
--------------

1. ``LocalSiteAggregator`` runs *inside* each site (e.g. ITCA-TEC,
   Coconino HHS, MCDPH, AZGFD). It consumes the site's local
   ``Observation`` set and emits a single
   :class:`SufficientStatistics` payload: per-(zcta, iso_week / 2h
   bucket) counts, a hashed site_id, the time window, and -- if a
   private key is configured -- an Ed25519 signature over the
   canonical-JSON form. **No Observation reference is reachable from
   the emitted payload.** The aggregator is the single chokepoint
   that enforces that invariant; ``test_federated.py`` walks the
   payload and asserts it holds.

2. ``FederatedScanCoordinator`` runs at the federation hub (or in
   the public-aggregate role -- this prototype is agnostic to where
   it sits). It accepts a list of ``SufficientStatistics`` from
   distinct sites, optionally verifies signatures with each site's
   registered Ed25519 public key, sums the per-bucket counts, and
   reconstructs the minimum *synthetic* ``Observation`` set needed
   to feed the existing :class:`ClusterDetectionAgent`. The output
   alerts are tagged ``cluster_kind='federated'`` and carry a
   ``contributing_sites=[<hashed site ids>]`` audit trail.

3. ``apply_laplace_noise(stats, epsilon)`` is an optional DP layer.
   It adds Laplace(1 / epsilon) noise to each per-bucket count and
   clamps to zero. The default ``epsilon=1.0`` matches the budget
   table in ``plan/FEDERATED.md``. **Trade-off**: lower epsilon -->
   stronger privacy, higher false negative + false positive rate.

4. ``verify_signed(stats, public_key)`` sketches the Ed25519
   verification surface. Signatures cover the canonical-JSON form
   of the statistics payload sans the ``signature`` / ``site_pubkey``
   fields. A production deployment would key by registered
   ``site_pubkey`` (Trust-On-First-Use against a tribal-DUA-managed
   registry); this prototype takes the public key as a direct
   argument.

What this is NOT
----------------

This is a *transport-and-aggregation* prototype, not a complete
private-computation system. Specifically:

* The aggregator is honest-but-curious. Secure MPC would let the
  sites compute the sum without revealing per-site counts even to
  the coordinator; not implemented.
* The DP budget is per-release, not tracked across runs. A formal
  privacy budget would compose over time and across query types.
* The coordinator surface is not malicious-aggregator-hardened
  (replay protection, monotonic nonces, anti-rollback).

See ``plan/FEDERATED.md`` "Why it's incomplete for production" for
the full open-work list.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .cluster import (
    ClusterDetectionAgent,
    _bucket_key,
    _in_heat_season,
    _obs_zcta,
    _parse_obs_ts,
)
from .contracts import (
    CandidatePathogen,
    ClusterAlert,
    GeneralClass,
    GeoEnrichment,
    Kind,
    MinimumDataset,
    Observation,
    TriageDecision,
    TriageClass,
    Vertical,
)


# ---------------------------------------------------------------------------
# Site-id hashing
# ---------------------------------------------------------------------------
def hash_site_id(site_id: str, *, salt: str = "epihack-az-2026") -> str:
    """Stable, deterministic, non-reversible site-id hash.

    The salt is a constant -- so the hash is consistent across runs but
    is meaningless without the salt. Sites that want unlinkability
    across releases pick their own per-release salt.
    """
    h = hashlib.sha256()
    h.update(salt.encode("utf-8"))
    h.update(b"::")
    h.update(site_id.encode("utf-8"))
    return "site." + h.hexdigest()[:16]


# ---------------------------------------------------------------------------
# Sufficient-statistics payload
# ---------------------------------------------------------------------------
class BucketCount(BaseModel):
    """One (zcta, bucket-key) cell from a site's local tally.

    ``bucket_key`` is the ISO-week label (``2021-W31``) for VBD /
    off-season Heat, or the 2-hour bucket-start ISO timestamp
    (``2024-08-15T18:00:00+00:00``) for in-season Heat. Same shape the
    centralised detector uses internally -- see
    ``onehealth_agents.cluster._bucket_key``.

    ``pathogen_tally`` is the per-pathogen sub-count inside the cell so
    that the centralised detector's pathogen-hint and single-case
    detectors stay functional in the federated path. Empty when no
    triage decision is attached to the underlying observations.
    """

    model_config = ConfigDict(extra="forbid")

    zcta: str
    bucket_key: str
    count: float = Field(
        ge=0.0,
        description=(
            "Number of observations in this (zcta, bucket) cell. Float to "
            "accommodate non-integer Laplace-noised counts; the coordinator "
            "rounds back to an int when reconstructing synthetic observations."
        ),
    )
    pathogen_tally: dict[str, int] = Field(default_factory=dict)


class SufficientStatistics(BaseModel):
    """A site's complete contribution to one federated detection round.

    Carries the per-bucket counts, the active-ZCTA universe (so the
    coordinator can compute a leave-one-out baseline rate consistently
    with the centralised detector), the time window, an optional
    Ed25519 signature, and the hashed site identifier.

    **Invariant**: no ``Observation`` reference is reachable from any
    field on this model. The aggregator is the single point that
    enforces that property; ``test_federated.py`` walks the payload and
    asserts it. (This is what makes the payload safe to release.)
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1

    site_id_hash: str = Field(
        description=(
            "SHA-256 hash of the site identifier (e.g. 'site.itcatec'). "
            "Reversible only by the site that issued it."
        ),
    )
    vertical: Vertical
    bucket: str = Field(description="'week' or '2h'.")

    window_start: str = Field(description="ISO 8601 inclusive lower bound.")
    window_end: str = Field(description="ISO 8601 inclusive upper bound.")

    cells: list[BucketCount] = Field(default_factory=list)
    active_zctas: list[str] = Field(
        default_factory=list,
        description=(
            "ZCTAs the site treats as part of its observational universe "
            "(non-zero population, currently in scope). Used by the "
            "coordinator to compute the leave-one-out baseline rate."
        ),
    )
    baseline_total: int = Field(
        default=0,
        ge=0,
        description=(
            "Total trailing-baseline-window observation count for the site, "
            "across all active ZCTAs. The detector divides this by "
            "(n_active * baseline_window_days) to get a per-ZCTA-per-day "
            "rate; sending the sum keeps the wire payload aggregate-only."
        ),
    )
    baseline_window_days: int = Field(
        default=28,
        ge=1,
        description="Width of the trailing baseline window (days). Default 4 wk.",
    )

    site_pubkey: Optional[str] = Field(
        default=None,
        description=(
            "Hex-encoded raw Ed25519 public key (32 bytes / 64 hex chars). "
            "When present, the coordinator verifies ``signature``."
        ),
    )
    signature: Optional[str] = Field(
        default=None,
        description=(
            "Hex-encoded Ed25519 signature over the canonical-JSON form of "
            "this payload with ``signature`` and ``site_pubkey`` excluded."
        ),
    )

    dp_epsilon: Optional[float] = Field(
        default=None,
        description=(
            "Privacy budget epsilon used by apply_laplace_noise(); None "
            "means no DP noise was applied."
        ),
    )

    # ------------------------------------------------------------------
    def canonical_json(self, *, omit_signature: bool = True) -> bytes:
        """Stable byte serialisation for signing / verifying.

        Sorts keys and excludes the signature itself so a sender can
        produce the bytes-to-sign deterministically and a receiver can
        recompute the same bytes-to-verify.
        """
        data = self.model_dump(mode="json")
        if omit_signature:
            data.pop("signature", None)
            data.pop("site_pubkey", None)
        return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


# ---------------------------------------------------------------------------
# Local site aggregator
# ---------------------------------------------------------------------------
class LocalSiteAggregator:
    """Runs inside a site. Turns local ``Observation`` rows into a
    :class:`SufficientStatistics` payload.

    The aggregator is the **single chokepoint** that enforces the
    "no observation ever leaves the site" invariant -- the emitted
    payload holds only primitives (strings, ints, floats, dicts of
    primitives). ``test_federated.py`` walks every reference inside a
    payload to confirm.
    """

    def __init__(
        self,
        *,
        site_id: str,
        baseline_weeks: int = 4,
    ) -> None:
        self.site_id = site_id
        self.site_id_hash = hash_site_id(site_id)
        self.baseline_weeks = baseline_weeks

    # ------------------------------------------------------------------
    def aggregate(
        self,
        observations: Iterable[Observation],
        *,
        vertical: Vertical,
        now: datetime | None = None,
    ) -> SufficientStatistics:
        """Bucket the site's observations and produce a release payload."""
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        bucket = _pick_bucket(vertical, now)
        scan_start, baseline_start = _windows_for(
            now=now, bucket=bucket, baseline_weeks=self.baseline_weeks,
        )

        cell_counts: dict[tuple[str, str], int] = defaultdict(int)
        cell_pathogens: dict[tuple[str, str], dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        active_zctas: set[str] = set()
        baseline_total = 0

        for obs in observations:
            # Vertical scoping mirrors ClusterDetectionAgent.run().
            if vertical is Vertical.VBD:
                if obs.vertical not in (Vertical.VBD, Vertical.BOTH):
                    continue
            elif vertical is Vertical.HEAT:
                if obs.vertical not in (Vertical.HEAT, Vertical.BOTH):
                    continue
            else:
                continue

            ts = _parse_obs_ts(obs.received_at)
            if ts is None:
                continue
            zcta = _obs_zcta(obs)
            if not zcta:
                continue
            active_zctas.add(zcta)

            if scan_start <= ts <= now:
                key = _bucket_key(ts, bucket)
                cell_counts[(zcta, key)] += 1
                if obs.triage and obs.triage.candidate_pathogens:
                    for cand in obs.triage.candidate_pathogens:
                        cell_pathogens[(zcta, key)][cand.pathogen_id] += 1
            elif baseline_start <= ts < scan_start:
                baseline_total += 1

        cells = [
            BucketCount(
                zcta=zcta,
                bucket_key=key,
                count=float(cnt),
                pathogen_tally=dict(cell_pathogens[(zcta, key)]),
            )
            for (zcta, key), cnt in sorted(cell_counts.items())
        ]

        return SufficientStatistics(
            site_id_hash=self.site_id_hash,
            vertical=vertical,
            bucket=bucket,
            window_start=scan_start.isoformat(),
            window_end=now.isoformat(),
            cells=cells,
            active_zctas=sorted(active_zctas),
            baseline_total=baseline_total,
            baseline_window_days=self.baseline_weeks * 7,
        )

    # ------------------------------------------------------------------
    def sign(self, stats: SufficientStatistics, private_key_pem: bytes) -> SufficientStatistics:
        """Attach an Ed25519 signature over the canonical-JSON form.

        ``private_key_pem`` is PEM-encoded Ed25519 (cryptography's
        ``serialization.load_pem_private_key``). The signature covers
        the payload with ``signature`` / ``site_pubkey`` cleared so
        that the same bytes can be recomputed on the receiving side.
        """
        from cryptography.hazmat.primitives import serialization

        priv = serialization.load_pem_private_key(private_key_pem, password=None)
        pub_bytes = priv.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        # Build a clean copy and sign the canonical form.
        cleared = stats.model_copy(update={"signature": None, "site_pubkey": None})
        sig = priv.sign(cleared.canonical_json())
        return stats.model_copy(update={
            "site_pubkey": pub_bytes.hex(),
            "signature": sig.hex(),
        })


# ---------------------------------------------------------------------------
# Federated coordinator
# ---------------------------------------------------------------------------
class FederatedScanCoordinator:
    """Runs the centralised cluster detector on aggregated sufficient
    statistics. Output alerts carry ``cluster_kind='federated'`` and a
    ``contributing_sites`` audit list.
    """

    def __init__(
        self,
        *,
        agent: ClusterDetectionAgent | None = None,
        trusted_pubkeys: Optional[dict[str, str]] = None,
    ) -> None:
        self.agent = agent or ClusterDetectionAgent()
        # site_id_hash -> hex public key (for signature verification).
        self.trusted_pubkeys = dict(trusted_pubkeys or {})

    # ------------------------------------------------------------------
    def detect(
        self,
        stats_list: list[SufficientStatistics],
        *,
        now: datetime | None = None,
        require_signature: bool = False,
    ) -> list[ClusterAlert]:
        """Aggregate the site payloads, rebuild synthetic observations,
        run the detector, and tag the resulting alerts as federated.
        """
        if not stats_list:
            return []
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        verified_sites: list[str] = []
        for stats in stats_list:
            pub = self.trusted_pubkeys.get(stats.site_id_hash) or stats.site_pubkey
            if require_signature and not pub:
                raise ValueError(
                    f"require_signature=True but no public key for {stats.site_id_hash}"
                )
            if pub and stats.signature:
                if not verify_signed(stats, pub):
                    raise ValueError(
                        f"Ed25519 signature failed for site {stats.site_id_hash}"
                    )
            verified_sites.append(stats.site_id_hash)

        # All payloads must agree on vertical + bucket for a single run.
        verticals = {s.vertical for s in stats_list}
        buckets = {s.bucket for s in stats_list}
        if len(verticals) != 1 or len(buckets) != 1:
            raise ValueError(
                "Federated round must be vertical-and-bucket-uniform; "
                f"got verticals={verticals} buckets={buckets}"
            )
        vertical = next(iter(verticals))
        bucket = next(iter(buckets))

        # Sum across sites.
        cell_total: dict[tuple[str, str], float] = defaultdict(float)
        cell_pathogen_total: dict[tuple[str, str], dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        active_zctas: set[str] = set()
        baseline_total = 0
        baseline_window_days = stats_list[0].baseline_window_days

        for stats in stats_list:
            active_zctas.update(stats.active_zctas)
            baseline_total += stats.baseline_total
            for cell in stats.cells:
                cell_total[(cell.zcta, cell.bucket_key)] += cell.count
                for pid, n in cell.pathogen_tally.items():
                    cell_pathogen_total[(cell.zcta, cell.bucket_key)][pid] += n

        synth = _reconstruct_synthetic_observations(
            vertical=vertical,
            bucket=bucket,
            cell_total=cell_total,
            cell_pathogens=cell_pathogen_total,
            active_zctas=active_zctas,
            baseline_total=baseline_total,
            baseline_window_days=baseline_window_days,
            now=now,
        )

        raw_alerts = self.agent.run(synth, now=now)

        # Only the spatial Tier-1/Tier-2 alerts are reliable on
        # aggregated sufficient stats. Tier-A single-case, Tier-C
        # chronic-drift, and travel-import detectors need row-level
        # exposure / pathogen / timestamp metadata that the
        # federated payload deliberately doesn't carry.
        out: list[ClusterAlert] = []
        for a in raw_alerts:
            if a.cluster_kind != "spatial":
                continue
            out.append(a.model_copy(update={
                "cluster_kind": "federated",
                "contributing_sites": sorted(set(verified_sites)),
            }))
        return out


# ---------------------------------------------------------------------------
# Optional DP layer
# ---------------------------------------------------------------------------
def apply_laplace_noise(
    stats: SufficientStatistics,
    epsilon: float = 1.0,
    *,
    rng: random.Random | None = None,
) -> SufficientStatistics:
    """Add Laplace(1 / epsilon) noise to each bucket count.

    The Laplace mechanism with scale ``b = sensitivity / epsilon = 1/eps``
    is epsilon-differentially private under the assumption that a single
    contributor changes any one bucket count by at most 1. Per the
    privacy-budget trade-off table in ``plan/FEDERATED.md``:

    * ``epsilon=0.1``  -- very strong privacy, mean |noise| ~10. The
      detector will lose small-denominator clusters and emit more
      false positives.
    * ``epsilon=1.0``  -- moderate privacy, mean |noise| ~1. Cluster
      alerts are usually preserved; FP-rate ~doubles vs the no-noise
      run on realistic baselines.
    * ``epsilon=10.0`` -- weak privacy, mean |noise| ~0.1. Alerts are
      essentially indistinguishable from the centralised output.

    Counts are clamped to zero (Laplace can go negative). The
    coordinator's reconstruction step rounds floats back to ints.
    """
    if epsilon <= 0:
        raise ValueError("epsilon must be strictly positive")
    rng = rng or random.Random()
    scale = 1.0 / epsilon

    noisy_cells: list[BucketCount] = []
    for cell in stats.cells:
        # Laplace via inverse-CDF on a uniform [-0.5, 0.5] draw.
        u = rng.uniform(-0.5, 0.5)
        noise = -scale * math.copysign(math.log(1 - 2 * abs(u) + 1e-12), u)
        noisy = max(0.0, cell.count + noise)
        noisy_cells.append(cell.model_copy(update={"count": noisy}))

    # Noise the baseline total too, so the rate denominator is also DP.
    u = rng.uniform(-0.5, 0.5)
    noise = -scale * math.copysign(math.log(1 - 2 * abs(u) + 1e-12), u)
    noisy_baseline = max(0, int(round(stats.baseline_total + noise)))

    return stats.model_copy(update={
        "cells": noisy_cells,
        "baseline_total": noisy_baseline,
        "dp_epsilon": epsilon,
        # A noised payload's signature no longer matches. Strip.
        "signature": None,
    })


# ---------------------------------------------------------------------------
# Ed25519 verification sketch
# ---------------------------------------------------------------------------
def verify_signed(stats: SufficientStatistics, public_key_hex: str) -> bool:
    """Verify the Ed25519 signature on a sufficient-statistics payload.

    ``public_key_hex`` is the 64-hex-char raw Ed25519 public key
    (matches what ``LocalSiteAggregator.sign`` stores in
    ``site_pubkey``). Returns True iff the signature on the canonical
    JSON form (with ``signature`` / ``site_pubkey`` cleared) verifies.
    """
    if not stats.signature:
        return False
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey,
        )
    except ImportError:  # pragma: no cover - cryptography is a hard dep at run
        return False

    try:
        pub_bytes = bytes.fromhex(public_key_hex)
    except ValueError:
        return False
    try:
        pub = Ed25519PublicKey.from_public_bytes(pub_bytes)
    except Exception:  # pragma: no cover
        return False

    try:
        sig_bytes = bytes.fromhex(stats.signature)
    except ValueError:
        return False
    try:
        pub.verify(sig_bytes, stats.canonical_json())
    except InvalidSignature:
        return False
    return True


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------
def _pick_bucket(vertical: Vertical, now: datetime) -> str:
    """Mirror ``ClusterDetectionAgent.profile_for`` bucket selection."""
    if vertical is Vertical.HEAT and _in_heat_season(now):
        return "2h"
    return "week"


def _windows_for(
    *, now: datetime, bucket: str, baseline_weeks: int,
) -> tuple[datetime, datetime]:
    """Return ``(scan_start, baseline_start)`` consistent with the central
    detector's ``_scan_horizon`` and ``_scan_vertical`` choices."""
    if bucket == "week":
        scan_horizon = timedelta(days=14, seconds=60)
    else:
        scan_horizon = timedelta(hours=24, seconds=60)
    scan_start = now - scan_horizon
    baseline_start = scan_start - timedelta(weeks=baseline_weeks)
    return scan_start, baseline_start


def _reconstruct_synthetic_observations(
    *,
    vertical: Vertical,
    bucket: str,
    cell_total: dict[tuple[str, str], float],
    cell_pathogens: dict[tuple[str, str], dict[str, int]],
    active_zctas: set[str],
    baseline_total: int,
    baseline_window_days: int,
    now: datetime,
) -> list[Observation]:
    """Build the smallest synthetic ``Observation`` set that, when fed
    to ``ClusterDetectionAgent.run``, reproduces the aggregated counts.

    The synthetic observations are deterministic in (zcta, bucket_key,
    index) so the federated detector is reproducible across runs given
    the same inputs.

    Each synthetic obs carries ``Kind.MCP_PULL`` (so audit fields make
    sense) and a ``GeoEnrichment`` with the ZCTA. The pathogen
    sub-tally is attached as a synthetic ``TriageDecision`` whose
    ``candidate_pathogens`` mirror the per-cell pathogen distribution,
    so the centralised detector's pathogen-hint logic still surfaces
    something sensible in the federated path.
    """
    # Place the synthetic obs at the *middle* of each bucket so a 2h
    # bucket lands inside its own boundary and the week-cadence detector
    # sees a clean Monday-to-Sunday assignment.
    obs_list: list[Observation] = []
    for (zcta, bucket_key), count in cell_total.items():
        n = int(round(count))
        if n <= 0:
            continue
        bucket_mid = _bucket_midpoint(bucket_key, bucket)
        pathogen_tally = cell_pathogens.get((zcta, bucket_key), {})
        pathogen_seq = _pathogen_sequence(pathogen_tally, n)
        for i in range(n):
            pid = pathogen_seq[i]
            triage: Optional[TriageDecision] = None
            if pid is not None:
                triage = TriageDecision(
                    vertical=vertical,
                    triage_class=TriageClass.SEE_CLINICIAN,
                    rationale="synthetic federated reconstruction",
                    candidate_pathogens=[
                        CandidatePathogen(pathogen_id=pid, score=1.0)
                    ],
                )
            obs_list.append(
                Observation(
                    observation_id=f"federated.{zcta}.{bucket_key}.{i}",
                    kind=Kind.MCP_PULL,
                    vertical=vertical,
                    received_at=bucket_mid.isoformat(),
                    dataset=MinimumDataset(general=GeneralClass(postal_code=zcta)),
                    geo=GeoEnrichment(zcta=zcta),
                    triage=triage,
                )
            )

    # Baseline observations: scatter across the trailing baseline window
    # so the detector's per-ZCTA-per-day rate calculation reproduces the
    # site-side division. We distribute proportionally to a known site
    # universe (the active ZCTAs); each ZCTA gets a share of the total
    # baseline equal to baseline_total // n_zctas, with the remainder
    # going to the first lexicographically-ordered ZCTAs.
    n_zctas = max(1, len(active_zctas))
    base_per_zcta, remainder = divmod(baseline_total, n_zctas)
    zctas_sorted = sorted(active_zctas)
    baseline_window = timedelta(days=baseline_window_days)
    scan_horizon = timedelta(days=14, seconds=60) if bucket == "week" \
        else timedelta(hours=24, seconds=60)
    baseline_end = now - scan_horizon
    baseline_start = baseline_end - baseline_window
    for idx, zcta in enumerate(zctas_sorted):
        share = base_per_zcta + (1 if idx < remainder else 0)
        for j in range(share):
            # Spread linearly through the baseline window so every day
            # gets coverage and the rate calc is stable.
            frac = (j + 0.5) / max(share, 1)
            ts = baseline_start + frac * baseline_window
            obs_list.append(
                Observation(
                    observation_id=f"federated.baseline.{zcta}.{j}",
                    kind=Kind.MCP_PULL,
                    vertical=vertical,
                    received_at=ts.isoformat(),
                    dataset=MinimumDataset(general=GeneralClass(postal_code=zcta)),
                    geo=GeoEnrichment(zcta=zcta),
                )
            )
    return obs_list


def _bucket_midpoint(bucket_key: str, bucket: str) -> datetime:
    if bucket == "week":
        from datetime import date
        year, week = bucket_key.split("-W")
        d = date.fromisocalendar(int(year), int(week), 4)  # Thursday
        return datetime(d.year, d.month, d.day, 12, 0, tzinfo=timezone.utc)
    start = datetime.fromisoformat(bucket_key)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    return start + timedelta(hours=1)


def _pathogen_sequence(tally: dict[str, int], n: int) -> list[Optional[str]]:
    """Expand a {pathogen: count} tally to a per-observation sequence of
    length ``n`` (padding with None when the tally undercounts)."""
    out: list[Optional[str]] = []
    for pid, cnt in sorted(tally.items()):
        out.extend([pid] * cnt)
    while len(out) < n:
        out.append(None)
    return out[:n]


__all__ = [
    "BucketCount",
    "SufficientStatistics",
    "LocalSiteAggregator",
    "FederatedScanCoordinator",
    "apply_laplace_noise",
    "verify_signed",
    "hash_site_id",
]
