"""Feed events for the closed loop: a decision approved, its spare arriving, and its outcome once settled.

They join the plant event feed, so a live replay shows the copilot's decisions playing out next to the plant itself.
Titles carry the numbers from the outcome, which come from the same pricing as the track record.
"""
from __future__ import annotations

from copilot.core.decisions import Decision
from copilot.core.errors import CopilotError
from copilot.core.outcomes import DecisionOutcome, OutcomeStatus
from copilot.core.plant_events import PlantEvent, Severity

OPTION_WORDS = {"transfer": "air transfer", "emergency_buy": "express buy", "new_order": "new order",
                "own_stock": "own stock", "open_order": "the open order", "no_spare_needed": "a repair without spares"}


def decision_events(decision: Decision, outcome: DecisionOutcome | None) -> list[PlantEvent]:
    """The approval, the arrival of any incoming spare, and the settled outcome."""
    words = OPTION_WORDS.get(decision.option_kind, decision.option_kind)
    source = f" from {decision.option_source}" if decision.option_kind == "transfer" else ""
    events = [PlantEvent(decision.decided_at, "decision", decision.site_id, decision.asset_id,
                         f"Approved for {decision.asset_id}: {words}{source}, extra cost ${decision.extra_cost_usd:,.0f}",
                         Severity.GOOD, alert_id=decision.alert_id)]
    if decision.brings_supply:
        events.append(PlantEvent(decision.ready_at, "decision_arrival", decision.site_id, decision.asset_id,
                                 f"Spare for {decision.asset_id} arrived at {decision.site_id} ({words}{source})",
                                 Severity.GOOD, alert_id=decision.alert_id))
    if outcome is not None and outcome.settled_at is not None:
        events.append(_outcome_event(decision, outcome))
    return events


def _outcome_event(decision: Decision, outcome: DecisionOutcome) -> PlantEvent:
    if outcome.settled_at is None or outcome.with_plan is None or outcome.without_plan is None:
        raise CopilotError(f"Outcome of {decision.proposal_id} is not settled")
    if outcome.status is OutcomeStatus.FAILED:
        title = (f"{decision.asset_id} failed as predicted: down {outcome.with_plan.lost_hours:.1f} h with the plan "
                 f"instead of {outcome.without_plan.lost_hours:.1f} h, ${outcome.usd_saved:,.0f} saved")
        return PlantEvent(outcome.settled_at, "outcome", decision.site_id, decision.asset_id, title, Severity.GOOD,
                          alert_id=decision.alert_id)
    title = (f"No failure on {decision.asset_id} within its warning window; "
             f"${outcome.with_plan.extra_cost_usd:,.0f} spent as a precaution")
    return PlantEvent(outcome.settled_at, "outcome", decision.site_id, decision.asset_id, title, Severity.INFO,
                      alert_id=decision.alert_id)
