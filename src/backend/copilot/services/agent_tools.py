"""The agent's tools, bound to one analysis time: alerts, impact, sensor evidence, supplier record, plant history, proposals.

Every tool is point-in-time: plant history is cut at the analysis time and later work order closures are hidden.
Tools return JSON-ready dicts; a request the data cannot answer returns an error message the agent can act on.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta

from copilot.core.agent_views import (
    TIME_FORMAT,
    alert_row,
    build_proposal,
    impact_result,
)
from copilot.core.alert_feedback import view_dict
from copilot.core.errors import CopilotError
from copilot.data_pipeline.proposal_store import ProposalStore
from copilot.services.feedback_service import FeedbackService
from copilot.services.field_service import FieldInputService
from copilot.services.impact_service import ImpactService
from copilot.services.supplier_reliability import SupplierReliabilityService
from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.services.investigation_tools import ToolBox

EVIDENCE_DAYS = 7
PENDING = "pending"
ERROR_KEY = "error"
PLANT_ERRORS = (CopilotError, KeyError, ValueError, IndexError)


class CopilotTools:
    """Tool implementations for one run at a fixed analysis time."""

    def __init__(self, as_of: datetime, impact: ImpactService, plant_tools: ToolBox, plant_catalog: PlantCatalog,
                 reliability: SupplierReliabilityService, proposals: ProposalStore,
                 field: FieldInputService | None = None, feedback: FeedbackService | None = None) -> None:
        self.as_of = as_of
        self.field = field
        self.feedback = feedback
        self.impact = impact
        self.plant_tools = plant_tools
        self.plant_catalog = plant_catalog
        self.reliability = reliability
        self.proposals = proposals

    def list_open_alerts(self) -> dict[str, object]:
        alerts = self.impact.open_alerts(self.as_of)
        return {"as_of": self.as_of.strftime(TIME_FORMAT), "count": len(alerts),
                "alerts": [alert_row(a, self.impact.asset_lines.get(a.asset_id, "")) for a in alerts]}

    def analyse_alert_impact(self, alert_id: str) -> dict[str, object]:
        return impact_result(self.impact.analyse(alert_id, self.as_of))

    def get_sensor_evidence(self, alert_id: str) -> dict[str, object]:
        alert = self.impact.alerts.get(alert_id)
        mode = next(cls.failure_modes[alert.failure_mode] for cls in self.plant_catalog.plant.asset_classes.values()
                    if alert.failure_mode in cls.failure_modes)
        start = self.as_of - timedelta(days=EVIDENCE_DAYS)
        trends = [self.plant_tools.sensor_trend(alert.asset_id, sensor, start, self.as_of) for sensor in mode.symptoms]
        return {"alert_id": alert_id, "asset_id": alert.asset_id, "failure_mode": mode.label,
                "pf_interval_days": mode.pf_interval_days, "recommended_action": mode.recommended_action,
                "sensors": trends}

    def get_field_reports(self, alert_id: str) -> dict[str, object]:
        operator = view_dict(self.feedback.view(alert_id, self.as_of)) if self.feedback else None
        if self.field is None:
            return {"inspections": [], "supplier_updates": [], "operator_feedback": operator}
        updates = self.field.updates_known(self.as_of)
        return {"alert_id": alert_id, "inspections": self.field.findings_for(alert_id, self.as_of),
                "operator_feedback": operator,
                "supplier_updates": [{"order_reference": u.order_reference, "supplier": u.supplier_name, "change": u.change,
                                      "new_delivery": u.new_delivery_at.strftime(TIME_FORMAT) if u.new_delivery_at else None,
                                      "reason": u.reason, "received": u.received_at.strftime(TIME_FORMAT)} for u in updates]}

    def get_supplier_record(self, supplier_id: str) -> dict[str, object]:
        s = self.reliability.assess(supplier_id, self.as_of)
        return {"supplier_id": s.supplier_id, "name": s.supplier_name, "governed_metric": "supplier_otd",
                "on_time_percent": None if s.on_time_share is None else round(s.on_time_share * 100, 1),
                "expected_days_late": s.expected_days_late, "window": f"{s.window_start} to {s.window_end}",
                "window_days": (s.window_end - s.window_start).days + 1,
                "sql_fingerprint": s.sql_fingerprint}

    def oee_summary(self, scope_type: str, scope_id: str, start: str, end: str) -> dict[str, object]:
        first, last = self._period(start, end)
        return {"scope": f"{scope_type} {scope_id}", "start": str(first), "end": str(last),
                **self.plant_tools.oee_summary(scope_type, scope_id, first, last)}

    def failures(self, scope_type: str, scope_id: str, start: str, end: str) -> dict[str, object]:
        first, _ = self._period(start, end)
        return self.plant_tools.failures(scope_type, scope_id, first, self.as_of)

    def work_order_history(self, asset_id: str, start: str) -> dict[str, object]:
        first, _ = self._period(start, self.as_of.date().isoformat())
        rows = self.plant_tools.work_order_history(asset_id, first, self.as_of)
        for row in rows:
            if row.get("closed_at") not in (None, "NaT") and str(row["closed_at"]) > self.as_of.strftime(TIME_FORMAT):
                row["closed_at"] = None
        return {"asset_id": asset_id, "work_orders": rows}

    def propose_action_plan(self, alert_id: str, option_kind: str, option_source: str, work_order_note: str,
                            customer_note: str) -> dict[str, object]:
        report = self.impact.analyse(alert_id, self.as_of)
        proposal = build_proposal(report, option_kind, option_source, work_order_note, customer_note,
                                  self.proposals.next_id(alert_id), self.as_of, PENDING)
        record = self.proposals.add(proposal)
        return {**record, "note": "Pending approval by a person. Nothing has been ordered, moved, or scheduled."}

    def _period(self, start: str, end: str) -> tuple[date, date]:
        """Parse ISO dates and cut the end at the analysis time."""
        return date.fromisoformat(start), min(date.fromisoformat(end), self.as_of.date())

    def safe(self, method: Callable[..., dict[str, object]]) -> Callable[..., dict[str, object]]:
        """Wrap a tool so data errors come back as a message for the agent instead of an exception."""
        def call(*args: object, **kwargs: object) -> dict[str, object]:
            try:
                return method(*args, **kwargs)
            except PLANT_ERRORS as error:
                return {ERROR_KEY: str(error)}
        return call
