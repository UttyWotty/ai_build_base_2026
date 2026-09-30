"""Assembles the impact report for one alert from its priced options, with the assumptions stated in words.

The assumptions are part of the answer: every figure the copilot shows can be traced to one of these rules.
Nothing here reads data; the impact service gathers the facts and passes them in.
"""
from __future__ import annotations

from copilot.core.impact_model import AssetContext, ImpactReport
from copilot.core.lead_history import LeadStats
from copilot.core.recovery_options import OptionInputs, build_options, recommend


def assemble_report(inputs: OptionInputs, asset: AssetContext, lead: LeadStats) -> ImpactReport:
    """Price every option, pick the recommended one, and state the rules used."""
    options = build_options(inputs)
    return ImpactReport(
        alert=inputs.alert, asset=asset, as_of=inputs.as_of, spare=inputs.spare, local=inputs.local,
        sisters=inputs.sisters, supplier=inputs.supplier, economics=inputs.economics, lead=lead, options=options,
        recommended=recommend(options), assumptions=assumptions(inputs),
    )


def assumptions(inputs: OptionInputs) -> tuple[str, ...]:
    """The rules behind the numbers, in plain words."""
    rules = [
        "The repair deadline is half the failure mode's P-F interval after the alert; a spare ready by then allows a planned repair.",
        "A spare that arrives later means the failure is assumed at the deadline (or now, if later) and the line waits for it.",
        "An asset outage stops its whole line; lost output is the line's current rate times the lost hours.",
        f"Lost contribution is {inputs.economics.contribution_usd_per_unit:g} USD per unit for this line (bridge assumption).",
        f"Customer lines are at risk when committed between the outage start and restoration plus {inputs.dispatch_buffer_days:g} days.",
        "Open alerts for the same spare at a site are served earliest deadline first.",
        "The worst case assumes the failure comes as soon as the fastest past alert of this failure mode, counting only "
        "alerts whose failure was already in the past.",
    ]
    if inputs.supplier is not None:
        rules.append("Open and new orders are expected at the promised date plus the supplier's mean lateness over the last 90 days.")
    return tuple(rules)
