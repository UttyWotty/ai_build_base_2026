"""Approved proposals as decisions that change the world from the moment they were made.

A transfer takes the spare off the sister site's shelf at once and arrives at the alert's site when promised; an
express buy or a new order arrives when promised. Other alerts stop competing for the decided alert's own supply.
Stock and open-order decisions change nothing: the data already holds that supply.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from copilot.core.impact_model import OpenOrder, SparePosition

TRANSFER = "transfer"
INCOMING_KINDS = frozenset({"transfer", "emergency_buy", "new_order"})
DECISION_ORDER_PREFIX = "DEC-"


@dataclass(frozen=True)
class Decision:
    """An approved proposal, with where its spare comes from and goes to."""

    proposal_id: str
    alert_id: str
    asset_id: str
    site_id: str
    spare_part_id: str | None
    option_kind: str
    option_source: str
    decided_at: datetime
    ready_at: datetime
    extra_cost_usd: float
    quantity: int

    @property
    def brings_supply(self) -> bool:
        return self.option_kind in INCOMING_KINDS


def apply_decisions(position: SparePosition, spare_part_id: str, decisions: list[Decision], now: datetime,
                    for_alert: str | None = None) -> SparePosition:
    """The position as it stands after every decision made by now; for_alert sees its own incoming supply."""
    mine = [d for d in decisions if d.spare_part_id == spare_part_id and d.decided_at <= now]
    on_hand = position.on_hand - sum(d.quantity for d in mine
                                     if d.option_kind == TRANSFER and d.option_source == position.site_id)
    arrived = [d for d in mine if d.brings_supply and d.site_id == position.site_id and d.ready_at <= now]
    on_hand += sum(d.quantity for d in arrived)
    incoming = tuple(OpenOrder(f"{DECISION_ORDER_PREFIX}{d.proposal_id}", d.option_source, d.quantity, d.ready_at, d.ready_at)
                     for d in mine if d.brings_supply and d.site_id == position.site_id and d.ready_at > now
                     and d.alert_id == for_alert)
    covered = {d.alert_id for d in mine if d.brings_supply and d.site_id == position.site_id and d.alert_id != for_alert}
    claims = tuple(c for c in position.claims if c.alert_id not in covered)
    reserved = sum(d.quantity for d in arrived if d.alert_id != for_alert)
    return replace(position, on_hand=max(on_hand - reserved, 0), open_orders=position.open_orders + incoming,
                   claims=claims)
