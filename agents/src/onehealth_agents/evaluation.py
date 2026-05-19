"""Phase-4 evaluation harness for the OneHealth eight-agent pipeline.

Scores the system against the Figure-3 timeliness milestones
(`figures/03-outbreak-timeliness-metrics.md`) by joining the
``kg.v_observation_timeliness`` pivot view in ``schema/deep/audit.sql``
against the historical Arizona outbreak baselines pre-extracted from
``schema/deep/outbreaks.sql`` into ``evaluation/baseline-2024.json``.

The Phase-3 success criterion from ``plan/05-roadmap.md`` is:

    During the heat season and the WNV season, the median Detect to
    Notify interval for reports flowing through the app is at least
    30% shorter than the 2024 baseline for the same counties.

`EvaluationReport` is the structured artifact this module emits;
`render_markdown(report)` turns it into a printable scorecard that
drops straight into a hackathon readout.

This module is intentionally **pure-stdlib** plus pydantic so the
report can be computed in any environment that already loads the
agents package -- no DuckDB dependency for the offline-row path,
which is what `agents/tests/test_evaluation.py` exercises.
"""

from __future__ import annotations

import json
import os
import statistics
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field

from .contracts import Vertical


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
#: Pre-extracted baseline lives at ``<repo>/evaluation/baseline-<year>.json``.
#: Computed once at import time (see :func:`_default_baseline_path`).
_REPO_ROOT_CANDIDATES = (
    # When the package is editable-installed from agents/src/onehealth_agents,
    # the repo root is two parents up from this file's parent (the package).
    Path(__file__).resolve().parents[3],
    # Fallback for installed wheels: $CWD.
    Path.cwd(),
)

#: Agent -> Figure-3 milestone mapping (mirrors schema/deep/audit.sql header).
AGENT_TO_MILESTONE: dict[str, str] = {
    "intake": "detect",
    "validation": "notify",
    "triage": "verify",
    "enrichment": "lab",
    "notification": "respond",
}

#: Adjacent-milestone pairs the scorecard reports on, in canonical order.
MILESTONE_PAIRS: tuple[tuple[str, str], ...] = (
    ("detect", "notify"),
    ("notify", "verify"),
    ("verify", "lab"),
    ("lab", "respond"),
    ("detect", "respond"),
)

#: Phase-3 success-criterion threshold for Detect -> Notify (pct shorter).
PHASE3_DETECT_TO_NOTIFY_TARGET_PCT_SHORTER: float = 30.0

#: Sentinel used in the scorecard when an interval cannot be computed.
_UNAVAILABLE = "n/a"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _default_baseline_path(year: int) -> Path:
    """Locate ``evaluation/baseline-<year>.json`` next to the repo root.

    Tries the editable-install layout first, then $CWD. Raises
    ``FileNotFoundError`` if neither resolves to an existing file.
    """
    for root in _REPO_ROOT_CANDIDATES:
        candidate = root / "evaluation" / f"baseline-{year}.json"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"Could not locate evaluation/baseline-{year}.json under any of: "
        f"{[str(p) for p in _REPO_ROOT_CANDIDATES]}"
    )


def _percentile(values: Sequence[float], pct: float) -> float:
    """Linear-interpolation percentile, pure stdlib (no numpy).

    Mirrors numpy's default linear method so the harness stays
    dependency-free without surprising callers.
    """
    if not values:
        raise ValueError("percentile of empty sequence")
    if pct < 0.0 or pct > 100.0:
        raise ValueError(f"pct must be 0..100, got {pct}")
    s = sorted(values)
    if len(s) == 1:
        return float(s[0])
    k = (pct / 100.0) * (len(s) - 1)
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    frac = k - lo
    return float(s[lo] + (s[hi] - s[lo]) * frac)


