"""Wire ``onehealth_agents.cluster.ClusterDetectionAgent`` into the kg.

The agent itself runs over typed ``Observation`` objects. This module
reconstructs lightweight Observations from ``kg.node`` /
``kg.property`` / ``kg.edge`` rows -- only the fields the detector
actually reads (``vertical``, ``received_at``, geo.zcta or
``general.postal_code``, and any ``reportsAbout`` -> pathogen edges
that surface as ``triage.candidate_pathogens``).

The agents package is a hard dependency declared in pyproject.toml --
the import is deferred to call time so that test environments that
swap out the agents path get a clear ImportError rather than a server
boot failure.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import duckdb


def cluster_scan(
    conn: duckdb.DuckDBPyConnection,
    vertical: str,
    lookback_days: int = 14,
    county_id: Optional[str] = None,
    now: Optional[datetime] = None,
) -> list[dict]:
    """Run ``ClusterDetectionAgent`` against observations in the kg.

    Args:
        vertical: one of ``vbd`` / ``heat`` / ``both`` / ``neither``;
            passed through to the detector after coercion to the
            ``Vertical`` enum.
        lookback_days: how far back from ``now`` to load observations.
            The detector itself enforces its own scan horizon + 4-week
            baseline window; ``lookback_days`` only controls how many
            observations we hand it.
        county_id: optional ``county.*`` slug -- restricts the
            observation set to ones with a ``colocatedWith`` edge to
            that county.
        now: override "now" (useful for tests). Defaults to
            ``datetime.now(timezone.utc)``.

    Returns a list of dicts with the fields the dashboard cares about:
    ``zcta, county_id, lookback_window, observed, expected, tier1_score,
    tier2_posterior, severity, alert_status, pathogen_hint,
    historical_match, observation_ids``. ``alert_status`` is the
    enum-ish string `"alert"` (alerts always fire when emitted by the
    detector); ``severity`` is mapped from the rule's ``tier2_posterior``
    (>=0.99 -> "critical", >=0.95 -> "high", else -> "moderate").
    """
    # Lazy import so a missing onehealth-agents only fails the cluster
    # tool rather than the entire MCP boot path.
    from onehealth_agents.cluster import ClusterDetectionAgent
    from onehealth_agents.contracts import (
        CandidatePathogen,
        GeneralClass,
        GeoEnrichment,
        Kind,
        MinimumDataset,
        Observation,
        TriageClass,
        TriageDecision,
        Vertical,
    )

    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    cutoff = now - timedelta(days=int(lookback_days))

    try:
        vertical_enum = Vertical(vertical)
    except ValueError as exc:
        raise ValueError(
            f"unknown vertical {vertical!r}; expected one of vbd/heat/both/neither"
        ) from exc

    # ---- Load the observation property + edge bags from the kg ------------
    obs_rows = conn.execute(
        """
        SELECT n.node_id
        FROM kg.node n
        WHERE n.node_type = 'observation'
        """
    ).fetchall()
    obs_ids = [r[0] for r in obs_rows]
    if not obs_ids:
        return []

    placeholders = ", ".join(["?"] * len(obs_ids))
    prop_rows = conn.execute(
        f"""
        SELECT node_id, key, value_text, value_num
        FROM kg.property
        WHERE node_id IN ({placeholders})
        """,
        obs_ids,
    ).fetchall()
    props: dict[str, dict[str, Any]] = defaultdict(dict)
    for nid, key, vt, vn in prop_rows:
        if vt is not None:
            props[nid][key] = vt
        elif vn is not None:
            props[nid][key] = vn

    edge_rows = conn.execute(
        f"""
        SELECT subject_id, predicate, object_id
        FROM kg.edge
        WHERE subject_id IN ({placeholders})
          AND predicate IN ('colocatedWith', 'reportsAbout')
        """,
        obs_ids,
    ).fetchall()
    edges_by_obs: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for sid, pred, oid in edge_rows:
        edges_by_obs[sid].append((pred, oid))

    # ---- Reconstruct Observations the detector can chew on ----------------
    observations: list[Observation] = []
    for nid in obs_ids:
        p = props.get(nid, {})
        reported_at = p.get("reported_at")
        # Skip observations we can't time-stamp; the detector silently
        # drops them anyway, but filtering here keeps the cutoff tight.
        ts_str = _coerce_str(reported_at)
        ts = _parse_ts(ts_str)
        if ts is None:
            continue
        if ts < cutoff or ts > now:
            continue

        v_text = p.get("vertical")
        try:
            obs_vert = Vertical(v_text) if v_text else vertical_enum
        except ValueError:
            obs_vert = vertical_enum

        postal_code = _coerce_str(p.get("postal_code"))
        edges = edges_by_obs.get(nid, [])

        # Geo: prefer an explicit zcta property; else fall back to postal_code.
        zcta = _coerce_str(p.get("zcta")) or postal_code

        obs_county_id: Optional[str] = None
        candidate_pathogens: list[CandidatePathogen] = []
        for pred, oid in edges:
            if pred == "colocatedWith" and oid.startswith("county."):
                obs_county_id = oid
            elif pred == "reportsAbout" and oid.startswith("pathogen."):
                candidate_pathogens.append(
                    CandidatePathogen(pathogen_id=oid, score=1.0)
                )

        # County filter: skip observations that don't match the requested
        # county (we still load them all up front because the detector
        # uses the full set for its state-level baseline).
        if county_id is not None and obs_county_id != county_id:
            continue

        triage: Optional[TriageDecision] = None
        if candidate_pathogens:
            # Synthesise a minimal TriageDecision so the detector can
            # pick a dominant pathogen hint. We don't try to recover the
            # canonical triage_class -- that's the Triage Agent's job
            # and the detector only reads `candidate_pathogens` here.
            triage = TriageDecision(
                vertical=obs_vert,
                triage_class=TriageClass.CHECK_IN_ONLY,
                rationale="reconstructed from kg.edge",
                candidate_pathogens=candidate_pathogens,
            )

        observations.append(
            Observation(
                observation_id=nid,
                kind=Kind.MCP_PULL,
                vertical=obs_vert,
                received_at=ts.isoformat(),
                dataset=MinimumDataset(general=GeneralClass(postal_code=postal_code)),
                geo=GeoEnrichment(zcta=zcta, county_id=obs_county_id) if zcta else None,
                triage=triage,
            )
        )

    if not observations:
        return []

    detector = ClusterDetectionAgent()
    alerts = detector.run(observations, now=now)
    # Keep only the alerts for the requested vertical -- the detector
    # may have scanned both verticals because observations with
    # vertical=both fan out into both.
    out: list[dict] = []
    for a in alerts:
        if a.vertical.value != vertical_enum.value:
            continue
        if county_id is not None and a.county_id != county_id:
            continue
        out.append(
            {
                "zcta": a.zcta,
                "county_id": a.county_id,
                "lookback_window": {
                    "window_start": a.window_start,
                    "window_end": a.window_end,
                    "baseline_window_start": a.baseline_window_start,
                    "baseline_window_end": a.baseline_window_end,
                },
                "observed": a.observed,
                "expected": a.expected,
                "tier1_score": a.tier1_score,
                "tier2_posterior": a.tier2_posterior,
                "severity": _severity_from_posterior(a.tier2_posterior),
                "alert_status": "alert",
                "pathogen_hint": a.pathogen_hint,
                "historical_match": a.historical_match,
                "rule_tripped": a.rule_tripped,
                "observation_ids": a.observation_ids,
            }
        )
    return out


def _severity_from_posterior(p: Optional[float]) -> str:
    if p is None:
        return "moderate"
    if p >= 0.99:
        return "critical"
    if p >= 0.95:
        return "high"
    return "moderate"


def _parse_ts(s: Any) -> Optional[datetime]:
    if s is None:
        return None
    try:
        ts = datetime.fromisoformat(str(s))
    except (ValueError, TypeError):
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def _coerce_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)
