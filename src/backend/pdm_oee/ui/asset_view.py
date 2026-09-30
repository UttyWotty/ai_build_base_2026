"""Asset health: each sensor's daily running mean against its healthy range, plus failures, work orders, and alerts.

Everything comes through the investigation tools, so the page shows exactly what the language model would see.
The window is the 30 days up to a chosen day.
"""
from __future__ import annotations

from datetime import timedelta

import pandas as pd
import streamlit as st

from pdm_oee.ui.resources import catalog, toolbox

WINDOW_DAYS = 30
ONE_DAY = timedelta(days=1)


def render_asset() -> None:
    tools = toolbox()
    assets = tools.assets.set_index("asset_id")
    asset_id = st.selectbox("Asset", list(assets.index))
    last = pd.to_datetime(tools.oee.measures["shift_date"]).max().date()
    end_day = st.date_input("Up to", value=last, min_value=last - timedelta(days=365), max_value=last)
    start, end = end_day - timedelta(days=WINDOW_DAYS), end_day + ONE_DAY
    spec = catalog().plant.asset_classes[assets.loc[asset_id, "asset_class"]]
    for sensor in spec.sensors.values():
        trend = tools.sensor_trend(asset_id, sensor.id, start, end)
        if trend["values"]:
            frame = pd.DataFrame(trend["values"]).set_index("period")
            frame["healthy low"], frame["healthy high"] = trend["normal_range"]
            st.caption(f"{trend['label']} ({trend['unit']})")
            st.line_chart(frame)
    failures = tools.failures("asset", asset_id, start, end)
    st.subheader(f"Failures ({failures['count']})")
    st.dataframe(pd.DataFrame(failures["failures"]), hide_index=True, width="stretch")
    st.subheader("Work orders")
    st.dataframe(pd.DataFrame(tools.work_order_history(asset_id, start, end)), hide_index=True, width="stretch")
    alerts = tools.alerts("asset", asset_id, start, end)
    st.subheader(f"Alerts ({alerts['count']})")
    st.dataframe(pd.DataFrame(alerts["alerts"]), hide_index=True, width="stretch")
