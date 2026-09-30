"""Conforms MES state intervals: workcenters to assets, site codes to governed states and reasons, local time to UTC.

Rows are taken in their recorded sequence per workcenter, which settles the repeated hour of a daylight-saving fall-back;
each interval ends where the next begins. Running intervals must have no reason and stops must have one.
"""
from __future__ import annotations

import pandas as pd

from pdm_oee.core.enums import MachineState
from pdm_oee.core.source_mapping_model import SourceMappings
from pdm_oee.data_pipeline.conform.errors import ConformError
from pdm_oee.data_pipeline.conform.local_clock import localize_ordered
from pdm_oee.data_pipeline.conform.source_layout import MES_STATES, Sources

NO_REASON = ""


def conform_states(sources: Sources, assets: pd.DataFrame, mappings: SourceMappings) -> pd.DataFrame:
    states = sources[MES_STATES]
    by_workcenter = assets.set_index("workcenter")
    unknown = sorted(set(states["WORKCENTER"]) - set(by_workcenter.index))
    if unknown:
        raise ConformError(f"{MES_STATES}: unknown workcenters {unknown}")
    frames = []
    for workcenter, rows in states.sort_values(["WORKCENTER", "SEQ"]).groupby("WORKCENTER", sort=True):
        asset = by_workcenter.loc[workcenter]
        site = mappings.sites[asset["site_id"]]
        start = localize_ordered(pd.to_datetime(rows["START_LOCAL"]), site.timezone)
        last_end = localize_ordered(pd.concat([pd.to_datetime(rows["START_LOCAL"]).iloc[-1:], pd.to_datetime(rows["END_LOCAL"]).iloc[-1:]]),
                                    site.timezone).iloc[-1]
        end = start.shift(-1)
        end.iloc[-1] = last_end
        frames.append(pd.DataFrame({"asset_id": asset["asset_id"], "state": _map(rows["STATE"], site.states, "state"),
                                    "reason": _reasons(rows, site.reasons, {c for c, v in site.states.items() if v is MachineState.RUNNING}), "start_at": start.to_numpy(), "end_at": end.to_numpy()}))
    return pd.concat(frames, ignore_index=True)


def _map(codes: pd.Series, mapping: dict, what: str) -> list:
    unknown = sorted(set(codes) - set(mapping))
    if unknown:
        raise ConformError(f"{MES_STATES}: unknown {what} codes {unknown}")
    return [mapping[c].value if isinstance(mapping[c], MachineState) else mapping[c] for c in codes]


def _reasons(rows: pd.DataFrame, mapping: dict, running_codes: set[str]) -> list:
    reasons = []
    for state, code in zip(rows["STATE"], rows["REASON"].fillna(NO_REASON)):
        if (code == NO_REASON) != (state in running_codes):
            raise ConformError(f"{MES_STATES}: state '{state}' with reason '{code}': only running has no reason")
        if code != NO_REASON and code not in mapping:
            raise ConformError(f"{MES_STATES}: unknown reason code '{code}'")
        reasons.append(None if code == NO_REASON else mapping[code])
    return reasons
