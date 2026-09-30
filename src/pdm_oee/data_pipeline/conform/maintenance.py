"""Conforms CMMS work orders and derives failure events from them and the MES breakdowns.

Every corrective order belongs to the MES breakdown on its asset that was open when the order was created; when a
breakdown has several orders, the earliest is the real one and the rest are duplicates. Failure times come from the
breakdown, never from the order's closure date. A blank failure code is recovered from the governed keywords.
"""
from __future__ import annotations

import pandas as pd

from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.core.enums import WorkType
from pdm_oee.core.source_mapping_model import SourceMappings
from pdm_oee.core.terms import normalize_text
from pdm_oee.data_pipeline.conform.errors import ConformError
from pdm_oee.data_pipeline.conform.local_clock import localize
from pdm_oee.data_pipeline.conform.source_layout import CMMS_ORDERS, Sources

BREAKDOWN_REASON = "equipment_failure"
WORK_ORDER_COLUMNS = ["wo_id", "asset_id", "component", "work_type", "failure_mode", "created_at", "started_at",
                      "closed_at", "labour_hours", "description", "sensor", "due_date"]


def conform_maintenance(sources: Sources, assets: pd.DataFrame, states: pd.DataFrame, catalog: PlantCatalog,
                        mappings: SourceMappings) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Work orders without duplicates, and one failure event per breakdown."""
    orders = _orders(sources, assets, mappings)
    corrective = orders[orders["work_type"] == WorkType.CORRECTIVE.value]
    linked = _link_breakdowns(corrective, states)
    kept = linked.sort_values(["created_at", "wo_id"]).drop_duplicates(["asset_id", "start_at"], keep="first")
    orders = orders[(orders["work_type"] != WorkType.CORRECTIVE.value) | orders["wo_id"].isin(kept["wo_id"])].copy()
    classes = assets.set_index("asset_id")["asset_class"]
    details = [_detail(row, classes[row.asset_id], catalog, mappings) for row in orders.itertuples()]
    orders["failure_mode"], orders["component"], orders["sensor"] = zip(*details) if details else ([], [], [])
    failures = kept.merge(orders[["wo_id", "failure_mode", "component"]], on="wo_id")
    failures = failures.rename(columns={"wo_id": "failure_id", "start_at": "failed_at", "end_at": "restored_at"})
    return (orders[WORK_ORDER_COLUMNS].reset_index(drop=True),
            failures[["failure_id", "asset_id", "component", "failure_mode", "failed_at", "restored_at"]].reset_index(drop=True))


def _orders(sources: Sources, assets: pd.DataFrame, mappings: SourceMappings) -> pd.DataFrame:
    raw = sources[CMMS_ORDERS].merge(assets[["asset_number", "asset_id", "site_id"]], left_on="ASSET_NO", right_on="asset_number", how="left")
    if raw["asset_id"].isna().any():
        raise ConformError(f"{CMMS_ORDERS}: unknown asset numbers {sorted(raw.loc[raw['asset_id'].isna(), 'ASSET_NO'].unique())}")
    unknown = sorted(set(raw["TYPE"]) - set(mappings.cmms.work_types))
    if unknown:
        raise ConformError(f"{CMMS_ORDERS}: unknown work types {unknown}")
    zones = raw["site_id"].map({s.site_id: s.timezone for s in mappings.sites.values()})
    times = {}
    for column, name in (("CREATED", "created_at"), ("STARTED", "started_at"), ("COMPLETED", "closed_at")):
        times[name] = pd.concat([localize(pd.to_datetime(raw.loc[zones == z, column]), z) for z in zones.unique()]).sort_index()
    return pd.DataFrame({"wo_id": raw["WO_NO"], "asset_id": raw["asset_id"],
                         "work_type": raw["TYPE"].map({c: t.value for c, t in mappings.cmms.work_types.items()}),
                         "failure_code": raw["FAILURE_CODE"].fillna(""), **times, "labour_hours": raw["LABOUR_HOURS"].astype(float),
                         "description": raw["DESCRIPTION"],
                         "due_date": [None if pd.isna(d) else pd.Timestamp(d).date() for d in raw["DUE_DATE"]]})


def _link_breakdowns(corrective: pd.DataFrame, states: pd.DataFrame) -> pd.DataFrame:
    breakdowns = states[states["reason"] == BREAKDOWN_REASON][["asset_id", "start_at", "end_at"]].sort_values("start_at")
    linked = pd.merge_asof(corrective.sort_values("created_at"), breakdowns, left_on="created_at", right_on="start_at",
                           by="asset_id", direction="backward")
    open_then = linked["end_at"] > linked["created_at"]
    if not open_then.all():
        raise ConformError(f"{CMMS_ORDERS}: corrective orders with no open breakdown: {sorted(linked.loc[~open_then, 'wo_id'])[:5]}")
    return linked[["wo_id", "asset_id", "created_at", "start_at", "end_at"]]


def _detail(row: object, asset_class: str, catalog: PlantCatalog, mappings: SourceMappings) -> tuple:
    """(failure mode, component, sensor) for one order."""
    spec = catalog.plant.asset_classes[asset_class]
    if row.work_type == WorkType.PREVENTIVE.value:
        return None, None, None
    if row.work_type == WorkType.INSTRUMENT.value:
        text = normalize_text(row.description)
        matches = [s for s in spec.sensors.values() if normalize_text(s.label) in text]
        if len(matches) != 1:
            raise ConformError(f"{CMMS_ORDERS}: order {row.wo_id} names {len(matches)} sensors of a {asset_class}")
        return None, matches[0].component, matches[0].id
    mode = mappings.cmms.failure_codes.get(row.failure_code) if row.failure_code else _mode_from_text(row, spec, mappings)
    if mode not in spec.failure_modes:
        raise ConformError(f"{CMMS_ORDERS}: order {row.wo_id} has failure '{mode}', not a {asset_class} failure mode")
    return mode, spec.failure_modes[mode].component, None


def _mode_from_text(row: object, spec: object, mappings: SourceMappings) -> str | None:
    text = normalize_text(row.description)
    matches = [m for m in spec.failure_modes if any(normalize_text(k) in text for k in mappings.cmms.failure_keywords.get(m, ()))]
    if len(matches) != 1:
        raise ConformError(f"{CMMS_ORDERS}: order {row.wo_id} has no failure code and its text matches {matches}")
    return matches[0]
