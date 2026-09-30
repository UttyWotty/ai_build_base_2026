"""Tests for the web app's pure presenters: formatting, option rows, the baseline, avoided cost, and conflicts.

They run on a hand-built impact result shaped like the agent's tool result.
No Streamlit is involved.
"""
from __future__ import annotations

from copilot.ui import presenters as p


def option(kind: str, source: str, down: float, total: float, recommended: bool, lines: int = 0) -> dict:
    return {"kind": kind, "source": source, "ready_at": "2026-07-27 02:00", "extra_cost_usd": 0.0, "downtime_hours": down,
            "worst_case_downtime_hours": None, "lost_contribution_usd": total, "customer_lines_at_risk": lines,
            "total_cost_usd": total, "recommended_by_rules": recommended, "orders_at_risk": []}


IMPACT = {
    "options": [option("transfer", "DE1", 10.0, 650.0, True), option("open_order", "PO-1", 190.3, 93825.0, False, 4)],
    "spare": {"spare_part_id": "SP-1", "label": "Bearing set",
              "local": {"site_id": "US1", "on_hand": 1, "alerts_queued_for_this_spare": ["AL-1", "AL-2"]}},
}


def test_formatting_handles_missing_values() -> None:
    assert (p.money(1234.5), p.hours(10), p.percent(66.14)) == ("$1,234", "10.0 h", "66.1%")
    assert p.money(None) == p.hours(None) == p.percent(None) == "-"


def test_rows_mark_the_recommendation_and_the_baseline_is_the_sites_own_supply() -> None:
    rows = p.option_rows(IMPACT)
    assert rows[0][""] == "recommended" and rows[0]["Option"] == "Air transfer" and rows[1][""] == ""
    assert p.baseline(IMPACT)["kind"] == "open_order"
    assert p.avoided(IMPACT) == (180.3, 93175.0)


def test_conflict_note_only_when_the_queue_exceeds_the_shelf() -> None:
    assert "2 alerts need Bearing set (SP-1) at US1" in p.conflict_note(IMPACT)
    calm = {**IMPACT, "spare": {**IMPACT["spare"], "local": {**IMPACT["spare"]["local"], "on_hand": 2}}}
    assert p.conflict_note(calm) is None and p.conflict_note({"options": []}) is None


def test_sensor_rows_are_long_format_with_the_normal_range() -> None:
    evidence = {"sensors": [{"label": "Vibration", "unit": "mm_per_s", "normal_range": [0.4, 2.8],
                             "values": [{"period": "2026-07-24", "mean": 3.46}]}]}
    assert p.sensor_rows(evidence) == [{"sensor": "Vibration", "unit": "mm_per_s", "day": "2026-07-24", "mean": 3.46,
                                        "normal_low": 0.4, "normal_high": 2.8}]
