"""Scores the copilot's recommendations against what really happened, alert by alert, over the test period.

For each alert the recommended option and the baseline (what the site would do alone) are priced at the actual failure
time: a spare in hand before the failure means a planned repair, a later one means waiting. A false alert costs only the
plan's extra spend. Outcomes are used here for evaluation only; the recommendations themselves never saw them.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from copilot.core.impact_model import ImpactReport, RecoveryOption
from copilot.core.impact_summary import BASELINE_KINDS

SECONDS_PER_HOUR = 3600.0
TOP_CASES = 5


@dataclass(frozen=True)
class RealisedCost:
    """What an option would have cost given the real outcome."""

    extra_cost_usd: float
    lost_hours: float
    lost_contribution_usd: float

    @property
    def total_usd(self) -> float:
        return self.extra_cost_usd + self.lost_contribution_usd


@dataclass(frozen=True)
class CaseValue:
    """One alert: the copilot's plan against the site acting alone, at the real outcome."""

    alert_id: str
    asset_id: str
    site_id: str
    raised_at: datetime
    failed_at: datetime | None
    recommended_kind: str
    baseline_kind: str
    baseline: RealisedCost
    copilot: RealisedCost

    @property
    def hours_saved(self) -> float:
        return round(self.baseline.lost_hours - self.copilot.lost_hours, 1)

    @property
    def usd_saved(self) -> float:
        return round(self.baseline.total_usd - self.copilot.total_usd, 2)


@dataclass(frozen=True)
class ValueSummary:
    """The track record over all scored alerts."""

    alerts: int
    real_failures: int
    false_alerts: int
    plans_that_differ: int
    hours_saved: float
    usd_saved_on_failures: float
    usd_spent_on_false_alerts: float
    net_usd: float
    by_site: dict[str, float]
    top_cases: tuple[CaseValue, ...]


def realised_cost(option: RecoveryOption, report: ImpactReport, failed_at: datetime | None) -> RealisedCost:
    """Price an option at the real outcome; without a failure only the extra spend counts."""
    if failed_at is None:
        return RealisedCost(option.extra_cost_usd, 0.0, 0.0)
    repair = report.alert.repair_hours
    if option.ready_at <= failed_at:
        lost = 0.0 if report.alert.planned_slot else repair
    else:
        lost = (option.ready_at - failed_at).total_seconds() / SECONDS_PER_HOUR + repair
    contribution = lost * report.economics.units_per_hour * report.economics.contribution_usd_per_unit
    return RealisedCost(option.extra_cost_usd, round(lost, 1), round(contribution, 2))


def baseline_option(report: ImpactReport) -> RecoveryOption:
    """The site's own choice: its first own-supply option, else a new order."""
    by_kind = {o.kind.value: o for o in report.options}
    return next(by_kind[k] for k in BASELINE_KINDS if k in by_kind)


def case_value(report: ImpactReport, failed_at: datetime | None) -> CaseValue:
    base = baseline_option(report)
    return CaseValue(report.alert.alert_id, report.asset.asset_id, report.asset.site_id, report.alert.raised_at,
                     failed_at, report.recommended.kind.value, base.kind.value,
                     realised_cost(base, report, failed_at), realised_cost(report.recommended, report, failed_at))


def summarise(cases: list[CaseValue]) -> ValueSummary:
    failures = [c for c in cases if c.failed_at is not None]
    false_alerts = [c for c in cases if c.failed_at is None]
    saved = round(sum(c.usd_saved for c in failures), 2)
    wasted = round(sum(c.copilot.extra_cost_usd - c.baseline.extra_cost_usd for c in false_alerts), 2)
    by_site: dict[str, float] = {}
    for case in cases:
        by_site[case.site_id] = round(by_site.get(case.site_id, 0.0) + case.usd_saved, 2)
    top = tuple(sorted(cases, key=lambda c: -c.usd_saved)[:TOP_CASES])
    return ValueSummary(len(cases), len(failures), len(false_alerts),
                        sum(1 for c in cases if c.recommended_kind != c.baseline_kind),
                        round(sum(c.hours_saved for c in failures), 1), saved, wasted, round(saved - wasted, 2),
                        dict(sorted(by_site.items())), top)
