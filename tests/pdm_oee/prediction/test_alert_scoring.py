"""Event-level alert scoring on hand-built rows: alert starts, useful, late, and false alerts, and the threshold choice.

One asset and mode over 20 hours with a failure at 20:00; a decision at hour h is 19 - h hours ahead of it.
Horizon 10 h, minimum lead 2 h, quiet 3 h. Scores above threshold at hours 1, 9-10, 14, and 18 give alert starts at
1 (18 h ahead: false), 9 (10 h: useful), 14 (5 h: useful, same failure), and 18 (1 h: late).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pdm_oee.core.alert_scoring import (
    alert_starts,
    choose_threshold,
    evaluate,
    scoring_context,
)
from pdm_oee.core.prediction_settings import PredictionSettings

SETTINGS = PredictionSettings(horizon_hours=10, min_lead_hours=2, quiet_hours=3, false_alerts_per_asset_month=10_000)
HOURS = 20
FAILURE = pd.Timestamp("2026-01-01 20:00")


def panel() -> pd.DataFrame:
    hours = pd.date_range("2026-01-01", periods=HOURS, freq="h")
    lead = (FAILURE - (hours + pd.Timedelta(hours=1))) / pd.Timedelta(hours=1)
    return pd.DataFrame({"asset_id": "A", "failure_mode": "m", "hour": hours, "eligible": True,
                         "next_failure_at": FAILURE, "time_to_failure_hours": lead})


SCORES = np.zeros(HOURS)
SCORES[[1, 9, 10, 14, 18]] = 0.9


def test_quiet_hours_merge_nearby_scores_into_one_alert() -> None:
    starts = alert_starts(scoring_context(panel()), SCORES, 0.5, SETTINGS.quiet_hours)
    assert list(np.flatnonzero(starts)) == [1, 9, 14, 18]


def test_useful_late_and_false_alerts() -> None:
    result = evaluate(scoring_context(panel()), SCORES, 0.5, np.ones(HOURS, bool), SETTINGS, asset_count=1)
    assert (result.caught_failures, result.evaluable_failures, result.late_alerts, result.false_alerts) == (1, 1, 1, 1)
    assert result.median_lead_hours == 10


def test_ineligible_rows_never_alert() -> None:
    rows = panel()
    rows["eligible"] = False
    result = evaluate(scoring_context(rows), SCORES, 0.5, np.ones(HOURS, bool), SETTINGS, asset_count=1)
    assert (result.caught_failures, result.evaluable_failures, result.false_alerts) == (0, 0, 0)


def test_threshold_choice_respects_the_false_alert_budget() -> None:
    strict = PredictionSettings(horizon_hours=10, min_lead_hours=2, quiet_hours=3, false_alerts_per_asset_month=0.0)
    scores = SCORES.copy()
    scores[1] = 0.95
    chosen = choose_threshold(scoring_context(panel()), scores, np.ones(HOURS, bool), strict, 1, np.array([0.5, 0.92, 0.99]))
    assert chosen.threshold == 0.99 and chosen.false_alerts == 0
