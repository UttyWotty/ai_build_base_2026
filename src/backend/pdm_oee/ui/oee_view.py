"""OEE and losses: availability, performance, quality, and OEE by a grouping for a period, and the loss waterfall.

Values are the governed metrics rolled up as sums; the waterfall starts at planned production time and ends at valuable
operating time. The period defaults to the last four weeks of data.
"""
from __future__ import annotations

from datetime import timedelta

import pandas as pd
import streamlit as st

from pdm_oee.services.oee_service import GROUPINGS
from pdm_oee.ui.presenters import percent
from pdm_oee.ui.resources import oee

FACTORS = ("availability", "performance", "quality", "oee")
DEFAULT_WEEKS = 4
MINUTES_PER_HOUR = 60


def render_oee() -> None:
    service = oee()
    last = pd.to_datetime(service.measures["shift_date"]).max().date()
    start, end = st.date_input("Period", value=(last - timedelta(weeks=DEFAULT_WEEKS), last))
    grouping = st.selectbox("By", GROUPINGS, index=GROUPINGS.index("line_id"))
    table = service.metrics(FACTORS, [grouping], start, end + timedelta(days=1))
    for factor in FACTORS:
        table[factor] = table[factor].map(percent)
    st.dataframe(table, hide_index=True, width="stretch")
    steps = service.loss_waterfall(start, end + timedelta(days=1))
    steps["hours"] = (steps["minutes"].abs() / MINUTES_PER_HOUR).round(1)
    st.subheader("Where planned time went (hours)")
    st.bar_chart(steps.set_index("step")["hours"], horizontal=True)
