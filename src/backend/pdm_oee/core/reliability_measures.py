"""Reliability measures for a period: operating hours, failures, and repairs per asset and component, and PM compliance.

Each measure follows its measures.yaml definition: failures count by failure time, repairs by restore time, operating
hours are the asset's running hours in the period, and preventive tasks count by due date.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from pdm_oee.core.enums import MachineState, WorkType

HOURS = pd.Timedelta(hours=1)


def component_measures(states: pd.DataFrame, failures: pd.DataFrame, components: pd.DataFrame,
                       start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """operating_hours, functional_failures, repair_hours, and repairs per asset and component in [start, end)."""
    running = states[states["state"] == MachineState.RUNNING.value]
    clipped = (running["end_at"].clip(upper=end) - running["start_at"].clip(lower=start)).clip(lower=pd.Timedelta(0))
    hours = (clipped / HOURS).groupby(running["asset_id"]).sum()
    failed = failures[(failures["failed_at"] >= start) & (failures["failed_at"] < end)]
    restored = failures[(failures["restored_at"] >= start) & (failures["restored_at"] < end)]
    result = components.copy()
    result["operating_hours"] = result["asset_id"].map(hours).fillna(0.0)
    keys = ["asset_id", "component"]
    result = result.merge(failed.groupby(keys).size().rename("functional_failures").reset_index(), on=keys, how="left")
    repair = restored.assign(hours=(restored["restored_at"] - restored["failed_at"]) / HOURS).groupby(keys)["hours"]
    result = result.merge(repair.sum().rename("repair_hours").reset_index(), on=keys, how="left")
    result = result.merge(repair.size().rename("repairs").reset_index(), on=keys, how="left")
    return result.fillna({"functional_failures": 0, "repair_hours": 0.0, "repairs": 0})


def preventive_measures(work_orders: pd.DataFrame, assets: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    """pm_due and pm_completed_on_time per asset for tasks due in [start, end)."""
    preventive = work_orders[work_orders["work_type"] == WorkType.PREVENTIVE.value].copy()
    due = pd.to_datetime(preventive["due_date"]).dt.date
    preventive = preventive[(due >= start) & (due < end)]
    on_time = pd.to_datetime(preventive["closed_at"]).dt.date <= pd.to_datetime(preventive["due_date"]).dt.date
    result = assets[["asset_id"]].copy()
    result["pm_due"] = result["asset_id"].map(preventive.groupby("asset_id").size()).fillna(0)
    result["pm_completed_on_time"] = result["asset_id"].map(on_time.groupby(preventive["asset_id"]).sum()).fillna(0)
    return result
