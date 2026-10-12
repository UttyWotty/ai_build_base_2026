"""Tests for the impact summary the API and the agent share: the baseline, the avoided cost, and the conflict note.

They run on a hand-built impact result shaped like the agent's tool result.
The API tests reuse the same result as their fake impact analysis.
"""
from __future__ import annotations

from copilot.core.impact_summary import avoided, baseline, conflict_note, recommended


def option(kind: str, source: str, down: float, total: float, recommended: bool, lines: int = 0) -> dict:
    return {"kind": kind, "source": source, "ready_at": "2026-07-27 02:00", "extra_cost_usd": 0.0, "downtime_hours": down,
            "worst_case_downtime_hours": None, "lost_contribution_usd": total, "customer_lines_at_risk": lines,
            "total_cost_usd": total, "recommended_by_rules": recommended, "orders_at_risk": []}


IMPACT = {
    "options": [option("transfer", "DE1", 10.0, 650.0, True), option("open_order", "PO-1", 190.3, 93825.0, False, 4)],
    "spare": {"spare_part_id": "SP-1", "label": "Bearing set",
              "local": {"site_id": "US1", "on_hand": 1, "alerts_queued_for_this_spare": ["AL-1", "AL-2"]}},
}


def test_the_recommendation_and_the_baseline_is_the_sites_own_supply() -> None:
    assert recommended(IMPACT)["kind"] == "transfer"
    assert baseline(IMPACT)["kind"] == "open_order"
    assert avoided(IMPACT) == (180.3, 93175.0)


def test_conflict_note_only_when_the_queue_exceeds_the_shelf() -> None:
    assert "2 alerts need Bearing set (SP-1) at US1" in str(conflict_note(IMPACT))
    calm = {**IMPACT, "spare": {**IMPACT["spare"], "local": {**IMPACT["spare"]["local"], "on_hand": 2}}}
    assert conflict_note(calm) is None and conflict_note({"options": []}) is None
