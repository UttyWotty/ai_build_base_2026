"""The prediction model: backtest results for the classifier and the baseline, and the OEE lift estimate with assumptions.

Results come from the files `make predict` and `make alerts` write; nothing is recomputed here.
Missing files are explained with the command that creates them.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from pdm_oee.services.command_center import model_report, replay_lift
from pdm_oee.ui.presenters import percent
from pdm_oee.ui.resources import model_dir, replay_path


def render_model() -> None:
    report = model_report(model_dir())
    if report is None:
        st.info("No model yet. Run `make predict`.")
    else:
        blocks = report["blocks"]
        st.caption(f"Fitted {blocks['fit']}; threshold chosen {blocks['validation']}; tested {blocks['test']}.")
        rows = [{"predictor": name, "caught": f"{r['caught_failures']} of {r['evaluable_failures']}",
                 "false alerts per asset-month": round(r["false_alerts_per_asset_month"], 2), "late alerts": r["late_alerts"],
                 "median lead (h)": None if r["median_lead_hours"] is None else round(r["median_lead_hours"])}
                for name, r in report["test"].items()]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    lift = replay_lift(replay_path())
    if lift is None:
        st.info("No alert replay yet. Run `make alerts`.")
        return
    columns = st.columns(2)
    columns[0].metric("OEE, test period", percent(lift["oee_after"]), delta=f"{(lift['oee_after'] - lift['oee_before']) * 100:+.2f} pts")
    columns[1].metric("Availability", percent(lift["availability_after"]),
                      delta=f"{(lift['availability_after'] - lift['availability_before']) * 100:+.2f} pts")
    st.markdown("Assumptions behind the estimate:")
    for assumption in lift["assumptions"]:
        st.markdown(f"- {assumption}")
