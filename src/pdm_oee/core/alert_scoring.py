"""Turns hourly scores into alerts and scores alerts against failures, event by event rather than row by row.

An alert starts when an eligible row's score reaches the threshold after quiet_hours without one. A start is useful when
its asset and mode fail between min_lead_hours and horizon_hours later, late when the failure is sooner, and false otherwise.
A failure counts as evaluable when at least one eligible row could have warned it in time.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from pdm_oee.core.prediction_settings import PredictionSettings

DAYS_PER_MONTH = 30.44
HOURS_PER_DAY = 24
NO_FAILURE = -1


@dataclass(frozen=True)
class ScoringContext:
    """Per-row arrays derived once from a panel sorted by asset, mode, and hour."""

    eligible: np.ndarray
    lead: np.ndarray
    failure_key: np.ndarray
    group_start: np.ndarray
    group_count: int


@dataclass(frozen=True)
class Evaluation:
    """Event-level results for one threshold over one period."""

    threshold: float
    evaluable_failures: int
    caught_failures: int
    late_alerts: int
    false_alerts: int
    false_alerts_per_asset_month: float
    median_lead_hours: float | None

    @property
    def recall(self) -> float:
        return self.caught_failures / self.evaluable_failures if self.evaluable_failures else 0.0


def scoring_context(panel: pd.DataFrame) -> ScoringContext:
    group = (panel["asset_id"] + "|" + panel["failure_mode"]).to_numpy()
    first = np.r_[True, group[1:] != group[:-1]]
    group_start = np.maximum.accumulate(np.where(first, np.arange(len(group)), 0))
    failure = panel["asset_id"] + "|" + panel["failure_mode"] + "|" + panel["next_failure_at"].astype(str)
    codes, _ = pd.factorize(failure.where(panel["next_failure_at"].notna()))
    return ScoringContext(panel["eligible"].to_numpy(), panel["time_to_failure_hours"].to_numpy(dtype=float),
                          codes, group_start, int(first.sum()))


def alert_starts(context: ScoringContext, scores: np.ndarray, threshold: float, quiet_hours: int) -> np.ndarray:
    """Rows where an alert starts."""
    above = (scores >= threshold) & context.eligible
    positions = np.arange(len(above))
    running = np.concatenate([[0], np.cumsum(above)])
    back = np.maximum(positions - quiet_hours, context.group_start)
    return above & (running[positions] - running[back] == 0)


def evaluate(context: ScoringContext, scores: np.ndarray, threshold: float, period: np.ndarray,
             settings: PredictionSettings, asset_count: int) -> Evaluation:
    """Caught, late, and false alerts for starts inside the period, and failures that could have been caught there."""
    starts = alert_starts(context, scores, threshold, settings.quiet_hours) & period
    lead = context.lead
    in_window = (lead >= settings.min_lead_hours) & (lead <= settings.horizon_hours)
    useful = starts & in_window
    late = starts & (lead > 0) & (lead < settings.min_lead_hours)
    false = starts & ~useful & ~late
    evaluable = np.unique(context.failure_key[context.eligible & period & in_window])
    caught = np.intersect1d(np.unique(context.failure_key[useful]), evaluable)
    leads = pd.Series(lead[useful]).groupby(context.failure_key[useful]).max().reindex(caught).to_numpy()
    months = period.sum() / max(1, context.group_count) / HOURS_PER_DAY / DAYS_PER_MONTH
    return Evaluation(threshold, len(evaluable), len(caught), int(late.sum()), int(false.sum()),
                      float(false.sum()) / max(1e-9, asset_count * months),
                      float(np.median(leads)) if len(leads) else None)


def choose_threshold(context: ScoringContext, scores: np.ndarray, period: np.ndarray, settings: PredictionSettings,
                     asset_count: int, candidates: np.ndarray) -> Evaluation:
    """The most sensitive threshold within the false-alert budget on the period (ties go to the higher threshold)."""
    best = None
    for threshold in np.sort(np.unique(candidates))[::-1]:
        result = evaluate(context, scores, float(threshold), period, settings, asset_count)
        if result.false_alerts_per_asset_month > settings.false_alerts_per_asset_month:
            break
        if best is None or result.caught_failures > best.caught_failures:
            best = result
    return best if best is not None else evaluate(context, scores, float(np.max(candidates)), period, settings, asset_count)
