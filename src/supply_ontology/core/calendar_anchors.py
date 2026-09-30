"""Named calendar periods computed from the data's as-of date, so relative phrases never depend on model arithmetic.

"Last quarter" means the most recent complete calendar quarter; "to date" periods end on the as-of date.
The prompt lists these anchors and the model copies the matching range instead of computing one.
"""
from __future__ import annotations

from datetime import date, timedelta

from supply_ontology.core.query_spec import TimeRange

MONTHS_PER_QUARTER = 3
ONE_DAY = timedelta(days=1)


def _quarter_start(day: date) -> date:
    return date(day.year, (day.month - 1) // MONTHS_PER_QUARTER * MONTHS_PER_QUARTER + 1, 1)


def _previous_month_start(day: date) -> date:
    first = day.replace(day=1)
    return (first - ONE_DAY).replace(day=1)


def calendar_anchors(as_of: date) -> dict[str, TimeRange]:
    """Named periods relative to `as_of`."""
    quarter_start = _quarter_start(as_of)
    last_quarter_start = _quarter_start(quarter_start - ONE_DAY)
    month_start = as_of.replace(day=1)
    last_month_start = _previous_month_start(as_of)
    twelve_months_start = month_start
    for _ in range(12):
        twelve_months_start = _previous_month_start(twelve_months_start)
    return {
        "last quarter": TimeRange(last_quarter_start, quarter_start - ONE_DAY),
        "this quarter to date": TimeRange(quarter_start, as_of),
        "last month": TimeRange(last_month_start, month_start - ONE_DAY),
        "this month to date": TimeRange(month_start, as_of),
        "this year to date": TimeRange(date(as_of.year, 1, 1), as_of),
        "last year": TimeRange(date(as_of.year - 1, 1, 1), date(as_of.year - 1, 12, 31)),
        "last 12 complete months": TimeRange(twelve_months_start, month_start - ONE_DAY),
    }
