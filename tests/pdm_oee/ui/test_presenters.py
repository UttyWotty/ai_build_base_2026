"""Pure command center formatting: percentages, hours, evidence lines, slots, titles, and draft ordering.

Evidence must say the value, the unit, the healthy range, and whether the value is outside it.
Drafts sort by priority, then by deadline.
"""
from __future__ import annotations

from pdm_oee.ui.presenters import (
    MISSING,
    draft_title,
    evidence_line,
    hours,
    percent,
    slot_text,
    sort_drafts,
)

ITEM = {"label": "Spindle vibration", "unit": "mm_per_s", "mean_24h": 3.46, "normal_low": 0.4, "normal_high": 2.8}


def test_numbers() -> None:
    assert percent(0.8227) == "82.3%" and percent(None) == MISSING
    assert hours(1234.56) == "1,234.6 h" and hours(float("nan")) == MISSING


def test_evidence_lines_flag_values_outside_the_range() -> None:
    assert evidence_line(ITEM) == "Spindle vibration: 3.46 mm/s over the last day, healthy 0.4 to 2.8 mm/s (above healthy range)"
    assert evidence_line({**ITEM, "mean_24h": 1.5}).endswith("2.8 mm/s")
    assert "no running readings" in evidence_line({**ITEM, "mean_24h": None})


def test_slots_titles_and_order() -> None:
    planned = {"planned_slot": True, "slot_start": "2026-06-13 11:00", "slot_end": "2026-06-13 21:00", "repair_hours": 10}
    assert slot_text(planned).startswith("Planned stop from 2026-06-13 11:00")
    assert "unplanned stop of 10 h" in slot_text({**planned, "planned_slot": False})
    drafts = [{"priority": "P2", "deadline_at": "2026-06-10"}, {"priority": "P1", "deadline_at": "2026-06-12"},
              {"priority": "P1", "deadline_at": "2026-06-11"}]
    assert [(d["priority"], d["deadline_at"]) for d in sort_drafts(drafts)] == [("P1", "2026-06-11"), ("P1", "2026-06-12"), ("P2", "2026-06-10")]
    title = draft_title({"priority": "P1", "asset_id": "A", "failure_mode": "m", "raised_at": "t", "status": "draft"}, {"m": "Mode"})
    assert title == "P1  A  Mode  (raised t, draft)"
