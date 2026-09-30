"""Pure formatting for the command center: percentages, hours, evidence lines, slots, and draft ordering.

Nothing here imports Streamlit. Evidence is written the way a maintenance planner reads it: value, unit, and healthy range.
Drafts sort by priority, then by deadline, so the most urgent work is always at the top.
"""
from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

PERCENT = 100
MISSING = "no value"
UNIT_TEXT = {"mm_per_s": "mm/s", "deg_c": "°C", "rpm": "rpm", "bar": "bar", "ampere": "A"}
PRIORITY_ORDER = {"P1": 0, "P2": 1, "P3": 2}


def percent(value: object) -> str:
    return MISSING if value is None or pd.isna(value) else f"{float(value) * PERCENT:.1f}%"


def hours(value: object) -> str:
    return MISSING if value is None or pd.isna(value) else f"{float(value):,.1f} h"


def evidence_line(item: Mapping[str, object]) -> str:
    unit = UNIT_TEXT.get(str(item["unit"]), str(item["unit"]))
    value = item.get("mean_24h")
    reading = "no running readings" if value is None else f"{value} {unit}"
    above = value is not None and float(value) > float(item["normal_high"])
    below = value is not None and float(value) < float(item["normal_low"])
    flag = " (above healthy range)" if above else " (below healthy range)" if below else ""
    return f"{item['label']}: {reading} over the last day, healthy {item['normal_low']} to {item['normal_high']} {unit}{flag}"


def slot_text(draft: Mapping[str, object]) -> str:
    if draft.get("planned_slot"):
        return f"Planned stop from {draft['slot_start']} to {draft['slot_end']}"
    return f"No planned stop before the deadline: needs an unplanned stop of {draft['repair_hours']} h"


def draft_title(draft: Mapping[str, object], mode_labels: Mapping[str, str]) -> str:
    mode = mode_labels.get(str(draft["failure_mode"]), str(draft["failure_mode"]))
    return f"{draft['priority']}  {draft['asset_id']}  {mode}  (raised {draft['raised_at']}, {draft['status']})"


def sort_drafts(drafts: list[Mapping[str, object]]) -> list[Mapping[str, object]]:
    return sorted(drafts, key=lambda d: (PRIORITY_ORDER.get(str(d["priority"]), len(PRIORITY_ORDER)), str(d["deadline_at"])))
