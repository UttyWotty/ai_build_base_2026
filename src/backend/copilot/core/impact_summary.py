"""Summaries over impact results that every interface shares: the named demo scenarios, the recommended and
baseline options, what the recommendation avoids, spare conflicts, and the headline numbers for a moment in time.

Inputs are the JSON-ready impact results the agent also sees, so the API, the web apps, and the agent agree.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

# The option a site takes without the copilot: its own stock or open order, else a normal new order.
BASELINE_KINDS = ("own_stock", "open_order", "new_order", "no_spare_needed")


@dataclass(frozen=True)
class Scenario:
    """A named moment of the data worth replaying."""

    scenario_id: str
    label: str
    as_of: datetime
    story: str


SCENARIOS = (
    Scenario("bearing-squeeze", "Bearing squeeze at US1", datetime(2026, 7, 25, 2, 0),
             "Two spindle-bearing alerts at US1, one set on the shelf, and the replacement is with a supplier that is "
             "late one time in three."),
    Scenario("pump-wear", "Hydraulic pump wear at DE1", datetime(2026, 8, 19, 1, 0),
             "A hydraulic pump wearing out six days ahead, with the spare in stock: a calm, planned repair."),
)


def recommended(impact: dict) -> dict:
    """The option the rules recommend."""
    return next(o for o in impact["options"] if o["recommended_by_rules"])


def baseline(impact: dict) -> dict:
    """What the site would do on its own: the first of its own-supply options, else a new order."""
    by_kind = {o["kind"]: o for o in impact["options"]}
    return next(by_kind[k] for k in BASELINE_KINDS if k in by_kind)


def avoided(impact: dict) -> tuple[float, float]:
    """Downtime hours and cost the recommendation avoids compared with the baseline."""
    base, best = baseline(impact), recommended(impact)
    return (round(max(base["downtime_hours"] - best["downtime_hours"], 0.0), 1),
            round(max(base["total_cost_usd"] - best["total_cost_usd"], 0.0), 2))


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


def headline(impacts: list[dict]) -> dict[str, object]:
    """The numbers across every open alert at one moment."""
    savings = [avoided(i) for i in impacts]
    return {"open_alerts": len(impacts), "alerts_in_spare_conflict": sum(1 for i in impacts if conflict_note(i)),
            "downtime_avoided_hours": round(sum(h for h, _ in savings), 1),
            "cost_avoided_usd": round(sum(c for _, c in savings), 2)}