def _parse_ts(value: str | datetime | None) -> datetime | None:
    """Coerce a value that may be ISO 8601 text, datetime, or None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    # DuckDB returns timestamps as strings or datetime depending on driver.
    try:
        # Trim trailing 'Z' if present; fromisoformat does not accept it pre-3.11.
        text = value.rstrip("Z")
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        return None


def _interval_min(start: datetime | None, end: datetime | None) -> float | None:
    if start is None or end is None:
        return None
    delta_min = (end - start).total_seconds() / 60.0
    # Negative deltas indicate clock skew / out-of-order rows; treat as missing.
    if delta_min < 0:
        return None
    return delta_min


def _pct_change(current: float | None, baseline: float | None) -> float | None:
    """Return ``(current - baseline) / baseline * 100``.

    Positive means current is **larger** than baseline (i.e. slower).
    Negative means **shorter** (faster), which is the desired direction.
    """
    if current is None or baseline is None or baseline == 0:
        return None
    return ((current - baseline) / baseline) * 100.0


def _pct_shorter(current: float | None, baseline: float | None) -> float | None:
    """Return ``(baseline - current) / baseline * 100`` -- positive is good."""
    if current is None or baseline is None or baseline == 0:
        return None
    return ((baseline - current) / baseline) * 100.0


# ---------------------------------------------------------------------------
# Pydantic contracts
# ---------------------------------------------------------------------------
class EvaluationConfig(BaseModel):
    """Inputs to :meth:`MilestoneEvaluator.evaluate`."""

    model_config = ConfigDict(extra="forbid")

    start_date: date
    end_date: date
    verticals: list[Vertical] = Field(default_factory=lambda: [Vertical.VBD, Vertical.HEAT])
    agencies: list[str] = Field(
        default_factory=list,
        description=(
            "Resource slugs (e.g. 'resource.adhs', 'resource.mcdph_heat'). "
            "Empty list means 'all agencies present in the agent_run audit table'."
        ),
    )
    historical_baseline_year: int = 2024


class TimelinessRow(BaseModel):
    """One observation's worth of milestone timestamps.

    Mirrors a row of ``kg.v_observation_timeliness`` plus the agency the
    observation was routed to (the view itself is agency-agnostic; the
    evaluator joins to the geo-enrichment property bag to attach one).
    """

    model_config = ConfigDict(extra="forbid")

    observation_id: str
    vertical: Vertical
    agency: str = Field(
        default="unspecified",
        description="Resource slug (e.g. 'resource.adhs'); 'unspecified' for unrouted.",
    )
    detect_at: Optional[datetime] = None
    notify_at: Optional[datetime] = None
    verify_at: Optional[datetime] = None
    lab_at: Optional[datetime] = None
    respond_at: Optional[datetime] = None

    def interval_min(self, start: str, end: str) -> float | None:
        ts_start = getattr(self, f"{start}_at", None)
        ts_end = getattr(self, f"{end}_at", None)
        return _interval_min(ts_start, ts_end)


class IntervalStat(BaseModel):
    """Per-pair summary statistic for one agency / vertical / milestone pair."""

    model_config = ConfigDict(extra="forbid")

    pair: str = Field(description="e.g. 'detect_to_notify'.")
    n: int = Field(description="Number of observations contributing to this stat.")
    median_min: Optional[float] = None
    p25_min: Optional[float] = None
    p75_min: Optional[float] = None
    iqr_min: Optional[float] = None
    baseline_min: Optional[float] = Field(
        default=None,
        description=(
            "Historical baseline median for the same pair. "
            "Pulled from evaluation/baseline-<year>.json."
        ),
    )
    pct_change_vs_baseline: Optional[float] = Field(
        default=None,
        description=(
            "(median - baseline) / baseline * 100. "
            "Negative = pipeline is faster than the counterfactual."
        ),
    )
    pct_shorter_vs_baseline: Optional[float] = Field(
        default=None,
        description="Positive = faster than baseline; mirrors plan/05-roadmap success-criterion phrasing.",
    )


class AgencyVerticalScorecard(BaseModel):
    """All five Figure-3 pair-stats for one (agency, vertical) cell."""

    model_config = ConfigDict(extra="forbid")

    agency: str
    vertical: Vertical
    n_observations: int
    intervals: list[IntervalStat] = Field(default_factory=list)

    def interval(self, pair: str) -> IntervalStat | None:
        return next((it for it in self.intervals if it.pair == pair), None)


class Phase3Verdict(BaseModel):
    """Pass/fail evaluation against the Phase-3 Detect-to-Notify target."""

    model_config = ConfigDict(extra="forbid")

    agency: str
    vertical: Vertical
    median_min: Optional[float] = None
    baseline_min: Optional[float] = None
    pct_shorter: Optional[float] = None
    target_pct_shorter: float = PHASE3_DETECT_TO_NOTIFY_TARGET_PCT_SHORTER
    passes: bool = False
    reason: str = ""


class EvaluationReport(BaseModel):
    """Top-level report produced by :meth:`MilestoneEvaluator.evaluate`."""

    model_config = ConfigDict(extra="forbid")

    config: EvaluationConfig
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    scorecards: list[AgencyVerticalScorecard] = Field(default_factory=list)
    phase3_verdicts: list[Phase3Verdict] = Field(default_factory=list)
    total_observations: int = 0
    baseline_source: str = Field(
        default="",
        description="Filesystem path to the JSON file the baseline was loaded from.",
    )

    def scorecard_for(self, agency: str, vertical: Vertical) -> AgencyVerticalScorecard | None:
        for sc in self.scorecards:
            if sc.agency == agency and sc.vertical == vertical:
                return sc
        return None


# ---------------------------------------------------------------------------
# Baseline loader
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Baseline:
    """A loaded baseline-<year>.json, indexed for fast lookup."""

    year: int
    source_path: str
    per_vertical_per_agency: dict[str, dict[str, dict[str, float | None]]]

    @classmethod
    def load(cls, path: str | Path) -> "Baseline":
        p = Path(path)
        with open(p, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        # Accept either ``per_vertical_per_agency`` (terse) or
        # ``per_vertical_per_agency_baseline`` (verbose, as written in
        # evaluation/baseline-2024.json) -- they mean the same thing.
        intervals = (
            data.get("per_vertical_per_agency_baseline")
            or data.get("per_vertical_per_agency")
            or {}
        )
        return cls(
            year=int(data.get("year", 0)),
            source_path=str(p),
            per_vertical_per_agency=intervals,
        )

    def interval(
        self,
        vertical: Vertical,
        agency: str,
        pair: str,
    ) -> float | None:
        v = self.per_vertical_per_agency.get(vertical.value, {})
        a = v.get(agency, {})
        key = f"{pair}_min"
        return a.get(key)


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------
class MilestoneEvaluator:
    """Joins ``kg.v_observation_timeliness`` against the chosen baseline.

    The evaluator has two entry points:

    * :meth:`evaluate` -- the public API; takes an :class:`EvaluationConfig`
      and (optionally) a DuckDB connection. If a connection is supplied,
      the evaluator runs the canonical SQL against
      ``kg.v_observation_timeliness`` plus the agency-routing properties.
      Otherwise it returns an empty report (useful for tests that drive
      it via :meth:`evaluate_rows`).
    * :meth:`evaluate_rows` -- the pure-function path; takes a
      pre-built sequence of :class:`TimelinessRow` and produces a report.
      This is what the offline tests use.
    """

    def __init__(
        self,
        *,
        connection: Any | None = None,
        baseline: Baseline | None = None,
        baseline_path: str | Path | None = None,
    ) -> None:
        self._con = connection
        self._explicit_baseline = baseline
        self._baseline_path_override = baseline_path

    # ---- baseline resolution ------------------------------------------------
    def _baseline_for(self, year: int) -> Baseline:
        if self._explicit_baseline is not None:
            return self._explicit_baseline
        path = (
            Path(self._baseline_path_override)
            if self._baseline_path_override
            else _default_baseline_path(year)
        )
        return Baseline.load(path)

    # ---- public API ---------------------------------------------------------
    def evaluate(self, config: EvaluationConfig) -> EvaluationReport:
        """Run the evaluation against the configured DuckDB connection.

        If no connection is wired, returns an empty report so callers
        in test environments do not have to spin up a database. Tests
        that want to assert numerics should call :meth:`evaluate_rows`
        directly.
        """
        baseline = self._baseline_for(config.historical_baseline_year)
        rows: list[TimelinessRow] = []
        if self._con is not None:
            rows = self._load_rows_from_connection(config)
        return self.evaluate_rows(config, rows, baseline=baseline)

    def evaluate_rows(
        self,
        config: EvaluationConfig,
        rows: Iterable[TimelinessRow],
        *,
        baseline: Baseline | None = None,
    ) -> EvaluationReport:
        """Compute the report from an in-memory row sequence."""
        baseline = baseline or self._baseline_for(config.historical_baseline_year)
        rows = list(rows)
        filtered = self._filter_rows(rows, config)

        scorecards = self._compute_scorecards(filtered, config, baseline)
        verdicts = self._compute_phase3_verdicts(scorecards, baseline)

        return EvaluationReport(
            config=config,
            scorecards=scorecards,
            phase3_verdicts=verdicts,
            total_observations=len(filtered),
            baseline_source=baseline.source_path,
        )

    # ---- internal: row loading ---------------------------------------------
    _SQL = """
    SELECT
        t.observation_id,
        COALESCE(vert.value_text, 'neither') AS vertical,
        COALESCE(ag.value_text, 'unspecified') AS agency,
        t.detect_at,
        t.notify_at,
        t.verify_at_provisional,
        t.lab_at_provisional,
        t.respond_at
    FROM kg.v_observation_timeliness t
    LEFT JOIN kg.property vert
        ON vert.node_id = t.observation_id AND vert.key = 'vertical'
    LEFT JOIN kg.property ag
        ON ag.node_id = t.observation_id AND ag.key = 'responsible_agency'
    WHERE
        (t.detect_at IS NULL OR t.detect_at >= ?)
        AND (t.detect_at IS NULL OR t.detect_at <= ?)
    """

    def _load_rows_from_connection(self, config: EvaluationConfig) -> list[TimelinessRow]:
        start_ts = datetime.combine(config.start_date, datetime.min.time(), tzinfo=timezone.utc)
        end_ts = datetime.combine(config.end_date, datetime.max.time(), tzinfo=timezone.utc)
        try:
            cursor = self._con.execute(self._SQL, (start_ts, end_ts))
            raw = cursor.fetchall()
        except Exception:
            # Schema may not be loaded (e.g. wildlife/heat seed-only DB);
            # an empty result keeps the harness running and clearly signals
            # "no audit data in the requested window" via total_observations=0.
            return []

        rows: list[TimelinessRow] = []
        for r in raw:
            (obs_id, vert_text, agency, det, notif, ver, lab, resp) = r
            try:
                vertical = Vertical(vert_text)
            except ValueError:
                vertical = Vertical.NEITHER
            rows.append(
                TimelinessRow(
                    observation_id=str(obs_id),
                    vertical=vertical,
                    agency=str(agency),
                    detect_at=_parse_ts(det),
                    notify_at=_parse_ts(notif),
                    verify_at=_parse_ts(ver),
                    lab_at=_parse_ts(lab),
                    respond_at=_parse_ts(resp),
                )
            )
        return rows

    # ---- internal: filtering -----------------------------------------------
    def _filter_rows(
        self,
        rows: Sequence[TimelinessRow],
        config: EvaluationConfig,
    ) -> list[TimelinessRow]:
        verticals = set(config.verticals)
        allowed_agencies = set(config.agencies) if config.agencies else None
        start = datetime.combine(
            config.start_date, datetime.min.time(), tzinfo=timezone.utc
        )
        end = datetime.combine(
            config.end_date, datetime.max.time(), tzinfo=timezone.utc
        )
        out: list[TimelinessRow] = []
        for r in rows:
            if r.vertical not in verticals:
                continue
            if allowed_agencies is not None and r.agency not in allowed_agencies:
                continue
            # An observation is in-window if its Detect timestamp falls
            # inside [start, end]. Rows with no Detect at all are dropped
            # because every milestone pair we report on requires it.
            if r.detect_at is None:
                continue
            if r.detect_at < start or r.detect_at > end:
                continue
            out.append(r)
        return out

    # ---- internal: stat computation ----------------------------------------
    def _compute_scorecards(
        self,
        rows: Sequence[TimelinessRow],
        config: EvaluationConfig,
        baseline: Baseline,
    ) -> list[AgencyVerticalScorecard]:
        # Group rows by (agency, vertical).
        buckets: dict[tuple[str, Vertical], list[TimelinessRow]] = {}
        for r in rows:
            buckets.setdefault((r.agency, r.vertical), []).append(r)

        # If the caller pinned a specific agency list, make sure every
        # (agency, vertical) cell shows up even with n=0 so the scorecard
        # is grid-shaped.
        if config.agencies:
            for agency in config.agencies:
                for vertical in config.verticals:
                    buckets.setdefault((agency, vertical), [])

        scorecards: list[AgencyVerticalScorecard] = []
        for (agency, vertical), bucket in sorted(
            buckets.items(), key=lambda kv: (kv[0][1].value, kv[0][0])
        ):
            intervals = self._compute_intervals(bucket, vertical, agency, baseline)
            scorecards.append(
                AgencyVerticalScorecard(
                    agency=agency,
                    vertical=vertical,
                    n_observations=len(bucket),
                    intervals=intervals,
                )
            )
        return scorecards

    def _compute_intervals(
        self,
        rows: Sequence[TimelinessRow],
        vertical: Vertical,
        agency: str,
        baseline: Baseline,
    ) -> list[IntervalStat]:
        out: list[IntervalStat] = []
        for start, end in MILESTONE_PAIRS:
            pair_key = f"{start}_to_{end}"
            values = [
                v for r in rows for v in (r.interval_min(start, end),) if v is not None
            ]
            baseline_min = baseline.interval(vertical, agency, pair_key)
            if not values:
                out.append(
                    IntervalStat(
                        pair=pair_key,
                        n=0,
                        baseline_min=baseline_min,
                    )
                )
                continue
            median_min = float(statistics.median(values))
            p25 = _percentile(values, 25.0)
            p75 = _percentile(values, 75.0)
            out.append(
                IntervalStat(
                    pair=pair_key,
                    n=len(values),
                    median_min=median_min,
                    p25_min=p25,
                    p75_min=p75,
                    iqr_min=p75 - p25,
                    baseline_min=baseline_min,
                    pct_change_vs_baseline=_pct_change(median_min, baseline_min),
                    pct_shorter_vs_baseline=_pct_shorter(median_min, baseline_min),
                )
            )
        return out

    def _compute_phase3_verdicts(
        self,
        scorecards: Sequence[AgencyVerticalScorecard],
        baseline: Baseline,
    ) -> list[Phase3Verdict]:
        verdicts: list[Phase3Verdict] = []
        target = PHASE3_DETECT_TO_NOTIFY_TARGET_PCT_SHORTER
        for sc in scorecards:
            it = sc.interval("detect_to_notify")
            if it is None or it.n == 0:
                verdicts.append(
                    Phase3Verdict(
                        agency=sc.agency,
                        vertical=sc.vertical,
                        baseline_min=baseline.interval(
                            sc.vertical, sc.agency, "detect_to_notify"
                        ),
                        passes=False,
                        reason="no Detect->Notify observations in window",
                    )
                )
                continue
            if it.baseline_min is None:
                verdicts.append(
                    Phase3Verdict(
                        agency=sc.agency,
                        vertical=sc.vertical,
                        median_min=it.median_min,
                        baseline_min=None,
                        passes=False,
                        reason="no historical baseline for this (vertical, agency)",
                    )
                )
                continue
            pct_shorter = it.pct_shorter_vs_baseline or 0.0
            passes = pct_shorter >= target
            verdicts.append(
                Phase3Verdict(
                    agency=sc.agency,
                    vertical=sc.vertical,
                    median_min=it.median_min,
                    baseline_min=it.baseline_min,
                    pct_shorter=pct_shorter,
                    target_pct_shorter=target,
                    passes=passes,
                    reason=(
                        f"{pct_shorter:.1f}% shorter vs {target:.0f}% target"
                        if passes
                        else f"only {pct_shorter:.1f}% shorter vs {target:.0f}% target"
                    ),
                )
            )
        return verdicts


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------
def _fmt_minutes(value: float | None) -> str:
    if value is None:
        return _UNAVAILABLE
    if value < 60:
        return f"{value:.1f} min"
    if value < 60 * 24:
        return f"{value / 60:.1f} h"
    return f"{value / (60 * 24):.1f} d"


def _fmt_pct(value: float | None, *, signed: bool = True) -> str:
    if value is None:
        return _UNAVAILABLE
    sign = "+" if (signed and value > 0) else ""
    return f"{sign}{value:.1f}%"


def render_markdown(report: EvaluationReport) -> str:
    """Render an :class:`EvaluationReport` as a human-readable Markdown scorecard."""
    cfg = report.config
    lines: list[str] = []
    lines.append("# OneHealth Pipeline -- Figure-3 Timeliness Scorecard")
    lines.append("")
    lines.append(
        f"**Window:** {cfg.start_date.isoformat()} → {cfg.end_date.isoformat()}  "
    )
    lines.append(
        f"**Verticals:** {', '.join(v.value for v in cfg.verticals) or 'none'}  "
    )
    lines.append(
        f"**Agencies:** {', '.join(cfg.agencies) if cfg.agencies else 'all in audit log'}  "
    )
    lines.append(f"**Historical baseline year:** {cfg.historical_baseline_year}  ")
    lines.append(f"**Baseline source:** `{report.baseline_source}`  ")
    lines.append(f"**Generated at:** {report.generated_at.isoformat()}  ")
    lines.append(f"**Total observations in window:** {report.total_observations}")
    lines.append("")

    # Phase-3 success-criterion verdicts ------------------------------------
    lines.append("## Phase-3 success criterion (Detect → Notify ≥ 30% shorter vs 2024)")
    lines.append("")
    if not report.phase3_verdicts:
        lines.append("_No Detect→Notify cells evaluated; no verdicts to render._")
    else:
        lines.append(
            "| Agency | Vertical | Median (pipeline) | Baseline (2024) | % shorter | Verdict |"
        )
        lines.append("|---|---|---:|---:|---:|:---:|")
        for v in report.phase3_verdicts:
            verdict_mark = "PASS" if v.passes else "FAIL"
            lines.append(
                "| {agency} | {vertical} | {med} | {base} | {pct} | {verdict} |".format(
                    agency=v.agency,
                    vertical=v.vertical.value,
                    med=_fmt_minutes(v.median_min),
                    base=_fmt_minutes(v.baseline_min),
                    pct=_fmt_pct(v.pct_shorter, signed=False)
                    if v.pct_shorter is not None
                    else _UNAVAILABLE,
                    verdict=verdict_mark,
                )
            )
    lines.append("")

    # Per (agency, vertical) detailed scorecards ----------------------------
    lines.append("## Per-agency, per-vertical interval scorecards")
    lines.append("")
    if not report.scorecards:
        lines.append("_No scorecards to render._")
    for sc in report.scorecards:
        lines.append(f"### {sc.agency} -- {sc.vertical.value}")
        lines.append(f"_n_ = {sc.n_observations} observations")
        lines.append("")
        lines.append("| Pair | n | Median | IQR (p25-p75) | Baseline | Δ vs baseline | % shorter |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for it in sc.intervals:
            iqr_text = (
                f"{_fmt_minutes(it.p25_min)} - {_fmt_minutes(it.p75_min)}"
                if it.iqr_min is not None
                else _UNAVAILABLE
            )
            lines.append(
                "| {pair} | {n} | {median} | {iqr} | {base} | {delta} | {short} |".format(
                    pair=it.pair,
                    n=it.n,
                    median=_fmt_minutes(it.median_min),
                    iqr=iqr_text,
                    base=_fmt_minutes(it.baseline_min),
                    delta=_fmt_pct(it.pct_change_vs_baseline),
                    short=_fmt_pct(it.pct_shorter_vs_baseline, signed=False),
                )
            )
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "_Detect / Notify / Verify / Lab / Respond mapping follows "
        "`schema/deep/audit.sql`. Verify and Lab columns are PROVISIONAL "
        "until human-review and lab-confirmation milestones are joined in._"
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def _connect_duckdb(ducklake_uri: str | None) -> Any | None:
    if not ducklake_uri:
        return None
    try:
        import duckdb  # type: ignore[import-not-found]
    except ImportError:
        return None
    return duckdb.connect(ducklake_uri)


def _build_parser() -> "argparse.ArgumentParser":
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m onehealth_agents.evaluation",
        description=(
            "Score the OneHealth pipeline against the Figure-3 timeliness "
            "milestones and the 2024 Arizona historical baseline."
        ),
    )
    parser.add_argument("--start", required=True, help="Window start (YYYY-MM-DD).")
    parser.add_argument("--end", required=True, help="Window end (YYYY-MM-DD).")
    parser.add_argument(
        "--vertical",
        action="append",
        choices=[v.value for v in Vertical],
        help="Restrict to one or more verticals (repeatable). Default: vbd + heat.",
    )
    parser.add_argument(
        "--agency",
        action="append",
        default=[],
        help="Restrict to one or more agency slugs (repeatable). Default: all.",
    )
    parser.add_argument(
        "--baseline-year",
        type=int,
        default=2024,
        help="Year of the historical baseline JSON to load. Default: 2024.",
    )
    parser.add_argument(
        "--baseline-path",
        default=None,
        help="Override path to baseline-<year>.json (default: <repo>/evaluation/baseline-<year>.json).",
    )
    parser.add_argument(
        "--ducklake-uri",
        default=os.environ.get("KG_DUCKLAKE_URI"),
        help="Override DuckLake URI (default: $KG_DUCKLAKE_URI; falls back to no connection).",
    )
    parser.add_argument(
        "--format",
        choices=["md", "json"],
        default="md",
        help="Output format: 'md' (default) or 'json'.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: ``python -m onehealth_agents.evaluation ...``."""
    import sys

    ns = _build_parser().parse_args(argv)

    verticals = (
        [Vertical(v) for v in ns.vertical]
        if ns.vertical
        else [Vertical.VBD, Vertical.HEAT]
    )
    config = EvaluationConfig(
        start_date=date.fromisoformat(ns.start),
        end_date=date.fromisoformat(ns.end),
        verticals=verticals,
        agencies=list(ns.agency),
        historical_baseline_year=ns.baseline_year,
    )

    connection = _connect_duckdb(ns.ducklake_uri)
    evaluator = MilestoneEvaluator(
        connection=connection,
        baseline_path=ns.baseline_path,
    )
    report = evaluator.evaluate(config)

    if ns.format == "json":
        sys.stdout.write(report.model_dump_json(indent=2))
    else:
        sys.stdout.write(render_markdown(report))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":  # pragma: no cover - module CLI
    raise SystemExit(main())


__all__ = [
    "AGENT_TO_MILESTONE",
    "AgencyVerticalScorecard",
    "Baseline",
    "EvaluationConfig",
    "EvaluationReport",
    "IntervalStat",
    "MILESTONE_PAIRS",
    "MilestoneEvaluator",
    "PHASE3_DETECT_TO_NOTIFY_TARGET_PCT_SHORTER",
    "Phase3Verdict",
    "TimelinessRow",
    "main",
    "render_markdown",
]
