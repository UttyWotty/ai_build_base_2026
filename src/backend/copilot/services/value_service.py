"""Runs the value backtest: every alert that opened a draft is analysed as it was raised, then scored at its outcome.

The impact analysis is the same one the agent and the app use, at each alert's own raise time, so the track record
measures the product as it would have run. The result is computed once per service and kept.
"""
from __future__ import annotations

from copilot.core.value_backtest import CaseValue, ValueSummary, case_value, summarise
from copilot.services.impact_service import ImpactService


class ValueService:
    """The copilot's track record over the alert replay."""

    def __init__(self, impact: ImpactService) -> None:
        self.impact = impact
        self._result: tuple[list[CaseValue], ValueSummary] | None = None

    def track_record(self) -> tuple[list[CaseValue], ValueSummary]:
        if self._result is None:
            alerts = self.impact.alerts
            cases = [case_value(self.impact.analyse(a.alert_id), alerts.failure_times.get(a.alert_id))
                     for a in sorted(alerts.drafting, key=lambda a: (a.raised_at, a.alert_id))]
            self._result = (cases, summarise(cases))
        return self._result
