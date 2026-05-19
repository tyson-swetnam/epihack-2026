"""ClusterDetectionAgent -- SaTScan-flavoured Poisson scan stub.

Production implementation runs a proper space-time scan statistic
(SaTScan / R-SatScan) on the rolling window of ``observation`` nodes.
The stub here implements a one-dimensional Poisson scan per ZCTA
that's good enough for the worked Scenario D cluster
(``4 hantavirus-compatible observations in Coconino over 10 days``).
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone

from .contracts import ClusterAlert, Observation, Vertical


class ClusterDetectionAgent:
    name = "cluster_detection"

    def __init__(
        self,
        window_days: int = 10,
        baseline_per_zcta_per_day: float = 0.05,
        min_observed: int = 3,
        llr_threshold: float = 1.0,
    ) -> None:
        self.window_days = window_days
        self.baseline_per_zcta_per_day = baseline_per_zcta_per_day
        self.min_observed = min_observed
        self.llr_threshold = llr_threshold

    def run(
        self,
        observations: Iterable[Observation],
        now: datetime | None = None,
    ) -> list[ClusterAlert]:
        now = now or datetime.now(timezone.utc)
        window_start = now - timedelta(days=self.window_days)
        # Per-vertical, per-ZCTA buckets (verticals are NOT merged per plan/03).
        buckets: dict[tuple[Vertical, str], list[str]] = defaultdict(list)
        for obs in observations:
            zcta = (obs.geo.zcta if obs.geo else None) or obs.dataset.general.postal_code
            if not zcta:
                continue
            try:
                ts = datetime.fromisoformat(obs.received_at)
            except ValueError:
                continue
            if ts < window_start:
                continue
            buckets[(obs.vertical, zcta)].append(obs.observation_id)

        alerts: list[ClusterAlert] = []
        expected = self.baseline_per_zcta_per_day * self.window_days
        for (vertical, zcta), obs_ids in buckets.items():
            observed = len(obs_ids)
            if observed < self.min_observed:
                continue
            llr = _poisson_log_likelihood_ratio(observed, expected)
            if llr < self.llr_threshold:
                continue
            alerts.append(
                ClusterAlert(
                    vertical=vertical,
                    zcta=zcta,
                    observation_ids=obs_ids,
                    window_start=window_start.isoformat(),
                    window_end=now.isoformat(),
                    expected=expected,
                    observed=observed,
                    log_likelihood=llr,
                )
            )
        return alerts


def _poisson_log_likelihood_ratio(observed: int, expected: float) -> float:
    """Kulldorff-style scan statistic ratio for one zone."""
    if observed == 0 or expected <= 0:
        return 0.0
    return observed * math.log(observed / expected) - (observed - expected)


__all__ = ["ClusterDetectionAgent"]
