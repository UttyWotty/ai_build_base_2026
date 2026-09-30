"""Turns approved proposals into decisions, and settles each decision's outcome at the demo clock.

The decision book is what the impact analysis consults so that approvals change stock and queues from their moment on.
The outcome service re-reads the analysis made when each decision was taken and prices it at the real outcome.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import pandas as pd

from copilot.core.bridge_model import BridgeCatalog
from copilot.core.decisions import Decision
from copilot.core.outcomes import DecisionOutcome, decision_outcome
from copilot.data_pipeline.proposal_store import ProposalStore
from copilot.services.alert_book import AlertBook

APPROVED = "approved"


def _ts(value: object) -> datetime:
    return pd.Timestamp(str(value)).to_pydatetime()


class DecisionBook:
    """Approved proposals as decisions."""

    def __init__(self, store: ProposalStore, alerts: AlertBook, bridge: BridgeCatalog, asset_sites: dict[str, str]) -> None:
        self.store = store
        self.alerts = alerts
        self.bridge = bridge
        self.asset_sites = asset_sites

    def decisions(self) -> list[Decision]:
        found = []
        for record in self.store.all():
            if record.get("status") != APPROVED or record["alert_id"] not in self.alerts.alerts:
                continue
            alert = self.alerts.get(str(record["alert_id"]))
            spare = self.bridge.spare_for_component(alert.component)
            found.append(Decision(
                str(record["proposal_id"]), alert.alert_id, alert.asset_id, self.asset_sites.get(alert.asset_id, ""),
                spare.spare_part_id if spare else None, str(record["option_kind"]), str(record["option_source"]),
                _ts(record["created_at"]), _ts(record["ready_at"]), float(record["extra_cost_usd"]),
                spare.quantity_per_repair if spare else 0))
        return sorted(found, key=lambda d: (d.decided_at, d.proposal_id))


class OutcomeService:
    """Outcomes of approved decisions as they stand at a given time."""

    def __init__(self, book: DecisionBook, analyse: Callable[[str, datetime], object], pf_days: dict[str, float]) -> None:
        self.book = book
        self.analyse = analyse
        self.pf_days = pf_days

    def outcomes(self, now: datetime) -> list[DecisionOutcome]:
        settled = []
        for decision in self.book.decisions():
            if decision.decided_at > now:
                continue
            alert = self.book.alerts.get(decision.alert_id)
            report = self.analyse(decision.alert_id, decision.decided_at)
            settled.append(decision_outcome(decision, report, self.book.alerts.failure_times.get(decision.alert_id),
                                            self.pf_days.get(alert.failure_mode, 0.0), now))
        return settled
