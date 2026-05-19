"""Tests for federated cluster detection (plan/05 Phase 4).

Synthesises the 2021 Maricopa WNV outbreak across four sites
(ITCA-TEC, Coconino HHS, MCDPH, AZGFD) and asserts:

* Centralised and federated detectors produce the *same* set of
  spatial cluster alerts (no DP noise).
* The DP variant (epsilon=1.0) yields an alert set that is a
  superset of the centralised set at least 80% of the time across
  20 reruns.
* A ``SufficientStatistics`` payload contains no reachable
  ``Observation`` reference -- the aggregator is the chokepoint
  that enforces the "no row-level data leaves the site"
  invariant from plan/02.
* Ed25519 signature sign/verify roundtrip works and rejects
  tampered payloads.
"""

from __future__ import annotations

import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Iterable

import pytest

from onehealth_agents import (
    CandidatePathogen,
    ClusterDetectionAgent,
    GeneralClass,
    GeoEnrichment,
    Kind,
    MinimumDataset,
    Observation,
    TriageClass,
    TriageDecision,
    Vertical,
)
from onehealth_agents.federated import (
    BucketCount,
    FederatedScanCoordinator,
    LocalSiteAggregator,
    SufficientStatistics,
    apply_laplace_noise,
    hash_site_id,
    verify_signed,
)


# ---------------------------------------------------------------------------
# Synthesis: 2021 Maricopa WNV outbreak across 4 sites
# ---------------------------------------------------------------------------
# The 4 sites approximately mirror the standing review board in plan/05:
#   * ITCA-TEC      -- tribal epidemiology center; some shared Maricopa
#                      reservation ZCTAs.
#   * Coconino HHS  -- northern AZ; mostly background, low VBD load.
#   * MCDPH         -- Maricopa County DPH; the bulk of the outbreak
#                      observations.
#   * AZGFD         -- statewide wildlife; small VBD signal from dead-bird
#                      reports that overlap MCDPH ZCTAs.
SITES = ("ITCA-TEC", "Coconino HHS", "MCDPH", "AZGFD")

# Outbreak ZCTAs (Maricopa hot cells -- all in 85*).
OUTBREAK_ZCTAS = ("85003", "85009", "85033", "85040")
# Coconino baseline ZCTAs (northern AZ).
COCONINO_ZCTAS = ("86001", "86040")
# ITCA-TEC baseline ZCTAs (mix of reservation-adjacent).
ITCA_ZCTAS = ("86503", "85624")

RNG_SEED = 20260519
NOW = datetime(2021, 9, 1, 12, 0, tzinfo=timezone.utc)
# Anchor the synthesis so the centralised detector's two-week scan
# horizon and 4-week baseline window line up with the WNV peak.


def _make_obs(
    *,
    zcta: str,
    ts: datetime,
    vertical: Vertical = Vertical.VBD,
    pathogen: str | None = "pathogen.wnv",
    obs_id: str | None = None,
) -> Observation:
    triage = None
    if pathogen:
        triage = TriageDecision(
            vertical=vertical,
            triage_class=TriageClass.SEE_CLINICIAN,
            rationale="synthetic",
            candidate_pathogens=[CandidatePathogen(pathogen_id=pathogen, score=1.0)],
        )
    return Observation(
        observation_id=obs_id or f"observation.{ts.timestamp():.6f}.{zcta}",
        kind=Kind.MCP_PULL,
        vertical=vertical,
        received_at=ts.isoformat(),
        dataset=MinimumDataset(general=GeneralClass(postal_code=zcta)),
        geo=GeoEnrichment(zcta=zcta),
        triage=triage,
    )


def _scatter(
    rng: random.Random,
    *,
    zctas: Iterable[str],
    start: datetime,
    end: datetime,
    n: int,
    pathogen: str | None = "pathogen.wnv",
) -> list[Observation]:
    """``n`` observations uniformly across ``[start, end)`` and ``zctas``."""
    span = (end - start).total_seconds()
    out: list[Observation] = []
    z = list(zctas)
    for i in range(n):
        ts = start + timedelta(seconds=rng.uniform(0, span))
        zcta = z[i % len(z)]
        out.append(_make_obs(zcta=zcta, ts=ts, pathogen=pathogen,
                             obs_id=f"observation.{i}.{ts.timestamp():.6f}.{zcta}"))
    return out


