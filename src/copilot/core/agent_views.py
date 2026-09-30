"""Shapes analysis results into compact, JSON-ready tool results for the agent, and builds action proposals.

Tool results carry every number the agent may quote, rounded the way it should quote them, so answers can be verified.
A proposal takes its numbers from the impact report, never from the model; the model only chooses and writes notes.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from copilot.core.errors import CopilotError
from copilot.core.impact_model import (
    AlertFacts,
    ImpactReport,
    RecoveryOption,
    SparePosition,
)

TIME_FORMAT = "%Y-%m-%d %H:%M"
MAX_ORDERS_IN_RESULT = 10
PERCENT = 100


class ProposalError(CopilotError):
    """The proposed option does not exist for this alert."""


@dataclass(frozen=True)
class ActionProposal:
    """A plan waiting for a person to approve: the work order, the parts action, and the customer notice."""

    proposal_id: str
    alert_id: str
    asset_id: str
    created_at: datetime
    option_kind: str
    option_source: str
    ready_at: datetime
    extra_cost_usd: float
    downtime_hours: float
    lost_contribution_usd: float
    orders_at_risk: tuple[str, ...]
    work_order_note: str
    customer_note: str
    status: str


def alert_row(alert: AlertFacts, line_id: str) -> dict[str, object]:
    return {"alert_id": alert.alert_id, "asset_id": alert.asset_id, "line_id": line_id,
            "failure_mode": alert.failure_mode, "raised_at": alert.raised_at.strftime(TIME_FORMAT),
            "repair_deadline": alert.deadline_at.strftime(TIME_FORMAT), "priority": alert.priority}


def impact_result(report: ImpactReport) -> dict[str, object]:
    """The impact report as the agent sees it."""
    result: dict[str, object] = {
        "alert": alert_row(report.alert, report.asset.line_id),
        "as_of": report.as_of.strftime(TIME_FORMAT),
        "repair_hours": report.alert.repair_hours,
        "planned_slot_available": report.alert.planned_slot,
        "line": {"line_id": report.asset.line_id, "units_per_hour": round(report.economics.units_per_hour, 1),
                 "contribution_usd_per_unit": report.economics.contribution_usd_per_unit},
        "options": [_option(o, o == report.recommended) for o in report.options],
        "assumptions": list(report.assumptions),
    }
    if report.spare is not None and report.local is not None:
        result["spare"] = {"spare_part_id": report.spare.spare_part_id, "label": report.spare.label,
                           "unit_cost_usd": report.spare.unit_cost_usd,
                           "local": _position(report.local), "sister_sites": [_position(s) for s in report.sisters]}
    if report.supplier is not None:
        s = report.supplier
        result["supplier"] = {"supplier_id": s.supplier_id, "name": s.supplier_name,
                              "on_time_percent": None if s.on_time_share is None else round(s.on_time_share * PERCENT, 1),
                              "expected_days_late": s.expected_days_late, "window": f"{s.window_start} to {s.window_end}",
                              "governed_metric": "supplier_otd", "sql_fingerprint": s.sql_fingerprint}
    if report.lead.count:
        result["past_alerts_of_this_mode"] = {"count": report.lead.count, "fastest_failure_hours": report.lead.fastest_hours,
                                              "median_failure_hours": report.lead.median_hours}
    return result


def _position(position: SparePosition) -> dict[str, object]:
    return {"site_id": position.site_id, "on_hand": position.on_hand,
            "open_orders": [{"po_id": o.po_id, "quantity": o.quantity, "promised": o.promised_at.strftime(TIME_FORMAT),
                             "expected": o.expected_at.strftime(TIME_FORMAT)} for o in position.open_orders],
            "alerts_queued_for_this_spare": [c.alert_id for c in position.claims]}


def _option(option: RecoveryOption, recommended: bool) -> dict[str, object]:
    orders = option.orders_at_risk
    return {"kind": option.kind.value, "source": option.source, "ready_at": option.ready_at.strftime(TIME_FORMAT),
            "planned_repair": option.planned, "extra_cost_usd": option.extra_cost_usd,
            "downtime_hours": option.downtime_hours, "lost_contribution_usd": option.lost_contribution_usd,
            "total_cost_usd": round(option.total_cost_usd, 2), "worst_case_downtime_hours": option.worst_case_downtime_hours,
            "customer_lines_at_risk": len(orders), "customer_value_at_risk_usd": round(sum(o.value_usd for o in orders), 2),
            "orders_at_risk": [{"so_line_id": o.so_line_id, "customer": o.customer_name, "part_id": o.part_id,
                                "quantity": o.quantity, "committed": str(o.committed_date)} for o in orders[:MAX_ORDERS_IN_RESULT]],
            "recommended_by_rules": recommended}


def build_proposal(report: ImpactReport, option_kind: str, option_source: str, work_order_note: str,
                   customer_note: str, proposal_id: str, created_at: datetime, status: str) -> ActionProposal:
    """A proposal for one of the report's options; the numbers are the report's."""
    option = next((o for o in report.options if o.kind.value == option_kind and o.source == option_source), None)
    if option is None:
        known = ", ".join(f"{o.kind.value}/{o.source}" for o in report.options)
        raise ProposalError(f"No option {option_kind}/{option_source} for {report.alert.alert_id}; options are: {known}")
    return ActionProposal(proposal_id, report.alert.alert_id, report.asset.asset_id, created_at, option.kind.value,
                          option.source, option.ready_at, option.extra_cost_usd, option.downtime_hours,
                          option.lost_contribution_usd, tuple(o.so_line_id for o in option.orders_at_risk),
                          work_order_note.strip(), customer_note.strip(), status)
