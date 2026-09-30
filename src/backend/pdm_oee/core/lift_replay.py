"""Estimates the OEE a period would have had if caught failures had been repaired as planned work.

A caught failure repaired in a planned slot gives back all of its breakdown minutes inside shifts; one repaired in an
unplanned stop gives back its breakdown minutes less the planned repair time. A false alert that needs an unplanned stop
costs an inspection. Recovered minutes produce at the asset's own performance and quality for the period.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

MINUTES_PER_HOUR = 60


@dataclass(frozen=True)
class LiftEstimate:
    """Before and after, with the minutes behind the difference."""

    oee_before: float
    oee_after: float
    availability_before: float
    availability_after: float
    recovered_minutes: float
    inspection_minutes: float
    assumptions: tuple[str, ...]


ASSUMPTIONS = (
    "A caught failure repaired in a planned slot costs no production time.",
    "A caught failure without a slot costs only its planned repair time as an unplanned stop.",
    "A false alert that needs an unplanned stop costs an inspection of {inspection_hours} h.",
    "Recovered minutes produce at the asset's own performance and quality over the period.",
)


def recovered_minutes(caught: pd.DataFrame, in_shift_breakdown: pd.Series) -> pd.Series:
    """Per caught failure: breakdown minutes in shifts, less the planned repair when there was no slot.

    caught needs failure_id, planned_slot (bool), repair_hours; in_shift_breakdown is indexed by failure_id.
    """
    minutes = caught["failure_id"].map(in_shift_breakdown).fillna(0.0)
    repair = caught["repair_hours"] * MINUTES_PER_HOUR
    return minutes.where(caught["planned_slot"], (minutes - repair).clip(lower=0.0))


def estimate(measures: pd.DataFrame, recovered_by_asset: pd.Series, inspection_by_asset: pd.Series,
             inspection_hours: float) -> LiftEstimate:
    """OEE and availability before and after, from per-asset recovered and inspection minutes over the period."""
    per_asset = measures.groupby("asset_id")[["planned_production_time", "run_time", "valuable_operating_time"]].sum()
    gain = recovered_by_asset.reindex(per_asset.index).fillna(0.0) - inspection_by_asset.reindex(per_asset.index).fillna(0.0)
    yield_per_run_minute = (per_asset["valuable_operating_time"] / per_asset["run_time"].where(per_asset["run_time"] > 0)).fillna(0.0)
    planned = per_asset["planned_production_time"].sum()
    run_after = per_asset["run_time"] + gain
    valuable_after = per_asset["valuable_operating_time"] + gain * yield_per_run_minute
    return LiftEstimate(
        oee_before=float(per_asset["valuable_operating_time"].sum() / planned), oee_after=float(valuable_after.sum() / planned),
        availability_before=float(per_asset["run_time"].sum() / planned), availability_after=float(run_after.sum() / planned),
        recovered_minutes=float(recovered_by_asset.sum()), inspection_minutes=float(inspection_by_asset.sum()),
        assumptions=tuple(a.format(inspection_hours=inspection_hours) for a in ASSUMPTIONS))
