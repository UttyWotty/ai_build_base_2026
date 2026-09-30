"""Small hand-built bridge, alert, and position values shared by the copilot tests.

The bridge mirrors the shape of semantic/bridge/bridge.yaml with two sites and one spare.
Times are fixed so every expected number in the tests can be worked out by hand.
"""
from __future__ import annotations

from datetime import datetime

from copilot.core.bridge_model import (
    BridgeCatalog,
    EmergencySource,
    LineLink,
    SiteLink,
    SparePart,
    StockPolicy,
    TransferTerms,
)
from copilot.core.impact_model import AlertFacts, Claim, LineEconomics, SparePosition

T0 = datetime(2026, 7, 25, 2, 0)
BEARING = SparePart("spindle_bearing", "SP-1", "Bearing set", 1000.0, 1, "V1", 14, EmergencySource(72.0, 3.0))


def bridge(initial_a: int = 2, reorder_point: int = 1, order_up_to: int = 2) -> BridgeCatalog:
    return BridgeCatalog(
        sites={"A": SiteLink("A", "PA", "A"), "B": SiteLink("B", "PB", "B")},
        spares={"spindle_bearing": BEARING},
        policies={("A", "SP-1"): StockPolicy("A", "SP-1", initial_a, reorder_point, order_up_to),
                  ("B", "SP-1"): StockPolicy("B", "SP-1", 1, 0, 1)},
        transfer=TransferTerms(48.0, 650.0),
        lines={"A-L1": LineLink("A-L1", ("P-1",), 50.0)},
        dispatch_buffer_days=2.0,
    )


def alert(alert_id: str = "AL-2", deadline: datetime = datetime(2026, 7, 28, 2, 0), planned_slot: bool = True,
          raised: datetime = T0) -> AlertFacts:
    return AlertFacts(alert_id, "A-L1-01", "spindle_bearing_wear", "spindle_bearing", raised, deadline, 10.0,
                      planned_slot, "P2")


def position(site: str, on_hand: int, claims: tuple[Claim, ...] = (), orders: tuple = ()) -> SparePosition:
    return SparePosition(site, on_hand, orders, claims)


ECONOMICS = LineEconomics(units_per_hour=10.0, contribution_usd_per_unit=50.0)
