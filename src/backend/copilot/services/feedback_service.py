"""Keeps operator feedback on alerts and shows each alert what operators said about it and its earlier siblings.

Verdicts are stored as JSON rows next to the other field inputs and read back point-in-time.
The track record and the impact analysis never read them, so feedback informs people and agents without moving any number.
"""
from __future__ import annotations

from datetime import datetime

from copilot.core.alert_feedback import (
    AlertFeedback,
    FeedbackView,
    feedback_from_row,
    feedback_row,
    feedback_view,
    new_false_alert,
)
from copilot.data_pipeline.record_store import RecordStore
from copilot.services.alert_book import AlertBook


class FeedbackService:
    """False-alert verdicts by operators."""

    def __init__(self, alerts: AlertBook, store: RecordStore) -> None:
        self.alerts = alerts
        self.store = store

    def mark_false(self, alert_id: str, reason: str, marked_at: datetime) -> AlertFeedback:
        alert = self.alerts.get(alert_id)
        feedback = new_false_alert(alert.alert_id, alert.asset_id, alert.failure_mode, alert.raised_at, reason,
                                   marked_at)
        self.store.add(feedback_row(feedback))
        return feedback

    def view(self, alert_id: str, now: datetime) -> FeedbackView:
        alert = self.alerts.get(alert_id)
        records = [feedback_from_row(r) for r in self.store.all()]
        return feedback_view(records, alert.alert_id, alert.asset_id, alert.failure_mode, now)

    def clear(self) -> int:
        return self.store.clear()