def synthesise_sites(rng: random.Random) -> dict[str, list[Observation]]:
    """Build per-site observation sets for the 2021 Maricopa WNV scenario.

    Total volume is tuned so the centralised Tier-1 (theta=3, k=5) and
    Tier-2 posterior cross threshold on at least one outbreak ZCTA.
    """
    baseline_start = NOW - timedelta(days=6 * 7)        # 6 wk of baseline
    scan_start = NOW - timedelta(days=14)               # 2 wk scan horizon

    site_obs: dict[str, list[Observation]] = {s: [] for s in SITES}

    # ---- Baseline noise -------------------------------------------------
    # MCDPH carries the bulk of the AZ baseline volume.
    site_obs["MCDPH"].extend(
        _scatter(rng, zctas=OUTBREAK_ZCTAS + ("85201", "85301", "85718"),
                 start=baseline_start, end=scan_start, n=12)
    )
    # Coconino baseline.
    site_obs["Coconino HHS"].extend(
        _scatter(rng, zctas=COCONINO_ZCTAS,
                 start=baseline_start, end=scan_start, n=3)
    )
    # ITCA-TEC baseline -- mostly tribal ZCTAs, very light.
    site_obs["ITCA-TEC"].extend(
        _scatter(rng, zctas=ITCA_ZCTAS,
                 start=baseline_start, end=scan_start, n=2)
    )
    # AZGFD dead-bird statewide baseline.
    site_obs["AZGFD"].extend(
        _scatter(rng, zctas=OUTBREAK_ZCTAS + ("85201", "85718"),
                 start=baseline_start, end=scan_start, n=4)
    )

    # ---- Outbreak signal in the scan window -----------------------------
    # MCDPH sees the clinical case spike (per AZ 2021 WNV peak). The
    # counts are deliberately well above the Tier-1 ``k=5`` and
    # ``theta=3`` thresholds in both hot ZCTAs, so the centralised
    # signature is robust to Laplace(b=1.0) noise in the DP variant.
    site_obs["MCDPH"].extend(
        _scatter(rng, zctas=("85003",),
                 start=scan_start, end=NOW, n=24)
    )
    site_obs["MCDPH"].extend(
        _scatter(rng, zctas=("85009",),
                 start=scan_start, end=NOW, n=22)
    )
    # AZGFD spots 5 dead corvids in 85003 + 2 in 85033.
    site_obs["AZGFD"].extend(
        _scatter(rng, zctas=("85003",), start=scan_start, end=NOW, n=5)
    )
    site_obs["AZGFD"].extend(
        _scatter(rng, zctas=("85033",), start=scan_start, end=NOW, n=2)
    )

    return site_obs


# ---------------------------------------------------------------------------
# Helpers for comparing alert sets
# ---------------------------------------------------------------------------
def _spatial_signature(alerts):
    """Reduce an alert list to the (zcta, window_start) signature so
    centralised vs federated can be compared invariantly of tagging."""
    return {
        (a.vertical, a.zcta, a.window_start)
        for a in alerts
        if a.cluster_kind in ("spatial", "federated") and a.zcta is not None
    }


# ---------------------------------------------------------------------------
# 1. Centralised vs federated equality (no DP noise)
# ---------------------------------------------------------------------------
def test_centralized_and_federated_produce_the_same_alert_set():
    rng = random.Random(RNG_SEED)
    site_obs = synthesise_sites(rng)

    # Centralised: pool every site's observations.
    all_obs = [o for obs in site_obs.values() for o in obs]
    central_alerts = ClusterDetectionAgent().run(all_obs, now=NOW)

    # Federated: aggregate per site, then run the coordinator.
    payloads: list[SufficientStatistics] = []
    for site, obs in site_obs.items():
        agg = LocalSiteAggregator(site_id=site)
        payloads.append(agg.aggregate(obs, vertical=Vertical.VBD, now=NOW))
    fed_alerts = FederatedScanCoordinator().detect(payloads, now=NOW)

    central_sig = _spatial_signature(central_alerts)
    fed_sig = _spatial_signature(fed_alerts)

    assert central_sig, (
        "Synthesis underflow: centralised detector found no spatial alerts "
        "for the Maricopa-WNV-2021 scenario; "
        "the federated equivalence test is meaningless without a positive."
    )
    assert central_sig == fed_sig, (
        f"Centralised vs federated mismatch:\n"
        f"  central only: {central_sig - fed_sig}\n"
        f"  federated only: {fed_sig - central_sig}"
    )

    # Every federated alert must carry the four contributing-site hashes.
    expected_sites = {hash_site_id(s) for s in SITES}
    for a in fed_alerts:
        assert a.cluster_kind == "federated"
        assert set(a.contributing_sites) == expected_sites
        assert a.contributing_sites == sorted(a.contributing_sites)


