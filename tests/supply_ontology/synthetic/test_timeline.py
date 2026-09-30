"""Tests for week arithmetic and day-offset conversion.

Weeks run Monday to Sunday from the horizon start.
Missing offsets must convert to None so Parquet stores a null date.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from supply_ontology.data_pipeline.synthetic.timeline import Timeline, offsets_to_dates

TIMELINE = Timeline(date(2024, 9, 30), 4)


def test_week_boundaries() -> None:
    assert TIMELINE.week_start(1) == date(2024, 10, 7)
    assert TIMELINE.week_end(0) == date(2024, 10, 6)
    assert TIMELINE.week_of(date(2024, 10, 6)) == 0
    assert TIMELINE.week_of(date(2024, 9, 29)) == -1
    assert TIMELINE.end == date(2024, 10, 27)


def test_offsets_to_dates_keeps_nulls() -> None:
    converted = offsets_to_dates(TIMELINE.start, pd.Series([0, None, 7], dtype="Int64"))
    assert list(converted) == [date(2024, 9, 30), None, date(2024, 10, 7)]
