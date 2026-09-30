"""The plant event feed for a time window: alerts from the replay, and breakdowns and spare movements from the data.

It is what live mode shows as the clock runs, so a viewer sees the plant happening rather than a static page.
Everything is read up to the window's end only.
"""
from __future__ import annotations

from datetime import datetime

from copilot.core.decision_events import decision_events
from copilot.core.plant_events import AlertRow, PlantEvent, build_feed
from copilot.data_pipeline import event_queries as q
from copilot.services.decisions import OutcomeService
from copilot.services.impact_service import ImpactService


class EventFeed:
    """Events between two moments, including the closed loop of approved decisions when an outcome service is given."""

    def __init__(self, impact: ImpactService, outcomes: OutcomeService | None = None) -> None:
        self.impact = impact
        self.outcomes = outcomes

    def between(self, start: datetime, end: datetime) -> list[PlantEvent]:
        store = self.impact.connection_manager
        sites = self.impact.asset_sites
        drafting = {a.alert_id for a in self.impact.alerts.drafting}
        alerts = [AlertRow(a.alert_id, a.asset_id, sites.get(a.asset_id, ""), a.failure_mode, a.priority, a.raised_at,
                           a.alert_id in drafting) for a in self.impact.alerts.raised_between(start, end)]
        feed = build_feed(alerts, q.failures_between(store, start, end), q.movements_between(store, start, end),
                          q.orders_between(store, start, end), start, end)
        return sorted(feed + self._loop_events(start, end), key=lambda e: (e.at, e.kind), reverse=True)

    def _loop_events(self, start: datetime, end: datetime) -> list[PlantEvent]:
        if self.outcomes is None:
            return []
        settled = {o.proposal_id: o for o in self.outcomes.outcomes(end)}
        events = [e for d in self.outcomes.book.decisions() for e in decision_events(d, settled.get(d.proposal_id))]
        return [e for e in events if start <= e.at <= end]
