"""The alerts the copilot can analyse, read from the plant package's alert replay.

Alert facts keep only what was known when the alert was raised. Outcomes (the failure an alert warned about) are
kept apart and are only ever used once they lie before the analysis time, by the lead history.
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from copilot.core.errors import ImpactError
from copilot.core.impact_model import AlertFacts
from copilot.core.lead_history import AlertOutcome

NEW_DRAFT = "new_draft"
USEFUL = "useful"
# Alerts followed by their failure: in time ("useful") or with less warning than the scoring window ("late").
REAL_FAILURE_TRUTHS = frozenset({"useful", "late"})


def _timestamp(value: object) -> datetime:
    return pd.Timestamp(str(value)).to_pydatetime()


def _failure_time(raw: dict[str, object]) -> datetime | None:
    return _timestamp(raw["failure_at"]) if raw.get("truth") in REAL_FAILURE_TRUTHS else None


def to_alert_facts(raw: dict[str, object]) -> AlertFacts:
    """Keep the fields known at raise time."""
    return AlertFacts(
        alert_id=str(raw["alert_id"]), asset_id=str(raw["asset_id"]), failure_mode=str(raw["failure_mode"]),
        component=str(raw["component"]), raised_at=_timestamp(raw["raised_at"]), deadline_at=_timestamp(raw["deadline_at"]),
        repair_hours=float(raw["repair_hours"]), planned_slot=bool(raw["planned_slot"]), priority=str(raw["priority"]),
    )


class AlertBook:
    """Alerts by id, and the ones that opened their own draft work order."""

    def __init__(self, raw_alerts: list[dict[str, object]]) -> None:
        self.alerts = {str(a["alert_id"]): to_alert_facts(a) for a in raw_alerts}
        self.drafting = [self.alerts[str(a["alert_id"])] for a in raw_alerts if a.get("outcome") == NEW_DRAFT]
        # Evaluation only: the failure each alert was followed by (None for false alerts). Recommendations never read it.
        self.failure_times = {str(a["alert_id"]): _failure_time(a) for a in raw_alerts}
        self.outcomes = [AlertOutcome(str(a["failure_mode"]), _timestamp(a["raised_at"]), _timestamp(a["failure_at"]))
                         for a in raw_alerts if a.get("truth") == USEFUL]

    def get(self, alert_id: str) -> AlertFacts:
        if alert_id not in self.alerts:
            raise ImpactError(f"Unknown alert {alert_id}; list_open_alerts gives the open alert ids")
        return self.alerts[alert_id]

    def raised_between(self, start: datetime, end: datetime) -> list[AlertFacts]:
        """Alerts raised in the window, oldest first."""
        return sorted((a for a in self.alerts.values() if start <= a.raised_at <= end), key=lambda a: (a.raised_at, a.alert_id))
