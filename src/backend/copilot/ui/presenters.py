"""Pure formatting and summarising for the web app: money, hours, option tables, conflicts, and headline numbers.

Everything here works on the JSON-ready tool results the agent also sees, so the app and the agent show the same numbers.
No Streamlit import; the views call these and render the results.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

MISSING = "-"
RECOMMENDED_MARK = "recommended"
# The option a site takes without the copilot: its own stock or open order, else a normal new order.
BASELINE_KINDS = ("own_stock", "open_order", "new_order", "no_spare_needed")
OPTION_LABELS = {"own_stock": "Own stock", "open_order": "Open order", "transfer": "Air transfer",
                 "emergency_buy": "Broker (express)", "new_order": "New order", "no_spare_needed": "No spare needed"}


@dataclass(frozen=True)
class Scenario:
    """A named moment of the data worth replaying."""

    label: str
    as_of: datetime
    story: str


SCENARIOS = (
    Scenario("Bearing squeeze at US1", datetime(2026, 7, 25, 2, 0),
             "Two spindle-bearing alerts at US1, one set on the shelf, and the replacement is with a supplier that is "
             "late one time in three."),
    Scenario("Hydraulic pump wear at DE1", datetime(2026, 8, 19, 1, 0),
             "A hydraulic pump wearing out six days ahead, with the spare in stock: a calm, planned repair."),
)


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


def recommended(impact: dict) -> dict:
    return next(o for o in impact["options"] if o["recommended_by_rules"])


def baseline(impact: dict) -> dict:
    """What the site would do on its own: the first of its own-supply options, else a new order."""
    by_kind = {o["kind"]: o for o in impact["options"]}
    return next(by_kind[k] for k in BASELINE_KINDS if k in by_kind)


def avoided(impact: dict) -> tuple[float, float]:
    """Downtime hours and cost the recommendation avoids compared with the baseline."""
    base, best = baseline(impact), recommended(impact)
    return (max(base["downtime_hours"] - best["downtime_hours"], 0.0),
            max(base["total_cost_usd"] - best["total_cost_usd"], 0.0))


def conflict_note(impact: dict) -> str | None:
    """A sentence when more alerts queue for the spare than the site has on the shelf."""
    spare = impact.get("spare")
    if not spare:
        return None
    local = spare["local"]
    queue = local["alerts_queued_for_this_spare"]
    if len(queue) <= local["on_hand"]:
        return None
    return (f"{len(queue)} alerts need {spare['label']} ({spare['spare_part_id']}) at {local['site_id']}, which has "
            f"{local['on_hand']} on hand. Served earliest deadline first: {', '.join(queue)}.")


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
