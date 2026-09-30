"""Pure formatting and summarising for the web app: money, hours, option tables, conflicts, and headline numbers.

Everything here works on the JSON-ready tool results the agent also sees, so the app and the agent show the same numbers.
No Streamlit import; the views call these and render the results.
"""
from __future__ import annotations

from copilot.core.impact_summary import (
    SCENARIOS,
    Scenario,
    avoided,
    baseline,
    conflict_note,
    recommended,
)

__all__ = ["SCENARIOS", "Scenario", "avoided", "baseline", "conflict_note", "recommended"]
MISSING = "-"
RECOMMENDED_MARK = "recommended"
OPTION_LABELS = {"own_stock": "Own stock", "open_order": "Open order", "transfer": "Air transfer",
                 "emergency_buy": "Broker (express)", "new_order": "New order", "no_spare_needed": "No spare needed"}


def money(value: float | None) -> str:
    return MISSING if value is None else f"${value:,.0f}"


def hours(value: float | None) -> str:
    return MISSING if value is None else f"{value:,.1f} h"


def percent(value: float | None) -> str:
    return MISSING if value is None else f"{value:.1f}%"


def option_label(kind: str) -> str:
    return OPTION_LABELS.get(kind, kind)


def option_rows(impact: dict) -> list[dict[str, object]]:
    """One table row per option, the recommended one marked."""
    return [{"": RECOMMENDED_MARK if o["recommended_by_rules"] else "", "Option": option_label(o["kind"]),
             "Source": o["source"], "Ready": o["ready_at"], "Extra cost": money(o["extra_cost_usd"]),
             "Downtime": hours(o["downtime_hours"]), "Worst case": hours(o["worst_case_downtime_hours"]),
             "Lost contribution": money(o["lost_contribution_usd"]), "Customer lines at risk": o["customer_lines_at_risk"],
             "Total cost": money(o["total_cost_usd"])} for o in impact["options"]]


def alert_label(alert: dict) -> str:
    return f"{alert['priority']}  {alert['asset_id']}  {alert['failure_mode'].replace('_', ' ')}  (deadline {alert['repair_deadline']})"


def sensor_rows(evidence: dict) -> list[dict[str, object]]:
    """Long-format rows for the evidence chart: one per sensor and day, with the normal range."""
    rows = []
    for sensor in evidence.get("sensors", []):
        low, high = sensor["normal_range"]
        rows += [{"sensor": sensor["label"], "unit": sensor["unit"], "day": v["period"], "mean": v["mean"],
                  "normal_low": low, "normal_high": high} for v in sensor["values"]]
    return rows
