"""CMMS work orders and failure events: corrective orders for failures, preventive orders for services, instrument work.

Each failure gets one corrective order, which also names the failure event. Recorded closures can lag the real repair.
Source-only noise (orders whose failure code was never entered, duplicate orders for one breakdown) is returned
separately, because it belongs to how the CMMS is used, not to what happened.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from pdm_oee.core.plant_model import PlantModel
from pdm_oee.data_pipeline.synthetic.calendar import MINUTES_PER_DAY
from pdm_oee.data_pipeline.synthetic.maintenance_plan import InstrumentWork
from pdm_oee.data_pipeline.synthetic.reference import (
    CREATE_DELAY_MINUTES,
    DUPLICATE_DELAY_MINUTES,
    DUPLICATE_SHARE,
    FAILURE_TEXT,
    LATE_CLOSE_DAYS,
    LATE_CLOSE_SHARE,
    MISSING_CODE_SHARE,
    PM_CREATE_LEAD_DAYS,
)

MINUTES_PER_HOUR = 60
INSTRUMENT_MINUTES = 60
START_DELAY_MINUTES = 5
# CMMS work order numbers; duplicates entered by mistake get numbers from DUPLICATE_WO_NUMBER upwards.
FIRST_WO_NUMBER = 4000001
DUPLICATE_WO_NUMBER = 4900001


@dataclass(frozen=True)
class Maintenance:
    """Truth work orders and failure events, plus the CMMS noise the renderer adds."""

    work_orders: pd.DataFrame
    failure_events: pd.DataFrame
    missing_code_ids: frozenset[str]
    duplicates: pd.DataFrame


def build_maintenance(failures: pd.DataFrame, preventive: pd.DataFrame, instruments: list[InstrumentWork],
                      assets: pd.DataFrame, plant: PlantModel, rng: np.random.Generator) -> Maintenance:
    """All work orders in creation order, with ids assigned in that order."""
    rows = [_corrective(f, rng) for f in failures.itertuples()] if len(failures) else []
    rows += [_preventive(p) for p in preventive.itertuples()]
    classes = assets.set_index("asset_id")["asset_class"]
    rows += [_instrument(w, plant.asset_classes[classes[w.asset_id]].sensors[w.sensor]) for w in instruments]
    orders = pd.DataFrame(rows).sort_values(["created_minute", "asset_id"], kind="stable").reset_index(drop=True)
    orders.insert(0, "wo_id", [str(FIRST_WO_NUMBER + n) for n in range(len(orders))])
    corrective = orders[orders["work_type"] == "corrective"]
    events = corrective.rename(columns={"wo_id": "failure_id"})[
        ["failure_id", "asset_id", "component", "failure_mode", "failed_minute", "restored_minute"]].reset_index(drop=True)
    missing = frozenset(corrective.loc[rng.random(len(corrective)) < MISSING_CODE_SHARE, "wo_id"])
    duplicated = corrective[rng.random(len(corrective)) < DUPLICATE_SHARE]
    duplicates = pd.DataFrame({"original_wo_id": duplicated["wo_id"].to_numpy(),
                               "delay_minutes": rng.integers(DUPLICATE_DELAY_MINUTES[0], DUPLICATE_DELAY_MINUTES[1] + 1,
                                                             len(duplicated))})
    return Maintenance(orders.drop(columns=["failed_minute", "restored_minute"]), events, missing, duplicates)


def _corrective(failure: object, rng: np.random.Generator) -> dict:
    created = failure.failed_minute + int(rng.integers(CREATE_DELAY_MINUTES[0], CREATE_DELAY_MINUTES[1] + 1))
    late = int(rng.integers(LATE_CLOSE_DAYS[0], LATE_CLOSE_DAYS[1] + 1)) * MINUTES_PER_DAY if rng.random() < LATE_CLOSE_SHARE else 0
    hours = (failure.restored_minute - failure.failed_minute) / MINUTES_PER_HOUR
    return {"asset_id": failure.asset_id, "component": failure.component, "work_type": "corrective",
            "failure_mode": failure.failure_mode, "created_minute": created, "started_minute": created + START_DELAY_MINUTES,
            "closed_minute": failure.restored_minute + late, "due_day": None, "labour_hours": round(hours, 1),
            "description": FAILURE_TEXT[failure.failure_mode], "sensor": None,
            "failed_minute": failure.failed_minute, "restored_minute": failure.restored_minute}


def _preventive(window: object) -> dict:
    return {"asset_id": window.asset_id, "component": None, "work_type": "preventive", "failure_mode": None,
            "created_minute": max(0, (window.due_day - PM_CREATE_LEAD_DAYS) * MINUTES_PER_DAY),
            "started_minute": window.start_minute, "closed_minute": window.end_minute, "due_day": window.due_day,
            "labour_hours": round((window.end_minute - window.start_minute) / MINUTES_PER_HOUR, 1),
            "description": "Routine service: lubrication, filters, inspection", "sensor": None,
            "failed_minute": None, "restored_minute": None}


def _instrument(work: InstrumentWork, spec: object) -> dict:
    return {"asset_id": work.asset_id, "component": spec.component, "work_type": "instrument", "failure_mode": None,
            "created_minute": work.minute, "started_minute": work.minute, "closed_minute": work.minute + INSTRUMENT_MINUTES,
            "due_day": None, "labour_hours": 1.0, "description": f"Replaced {spec.label.lower()} sensor", "sensor": work.sensor,
            "failed_minute": None, "restored_minute": None}
