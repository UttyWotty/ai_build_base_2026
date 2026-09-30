"""The failure prediction setup from docs/plan.md section 4, as one record with explicit, documented defaults.

Every duration is in hours so the hourly panel can use them directly.
The split puts model fitting, threshold choice, and testing in three consecutive, non-overlapping blocks of time.
"""
from __future__ import annotations

from dataclasses import dataclass

HOURS_PER_DAY = 24


@dataclass(frozen=True)
class PredictionSettings:
    """Horizon, lead, baseline, alert budget, and the time split."""

    # A row is positive when its failure mode fails within this many hours.
    horizon_hours: int = 7 * HOURS_PER_DAY
    # An alert is useful only if it starts at least this long before the failure.
    min_lead_hours: int = HOURS_PER_DAY
    # Sensors are re-baselined after a repair or a sensor swap, over this window; rows inside it are not scored.
    baseline_hours: int = 14 * HOURS_PER_DAY
    # A new alert starts only after this many hours without the score above threshold.
    quiet_hours: int = HOURS_PER_DAY
    # The threshold is the most sensitive one with at most this many false alerts per asset per month.
    false_alerts_per_asset_month: float = 1.0
    # Months from the start of the data: fit the model before fit_months, choose the threshold before test_months.
    fit_months: int = 6
    test_start_months: int = 8
    # Rolling windows for features.
    short_window_hours: int = HOURS_PER_DAY
    long_window_hours: int = 7 * HOURS_PER_DAY


DEFAULT_SETTINGS = PredictionSettings()