# ---------------------------------------------------------------------------
# 2. DP variant: superset rate
# ---------------------------------------------------------------------------
def test_dp_variant_alert_set_is_superset_at_least_80pct():
    """With epsilon=1.0 Laplace noise, the federated alert set should be
    a superset of the centralised alert set at least 80% of the time.

    The Laplace mechanism with sensitivity 1 / epsilon 1 inflates cells
    upwards roughly as often as it deflates them, so the count-based
    threshold is more often crossed in extra cells than the true cells
    are pushed below threshold.
    """
    rng = random.Random(RNG_SEED + 1)
    site_obs = synthesise_sites(rng)

    all_obs = [o for obs in site_obs.values() for o in obs]
    central_sig = _spatial_signature(
        ClusterDetectionAgent().run(all_obs, now=NOW)
    )
    assert central_sig, "expected non-empty centralised signature for DP test"

    n_trials = 20
    n_superset = 0
    for trial in range(n_trials):
        trial_rng = random.Random(RNG_SEED + 100 + trial)
        payloads: list[SufficientStatistics] = []
        for site, obs in site_obs.items():
            agg = LocalSiteAggregator(site_id=site)
            stats = agg.aggregate(obs, vertical=Vertical.VBD, now=NOW)
            stats = apply_laplace_noise(stats, epsilon=1.0, rng=trial_rng)
            payloads.append(stats)
        fed_sig = _spatial_signature(
            FederatedScanCoordinator().detect(payloads, now=NOW)
        )
        if central_sig.issubset(fed_sig):
            n_superset += 1

    superset_rate = n_superset / n_trials
    # The brief asks for >= 80%; assert with a small safety margin.
    assert superset_rate >= 0.8, (
        f"DP superset rate {superset_rate:.0%} below target 80% "
        f"({n_superset}/{n_trials})"
    )


# ---------------------------------------------------------------------------
# 3. Property: no Observation reachable from a SufficientStatistics payload
# ---------------------------------------------------------------------------
def _reachable_references(root: object, *, max_objects: int = 5000) -> list[object]:
    """Walk every reference reachable from ``root`` (avoiding infinite
    recursion via an id-seen set). Mirrors the structural walk used by
    privacy-leak checks elsewhere in the repo."""
    seen: set[int] = set()
    out: list[object] = []
    stack: list[object] = [root]
    while stack and len(seen) < max_objects:
        obj = stack.pop()
        oid = id(obj)
        if oid in seen:
            continue
        seen.add(oid)
        out.append(obj)
        if isinstance(obj, (str, bytes, int, float, bool, type(None))):
            continue
        if isinstance(obj, dict):
            stack.extend(obj.keys())
            stack.extend(obj.values())
            continue
        if isinstance(obj, (list, tuple, set, frozenset)):
            stack.extend(obj)
            continue
        # pydantic / dataclass-ish: walk public attrs
        dct = getattr(obj, "__dict__", None)
        if isinstance(dct, dict):
            stack.extend(dct.values())
        slots = getattr(obj, "__slots__", None)
        if slots:
            for s in slots:
                try:
                    stack.append(getattr(obj, s))
                except AttributeError:
                    pass
        # pydantic BaseModel: access model_fields via the class to silence
        # the V2.11 deprecation warning about instance-level access.
        cls = type(obj)
        if hasattr(cls, "model_fields"):
            for fname in cls.model_fields:
                try:
                    stack.append(getattr(obj, fname))
                except AttributeError:
                    pass
    return out


