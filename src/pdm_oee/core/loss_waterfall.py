"""The OEE loss waterfall: planned production time minus each governed loss equals valuable operating time.

Stop-reason losses take the minutes of their reasons' long stops; small stops take every short loss stop; reduced speed
is what remains of run time after small stops and ideal time; the two reject losses are scrap at ideal cycle time.
Reduced speed is negative only when an ideal cycle time is wrong, and the waterfall then still reconciles.
"""
from __future__ import annotations

import pandas as pd

from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.core.enums import LossSource
from pdm_oee.core.shift_measures import LONG_LOSS, SECONDS_PER_MINUTE, classify_stops

START_COLUMN = "planned_production_time"
END_COLUMN = "valuable_operating_time"


def loss_minutes(pieces: pd.DataFrame, measures: pd.DataFrame, catalog: PlantCatalog) -> pd.DataFrame:
    """One column per governed loss (minutes), per asset and shift, aligned with `measures` rows."""
    pieces = pieces.assign(kind=classify_stops(pieces, catalog))
    booked = {reason.id: reason.loss for reason in catalog.losses.loss_reasons.values()}
    long_stops = pieces[pieces["kind"] == LONG_LOSS].assign(loss=lambda f: f["reason"].map(booked))
    by_loss = long_stops.pivot_table(index=["asset_id", "shift_id"], columns="loss", values="minutes", aggfunc="sum", fill_value=0.0)
    result = measures[["asset_id", "shift_id"]].merge(by_loss.reset_index(), on=["asset_id", "shift_id"], how="left").fillna(0.0)
    ideal_minutes = measures["ideal_cycle_s"].to_numpy() / SECONDS_PER_MINUTE
    for loss in catalog.losses.losses.values():
        if loss.source is LossSource.STOP_REASON:
            result[loss.id] = result[loss.id] if loss.id in result else 0.0
        elif loss.source is LossSource.SHORT_STOP:
            result[loss.id] = measures["small_stop_time"].to_numpy()
        elif loss.source is LossSource.SPEED_GAP:
            result[loss.id] = (measures["run_time"] - measures["small_stop_time"] - measures["ideal_run_time"]).to_numpy()
        elif loss.source is LossSource.STARTUP_SCRAP:
            result[loss.id] = measures["startup_scrap_count"].to_numpy() * ideal_minutes
        else:
            result[loss.id] = (measures["scrap_count"] - measures["startup_scrap_count"]).to_numpy() * ideal_minutes
    return result[["asset_id", "shift_id", *catalog.losses.losses]]


def waterfall(measures: pd.DataFrame, losses: pd.DataFrame, catalog: PlantCatalog) -> pd.DataFrame:
    """Summed waterfall steps (label, minutes) from planned production time down to valuable operating time."""
    steps = [(catalog.measures[START_COLUMN].label, float(measures[START_COLUMN].sum()))]
    steps += [(loss.label, -float(losses[loss.id].sum())) for loss in catalog.losses.losses.values()]
    steps.append((catalog.measures[END_COLUMN].label, float(measures[END_COLUMN].sum())))
    return pd.DataFrame(steps, columns=["step", "minutes"])
