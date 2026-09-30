"""The outcome of an approved decision, once the demo clock has passed the moment that settles it.

If the alert's failure has happened by now, the decided option and the site's own choice are both priced at the real
failure time. If the P-F window has closed with no failure, the decision's extra spend was precautionary. Until then the
outcome is pending, so the app never reveals the future.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from copilot.core.decisions import Decision
from copilot.core.impact_model import ImpactReport
from copilot.core.value_backtest import RealisedCost, baseline_option, realised_cost


class OutcomeStatus(str, Enum):
    PENDING = "pending"
    FAILED = "failed"
    NO_FAILURE = "no_failure"


@dataclass(frozen=True)
class DecisionOutcome:
    """What the decision turned out to mean."""

    proposal_id: str
    alert_id: str
    status: OutcomeStatus
    settled_at: datetime | None
    with_plan: RealisedCost | None
    without_plan: RealisedCost | None

    @property
    def hours_saved(self) -> float | None:
        return None if self.with_plan is None or self.without_plan is None else round(
            self.without_plan.lost_hours - self.with_plan.lost_hours, 1)

    @property
    def usd_saved(self) -> float | None:
        return None if self.with_plan is None or self.without_plan is None else round(
            self.without_plan.total_usd - self.with_plan.total_usd, 2)


def decision_outcome(decision: Decision, report: ImpactReport, failed_at: datetime | None, pf_days: float,
                     now: datetime) -> DecisionOutcome:
    """Settle the decision at now, using the report made when it was decided."""
    chosen = next((o for o in report.options if o.kind.value == decision.option_kind
                   and o.source == decision.option_source), report.recommended)
    base = baseline_option(report)
    if failed_at is not None and failed_at <= now:
        return DecisionOutcome(decision.proposal_id, decision.alert_id, OutcomeStatus.FAILED, failed_at,
                               realised_cost(chosen, report, failed_at), realised_cost(base, report, failed_at))
    window_end = report.alert.raised_at + timedelta(days=pf_days)
    if failed_at is None and window_end <= now:
        return DecisionOutcome(decision.proposal_id, decision.alert_id, OutcomeStatus.NO_FAILURE, window_end,
                               realised_cost(chosen, report, None), realised_cost(base, report, None))
    return DecisionOutcome(decision.proposal_id, decision.alert_id, OutcomeStatus.PENDING, None, None, None)