def test_sufficient_statistics_payload_contains_no_observation_reference():
    """The aggregator is the chokepoint: zero ``Observation`` instances
    must be reachable from any field on ``SufficientStatistics``."""
    rng = random.Random(RNG_SEED + 2)
    site_obs = synthesise_sites(rng)

    payloads: list[SufficientStatistics] = []
    for site, obs in site_obs.items():
        agg = LocalSiteAggregator(site_id=site)
        payloads.append(agg.aggregate(obs, vertical=Vertical.VBD, now=NOW))

    leaks: list[str] = []
    for stats in payloads:
        for o in _reachable_references(stats):
            if isinstance(o, Observation):
                leaks.append(f"{stats.site_id_hash}: {o.observation_id}")
    assert not leaks, "Observation references leaked into payload: " + ", ".join(leaks)

    # Bonus: each payload should also be JSON-round-trippable, which is
    # the wire shape the federation hub actually receives.
    for stats in payloads:
        wire = stats.model_dump_json()
        round_tripped = SufficientStatistics.model_validate_json(wire)
        assert round_tripped == stats


# ---------------------------------------------------------------------------
# 4. Ed25519 sign / verify roundtrip
# ---------------------------------------------------------------------------
def _ed25519_keypair():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
    )
    priv = Ed25519PrivateKey.generate()
    pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_hex = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()
    return pem, pub_hex


def test_signed_statistics_verify_and_tamper_detection():
    rng = random.Random(RNG_SEED + 3)
    site_obs = synthesise_sites(rng)["MCDPH"]
    agg = LocalSiteAggregator(site_id="MCDPH")
    stats = agg.aggregate(site_obs, vertical=Vertical.VBD, now=NOW)

    pem, pub_hex = _ed25519_keypair()
    signed = agg.sign(stats, pem)
    assert signed.signature is not None
    assert signed.site_pubkey == pub_hex
    assert verify_signed(signed, pub_hex) is True

    # Tamper: bump a single bucket count by 1 and re-verify.
    if signed.cells:
        tampered_cells = list(signed.cells)
        tampered_cells[0] = tampered_cells[0].model_copy(
            update={"count": tampered_cells[0].count + 1.0}
        )
        tampered = signed.model_copy(update={"cells": tampered_cells})
        assert verify_signed(tampered, pub_hex) is False


def test_coordinator_rejects_bad_signature():
    """A trusted-key coordinator must throw when the signature doesn't
    verify; this is the line of defence against a tampered relay."""
    rng = random.Random(RNG_SEED + 4)
    site_obs = synthesise_sites(rng)
    pem, pub_hex = _ed25519_keypair()

    payloads = []
    for site, obs in site_obs.items():
        agg = LocalSiteAggregator(site_id=site)
        stats = agg.aggregate(obs, vertical=Vertical.VBD, now=NOW)
        signed = agg.sign(stats, pem)  # all sites share the keypair in this test
        payloads.append(signed)

    # Tamper with the first payload that actually has cells (some sites
    # may have an empty scan window).
    tamper_idx = next(i for i, p in enumerate(payloads) if p.cells)
    bad = payloads[tamper_idx]
    bad_cells = list(bad.cells)
    bad_cells[0] = bad_cells[0].model_copy(
        update={"count": bad_cells[0].count + 5}
    )
    payloads[tamper_idx] = bad.model_copy(update={"cells": bad_cells})

    coord = FederatedScanCoordinator(
        trusted_pubkeys={p.site_id_hash: pub_hex for p in payloads}
    )
    with pytest.raises(ValueError, match="signature failed"):
        coord.detect(payloads, now=NOW, require_signature=True)


# ---------------------------------------------------------------------------
# 5. Misc invariants
# ---------------------------------------------------------------------------
def test_hash_site_id_is_stable_and_opaque():
    a = hash_site_id("ITCA-TEC")
    b = hash_site_id("ITCA-TEC")
    c = hash_site_id("MCDPH")
    assert a == b
    assert a != c
    assert a.startswith("site.")
    # Hash must not contain the raw site id.
    assert "ITCA" not in a


def test_coordinator_requires_uniform_vertical_and_bucket():
    rng = random.Random(RNG_SEED + 5)
    site_obs = synthesise_sites(rng)["MCDPH"]
    a = LocalSiteAggregator(site_id="A").aggregate(
        site_obs, vertical=Vertical.VBD, now=NOW
    )
    # An empty Heat payload is enough to provoke the mixed-vertical guard.
    b = LocalSiteAggregator(site_id="B").aggregate(
        [], vertical=Vertical.HEAT, now=NOW,
    )
    with pytest.raises(ValueError, match="vertical-and-bucket-uniform"):
        FederatedScanCoordinator().detect([a, b], now=NOW)
