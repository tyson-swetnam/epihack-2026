"""Aggregation queries over ``kg.node(node_type='observation')`` and the
agent-runtime audit views.

These are the heavier rollups the dashboard-style consumers want
(weekly counts bucketed by county+pathogen, per-observation timeliness
intervals, full-cluster scans) without having to issue a custom
``kg_sql`` query each time.

All functions are synchronous; the ``server`` layer wraps them with
``asyncio.to_thread`` so a slow scan never blocks the MCP event loop.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

import duckdb


# ---------------------------------------------------------------------------
# 1. Observations bucketed by (iso_week, county_id, pathogen_id)
# ---------------------------------------------------------------------------
# Severity rank for tc.severity values; we collapse the per-cell list of
# triage classes down to a single "worst severity seen" string by picking
# the max along this ranking.
_SEVERITY_RANK: dict[str, int] = {
    "low": 1,
    "moderate": 2,
    "high": 3,
    "critical": 4,
}


def _max_severity(values: list[str]) -> Optional[str]:
    best: Optional[str] = None
    best_rank = -1
    for v in values:
        if not v:
            continue
        r = _SEVERITY_RANK.get(v, 0)
        if r > best_rank:
            best_rank = r
            best = v
    return best


def observations_by_window(
    conn: duckdb.DuckDBPyConnection,
    start_date: str,
    end_date: str,
    vertical: Optional[str] = None,
    county_id: Optional[str] = None,
    pathogen_id: Optional[str] = None,
) -> list[dict]:
    """Server-side rollup of ``kg.node(node_type='observation')``.

    Buckets observations by ``(iso_week, county_id, pathogen_id)`` and
    returns ``observation_count``, ``severity_max``, and a
    ``triage_class_breakdown`` map per cell.

    * ``start_date`` / ``end_date`` -- inclusive ISO-8601 date strings.
      The `reported_at` property is parsed; observations with no
      `reported_at` fall back to ``created_at`` on the node row.
    * Optional ``vertical`` filters on the ``vertical`` property
      (``vbd`` / ``heat`` / ``both`` / ``neither``).
    * Optional ``county_id`` filters on the ``colocatedWith`` edge.
    * Optional ``pathogen_id`` filters on the ``reportsAbout`` edge.

    The resulting rows are sorted by ``(iso_week, county_id, pathogen_id)``
    so a downstream chart can stream them without re-sorting.
    """
    # The query is built as a single CTE chain so we can join the
    # property bag (per-key column pivot) against the two edge tables
    # in a single pass over ``kg.edge``.
    sql = """
        WITH obs AS (
            SELECT
                n.node_id           AS observation_id,
                n.created_at        AS created_at
            FROM kg.node n
            WHERE n.node_type = 'observation'
        ),
        prop_pivot AS (
            SELECT
                node_id,
                MAX(CASE WHEN key = 'reported_at' THEN value_text END) AS reported_at,
                MAX(CASE WHEN key = 'vertical'    THEN value_text END) AS vertical
            FROM kg.property
            WHERE node_id IN (SELECT observation_id FROM obs)
            GROUP BY node_id
        ),
        county_link AS (
            SELECT subject_id AS observation_id, object_id AS county_id
            FROM kg.edge
            WHERE predicate = 'colocatedWith'
              AND object_id LIKE 'county.%'
              AND subject_id IN (SELECT observation_id FROM obs)
        ),
        pathogen_link AS (
            SELECT subject_id AS observation_id, object_id AS pathogen_id
            FROM kg.edge
            WHERE predicate = 'reportsAbout'
              AND object_id LIKE 'pathogen.%'
              AND subject_id IN (SELECT observation_id FROM obs)
        ),
        triage_link AS (
            SELECT
                e.subject_id        AS observation_id,
                e.object_id         AS triage_class,
                sev.value_text      AS severity
            FROM kg.edge e
            LEFT JOIN kg.property sev
                   ON sev.node_id = e.object_id AND sev.key = 'severity'
            WHERE e.predicate = 'gradedAs'
              AND e.subject_id IN (SELECT observation_id FROM obs)
        )
        SELECT
            o.observation_id,
            COALESCE(p.reported_at, CAST(o.created_at AS VARCHAR)) AS ts_text,
            p.vertical,
            c.county_id,
            pa.pathogen_id,
            t.triage_class,
            t.severity
        FROM obs o
        LEFT JOIN prop_pivot   p  ON p.node_id    = o.observation_id
        LEFT JOIN county_link  c  ON c.observation_id = o.observation_id
        LEFT JOIN pathogen_link pa ON pa.observation_id = o.observation_id
        LEFT JOIN triage_link  t  ON t.observation_id = o.observation_id
    """

    rows = conn.execute(sql).fetchall()
    cols = [
        "observation_id",
        "ts_text",
        "vertical",
        "county_id",
        "pathogen_id",
        "triage_class",
        "severity",
    ]
    raw = [dict(zip(cols, r)) for r in rows]

    try:
        start_ts = _parse_date(start_date, end_of_day=False)
        end_ts = _parse_date(end_date, end_of_day=True)
    except ValueError as exc:
        raise ValueError(f"bad start_date/end_date: {exc}") from exc

    # An observation can have multiple county / pathogen / triage edges;
    # we expand the cartesian per row but de-dup the observation_id when
    # tallying counts so a county-only filter doesn't double-count an
    # observation that happens to have two pathogen edges.
    cell_obs: dict[tuple[str, Optional[str], Optional[str]], set[str]] = defaultdict(set)
    cell_triage: dict[tuple[str, Optional[str], Optional[str]], dict[str, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    cell_severity: dict[tuple[str, Optional[str], Optional[str]], list[str]] = defaultdict(list)
    cell_obs_triage_seen: dict[
        tuple[str, Optional[str], Optional[str]], set[tuple[str, str]]
    ] = defaultdict(set)

    for row in raw:
        ts = _parse_ts(row["ts_text"])
        if ts is None:
            continue
        if ts < start_ts or ts > end_ts:
            continue
        if vertical is not None and row["vertical"] != vertical:
            continue
        if county_id is not None and row["county_id"] != county_id:
            continue
        if pathogen_id is not None and row["pathogen_id"] != pathogen_id:
            continue

        iso = ts.isocalendar()
        week = f"{iso.year:04d}-W{iso.week:02d}"
        key = (week, row["county_id"], row["pathogen_id"])
        cell_obs[key].add(row["observation_id"])
        tc = row["triage_class"]
        if tc:
            # Avoid double-counting a (observation, triage_class) pair when
            # the cartesian join expands it across multiple county/pathogen
            # edges within the same cell.
            stamp = (row["observation_id"], tc)
            if stamp not in cell_obs_triage_seen[key]:
                cell_obs_triage_seen[key].add(stamp)
                cell_triage[key][tc] += 1
                sev = row["severity"]
                if sev:
                    cell_severity[key].append(sev)

    def _sort_key(k: tuple[str, Optional[str], Optional[str]]) -> tuple:
        week, cid, pid = k
        # Sort None last by mapping it to a sentinel "~" string that
        # comes after any real slug alphabetically.
        return (week, cid or "~", pid or "~")

    out: list[dict] = []
    for key in sorted(cell_obs.keys(), key=_sort_key):
        week, cid, pid = key
        out.append(
            {
                "iso_week": week,
                "county_id": cid,
                "pathogen_id": pid,
                "observation_count": len(cell_obs[key]),
                "severity_max": _max_severity(cell_severity[key]),
                "triage_class_breakdown": dict(cell_triage[key]),
            }
        )
    return out


def _parse_date(s: str, *, end_of_day: bool) -> datetime:
    """Accept 'YYYY-MM-DD' or a full ISO datetime."""
    s = s.strip()
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        d = datetime.fromisoformat(s)
        if end_of_day:
            d = d.replace(hour=23, minute=59, second=59, microsecond=999_999)
        return d.replace(tzinfo=timezone.utc)
    ts = datetime.fromisoformat(s)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


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


# ---------------------------------------------------------------------------
# 2. Observation milestone intervals (per-observation timeliness pivot)
# ---------------------------------------------------------------------------
def milestone_intervals(
    conn: duckdb.DuckDBPyConnection,
    start_date: str,
    end_date: str,
    vertical: Optional[str] = None,
    agency: Optional[str] = None,
) -> list[dict]:
    """Per-observation timeliness milestones with cost summary.

    Joins ``kg.v_observation_timeliness`` against ``kg.node`` and the
    observation property bag, then folds in the per-day-per-agent rollup
    from ``kg.v_agent_run_cost`` (summed across the run window for each
    observation's `detect_at` day).

    Returns one row per observation with:

        observation_id,
        vertical,
        responsible_vector_control_agency,
        detect_at, notify_at, verify_at_provisional, lab_at_provisional, respond_at,
        detect_to_notify_min, notify_to_verify_min, verify_to_lab_min, lab_to_respond_min,
        cost_usd_total, run_count, prompt_tokens_total, completion_tokens_total
    """
    try:
        start_ts = _parse_date(start_date, end_of_day=False)
        end_ts = _parse_date(end_date, end_of_day=True)
    except ValueError as exc:
        raise ValueError(f"bad start_date/end_date: {exc}") from exc

    # Pull the timeliness view rows + property bag in a single CTE. We
    # then post-filter in Python so vertical / agency are matched against
    # the property-bag values without having to PIVOT them in SQL.
    sql = """
        WITH props AS (
            SELECT
                node_id,
                MAX(CASE WHEN key = 'vertical' THEN value_text END) AS vertical,
                MAX(CASE WHEN key = 'responsible_vector_control_agency'
                                                THEN value_text END) AS agency
            FROM kg.property
            GROUP BY node_id
        )
        SELECT
            v.observation_id,
            p.vertical,
            p.agency,
            v.detect_at,
            v.notify_at,
            v.verify_at_provisional,
            v.lab_at_provisional,
            v.respond_at,
            v.detect_to_notify_min,
            v.notify_to_verify_min,
            v.verify_to_lab_min,
            v.lab_to_respond_min,
            v.detect_to_respond_min
        FROM kg.v_observation_timeliness v
        LEFT JOIN props p ON p.node_id = v.observation_id
    """
    rows = conn.execute(sql).fetchall()
    cols = [
        "observation_id",
        "vertical",
        "agency",
        "detect_at",
        "notify_at",
        "verify_at_provisional",
        "lab_at_provisional",
        "respond_at",
        "detect_to_notify_min",
        "notify_to_verify_min",
        "verify_to_lab_min",
        "lab_to_respond_min",
        "detect_to_respond_min",
    ]
    raw = [dict(zip(cols, r)) for r in rows]

    # Cost rollup keyed by observation_id; sum across whatever days that
    # observation's runs spanned.
    cost_sql = """
        SELECT
            ar.observation_id,
            COALESCE(SUM(ar.cost_usd),         0.0) AS cost_usd_total,
            COUNT(*)                                 AS run_count,
            COALESCE(SUM(ar.prompt_tokens),     0)  AS prompt_tokens_total,
            COALESCE(SUM(ar.completion_tokens), 0)  AS completion_tokens_total,
            COALESCE(SUM(ar.cache_read_tokens), 0)  AS cache_read_tokens_total,
            COALESCE(SUM(ar.cache_creation_tokens), 0) AS cache_creation_tokens_total
        FROM kg.agent_run ar
        WHERE ar.observation_id IS NOT NULL
        GROUP BY ar.observation_id
    """
    cost_rows = conn.execute(cost_sql).fetchall()
    cost_cols = [
        "observation_id",
        "cost_usd_total",
        "run_count",
        "prompt_tokens_total",
        "completion_tokens_total",
        "cache_read_tokens_total",
        "cache_creation_tokens_total",
    ]
    cost_by_obs = {
        r[0]: dict(zip(cost_cols, r)) for r in cost_rows
    }

    out: list[dict] = []
    for row in raw:
        detect_at = row["detect_at"]
        if detect_at is None:
            continue
        # detect_at lands in the response window?
        ts = _coerce_dt(detect_at)
        if ts is None or ts < start_ts or ts > end_ts:
            continue
        if vertical is not None and row["vertical"] != vertical:
            continue
        if agency is not None and row["agency"] != agency:
            continue

        cost = cost_by_obs.get(row["observation_id"], {})
        out.append(
            {
                "observation_id": row["observation_id"],
                "vertical": row["vertical"],
                "responsible_vector_control_agency": row["agency"],
                "detect_at": _iso(row["detect_at"]),
                "notify_at": _iso(row["notify_at"]),
                "verify_at_provisional": _iso(row["verify_at_provisional"]),
                "lab_at_provisional": _iso(row["lab_at_provisional"]),
                "respond_at": _iso(row["respond_at"]),
                "detect_to_notify_min": row["detect_to_notify_min"],
                "notify_to_verify_min": row["notify_to_verify_min"],
                "verify_to_lab_min": row["verify_to_lab_min"],
                "lab_to_respond_min": row["lab_to_respond_min"],
                "detect_to_respond_min": row["detect_to_respond_min"],
                "cost_usd_total": cost.get("cost_usd_total", 0.0),
                "run_count": cost.get("run_count", 0),
                "prompt_tokens_total": cost.get("prompt_tokens_total", 0),
                "completion_tokens_total": cost.get("completion_tokens_total", 0),
                "cache_read_tokens_total": cost.get("cache_read_tokens_total", 0),
                "cache_creation_tokens_total": cost.get("cache_creation_tokens_total", 0),
            }
        )
    out.sort(key=lambda r: (r["detect_at"] or "", r["observation_id"]))
    return out


def _coerce_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return _parse_ts(value)


def _iso(value: Any) -> Optional[str]:
    dt = _coerce_dt(value)
    return dt.isoformat() if dt else None
