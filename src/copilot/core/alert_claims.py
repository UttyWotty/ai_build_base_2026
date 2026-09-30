"""Works out which alerts were still waiting for a repair at a given time, and so still claim a spare.

An alert claims a spare from when it is raised until its component is repaired or its P-F interval has passed.
Only alerts that opened their own draft work order count; alerts attached to an existing order are duplicates.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from copilot.core.impact_model import AlertFacts, Claim


@dataclass(frozen=True)
class Repair:
    """A repair of one component on one asset, known from the failure history."""

    asset_id: str
    component: str
    at: datetime


def open_claims(alerts: list[AlertFacts], repairs: list[Repair], pf_days: dict[str, float],
                as_of: datetime) -> tuple[Claim, ...]:
    """Alerts raised by as_of whose repair had not happened and whose P-F window had not closed."""
    claims = []
    for alert in alerts:
        window = pf_days.get(alert.failure_mode)
        if alert.raised_at > as_of or window is None or as_of >= alert.raised_at + timedelta(days=window):
            continue
        repaired = any(r.asset_id == alert.asset_id and r.component == alert.component
                       and alert.raised_at <= r.at <= as_of for r in repairs)
        if not repaired:
            claims.append(Claim(alert.alert_id, alert.asset_id, alert.deadline_at))
    return tuple(sorted(claims, key=lambda c: (c.deadline_at, c.alert_id)))
