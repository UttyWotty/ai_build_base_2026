"""Collapses the minute codes of each asset into the MES state intervals: running, planned stop, or unplanned stop.

Consecutive minutes with the same code become one interval, so the interval's length is the stop duration the MES records.
The governed reason is kept for every stop; running intervals have no reason.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pdm_oee.core.loss_model import LossTaxonomy
from pdm_oee.data_pipeline.synthetic.minute_states import RUNNING, StateCodes

PLANNED_STOP = "planned_stop"
UNPLANNED_STOP = "unplanned_stop"


def state_intervals(minute_states: dict[str, np.ndarray], codes: StateCodes, losses: LossTaxonomy) -> pd.DataFrame:
    """One row per interval: asset_id, start_minute, end_minute, state, reason."""
    kinds = [RUNNING if n == RUNNING else PLANNED_STOP if n in losses.planned_stop_reasons else UNPLANNED_STOP
             for n in codes.names]
    frames = []
    for asset_id, states in minute_states.items():
        change = np.flatnonzero(np.diff(states)) + 1
        starts = np.concatenate(([0], change))
        ends = np.concatenate((change, [len(states)]))
        values = states[starts]
        frames.append(pd.DataFrame({
            "asset_id": asset_id, "start_minute": starts, "end_minute": ends,
            "state": [kinds[v] for v in values],
            "reason": [None if codes.names[v] == RUNNING else codes.names[v] for v in values],
        }))
    return pd.concat(frames, ignore_index=True)
