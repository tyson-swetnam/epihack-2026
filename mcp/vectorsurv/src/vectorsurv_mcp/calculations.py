"""Standard vector-surveillance calculations.

Mirrors the calculations in the `vectorsurvR` R package
(`getAbundance`, `getInfectionRate`, `getVectorIndex`) so that an
LLM client can compute the same values that VectorSurv Gateway
shows in its UI.

References:
- https://vectorsurv.org/docs/tools/calculators/vector-index/
- Biggerstaff, Bayesian / MLE pooled-prevalence estimators
  (PooledInfRate / pooltestr).
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Iterable, Mapping


# ---------------------------------------------------------------------- helpers
def _bucket(record: Mapping, interval: str) -> str:
    """Bucket a collection by the configured interval (collection_date,
    Week, Biweek, Month)."""
    date = record.get("collection_date") or record.get("date")
    if not date:
        return "unknown"
    if interval == "collection_date":
        return str(date)
    # Date is ISO-like 'YYYY-MM-DD'.
    y, m, d = (int(x) for x in str(date)[:10].split("-"))
    if interval == "Month":
        return f"{y}-{m:02d}"
    # day-of-year for Week / Biweek
    doy = (
        sum([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][: m - 1])
        + (1 if (m > 2 and y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 0)
        + d
    )
    if interval == "Week":
        week = (doy - 1) // 7 + 1
        return f"{y}-W{week:02d}"
    if interval == "Biweek":
        biweek = (doy - 1) // 14 + 1
        return f"{y}-B{biweek:02d}"
    raise ValueError(f"Unknown interval {interval!r}")


# ----------------------------------------------------------------- abundance
def abundance(
    collections: Iterable[Mapping],
    interval: str = "Biweek",
    species: str | None = None,
    trap: str | None = None,
) -> list[dict]:
    """Total arthropods collected / total trap-nights, per interval.

    A collection record is expected to carry at least:
        collection_date, num_count, num_trap, trap_nights
        (or trap_nights derivable from num_trap * num_nights)
        species_display_name, trap_acronym
    """
    buckets: dict[str, dict[str, float]] = defaultdict(
        lambda: {"count": 0.0, "trap_nights": 0.0}
    )
    for c in collections:
        if species and c.get("species_display_name") != species:
            continue
        if trap and c.get("trap_acronym") != trap:
            continue
        key = _bucket(c, interval)
        tn = (
            c.get("trap_nights")
            or (c.get("num_trap", 1) * c.get("num_nights", 1))
            or 1
        )
        buckets[key]["count"] += float(c.get("num_count", 0))
        buckets[key]["trap_nights"] += float(tn)
    out = []
    for k, v in sorted(buckets.items()):
        out.append(
            {
                "interval": k,
                "count": v["count"],
                "trap_nights": v["trap_nights"],
                "abundance": v["count"] / v["trap_nights"] if v["trap_nights"] else 0.0,
            }
        )
    return out


# ----------------------------------------------------------- infection rate
def infection_rate(
    pools: Iterable[Mapping],
    target_disease: str,
    interval: str = "Biweek",
    method: str = "mir",
    scale: float = 1000.0,
    species: str | None = None,
    trap: str | None = None,
) -> list[dict]:
    """Estimate arbovirus infection rate per `scale` mosquitoes per interval.

    Methods:
        mir     -- Minimum Infection Rate (positive pools / total mosquitoes)
        bc-mle  -- bias-corrected MLE (Hepworth small-sample correction)

    A pool record is expected to carry:
        collection_date, num_count (mosquitoes in pool),
        target_acronym (disease), test_status ("Positive"/"Negative"),
        species_display_name, trap_acronym
    """
    method = method.lower()
    buckets: dict[str, dict[str, float]] = defaultdict(
        lambda: {"pos": 0, "n_pools": 0, "mosquitoes": 0}
    )
    for p in pools:
        if p.get("target_acronym") != target_disease:
            continue
        if species and p.get("species_display_name") != species:
            continue
        if trap and p.get("trap_acronym") != trap:
            continue
        key = _bucket(p, interval)
        n = int(p.get("num_count", 0))
        is_pos = str(p.get("test_status", "")).lower().startswith("pos")
        buckets[key]["pos"] += 1 if is_pos else 0
        buckets[key]["n_pools"] += 1
        buckets[key]["mosquitoes"] += n
    out = []
    for k, v in sorted(buckets.items()):
        if method == "mir":
            ir = scale * v["pos"] / v["mosquitoes"] if v["mosquitoes"] else 0.0
        elif method in {"bc-mle", "mle"}:
            ir = _bc_mle_infection_rate(
                positives=int(v["pos"]),
                pools=int(v["n_pools"]),
                mosquitoes=int(v["mosquitoes"]),
                scale=scale,
            )
        else:
            raise ValueError(f"Unknown method {method!r}")
        out.append(
            {
                "interval": k,
                "positive_pools": v["pos"],
                "total_pools": v["n_pools"],
                "mosquitoes_tested": v["mosquitoes"],
                "infection_rate": ir,
                "method": method,
                "scale": scale,
                "target": target_disease,
            }
        )
    return out


def _bc_mle_infection_rate(
    positives: int, pools: int, mosquitoes: int, scale: float
) -> float:
    """Bias-corrected MLE under equal-pool-size assumption.

    For unequal pool sizes, this reduces to the average; this is the
    same simplification PooledInfRate makes when the pool-size
    variance is small. Suitable as a default; switch to MIR or a
    full pooltestr fit for high-precision work.
    """
    if mosquitoes == 0 or pools == 0:
        return 0.0
    if positives == 0:
        return 0.0
    if positives == pools:
        # Saturated: prevalence is bounded; fall back to MIR upper bound.
        return scale * positives / mosquitoes
    m = mosquitoes / pools  # average pool size
    # Naive MLE: p = 1 - (1 - x/n)^(1/m) where x = positives, n = pools
    p_hat = 1.0 - math.pow(1.0 - positives / pools, 1.0 / m)
    # First-order bias correction (Hepworth 2005, equal-sized pools)
    p_bc = p_hat - p_hat * (1 - p_hat) ** m * (
        (1 - p_hat) ** m - 1 + m * p_hat
    ) / (2 * pools * m * (1 - (1 - p_hat) ** m))
    return scale * max(p_bc, 0.0)


# ------------------------------------------------------------- vector index
def vector_index(
    collections: Iterable[Mapping],
    pools: Iterable[Mapping],
    target_disease: str,
    interval: str = "Biweek",
    method: str = "mir",
    scale: float = 1000.0,
    species: str | None = None,
    trap: str | None = None,
) -> list[dict]:
    """Vector Index = Infection Rate × Abundance per interval.

    Per the Maricopa County / VectorSurv definition, the Vector Index
    is the *expected number of infected mosquitoes per trap-night*.
    """
    ab = {row["interval"]: row for row in abundance(collections, interval, species, trap)}
    ir = {row["interval"]: row for row in infection_rate(
        pools, target_disease, interval, method, scale, species, trap
    )}
    out = []
    for k in sorted(set(ab) | set(ir)):
        a = ab.get(k, {})
        i = ir.get(k, {})
        out.append(
            {
                "interval": k,
                "abundance": a.get("abundance", 0.0),
                "infection_rate": i.get("infection_rate", 0.0),
                "vector_index": a.get("abundance", 0.0)
                * i.get("infection_rate", 0.0)
                / scale,
                "target": target_disease,
                "method": method,
            }
        )
    return out
