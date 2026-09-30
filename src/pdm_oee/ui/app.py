"""Streamlit entry point for the command center: five tabs from alert triage to the prediction model.

Run with `make ui`. The page loads the conformed data and saved results but contacts the local model only when a question
is asked on the Ask tab.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from pdm_oee.services.settings import LLM_MODEL
from pdm_oee.ui.ask_view import render_ask
from pdm_oee.ui.asset_view import render_asset
from pdm_oee.ui.model_view import render_model
from pdm_oee.ui.oee_view import render_oee
from pdm_oee.ui.queue_view import render_queue
from pdm_oee.ui.resources import oee

PAGE_TITLE = "PdM and OEE Command Center"
TAB_NAMES = ("Alert queue", "Asset health", "OEE and losses", "Ask", "Prediction model")


def main() -> None:
    st.set_page_config(page_title=PAGE_TITLE, layout="wide")
    st.title(PAGE_TITLE)
    last = pd.to_datetime(oee().measures["shift_date"]).max().date()
    with st.sidebar:
        st.caption(f"Data up to {last}. Language model: {LLM_MODEL}.")
    queue, asset, losses, ask, model = st.tabs(TAB_NAMES)
    with queue:
        render_queue()
    with asset:
        render_asset()
    with losses:
        render_oee()
    with ask:
        render_ask()
    with model:
        render_model()


main()
