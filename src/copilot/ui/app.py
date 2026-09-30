"""Streamlit entry point for the operations copilot: control room, Ask, Approvals, and How it works.

Run with `make app`. The sidebar sets the demo clock, the moment every view and the agent treat as now.
The page contacts the model only when the copilot is asked something.
"""
from __future__ import annotations

from datetime import datetime

import streamlit as st

from copilot.ui import presenters as p
from copilot.ui.about_view import render_about
from copilot.ui.approvals_view import render_approvals
from copilot.ui.ask_view import render_ask
from copilot.ui.control_view import render_control_room
from copilot.ui.resources import AS_OF_KEY, services
from llm_gateway.factory import default_selection

PRODUCT_NAME = "Operations Copilot"
TAGLINE = "From a failure alert to an approved plan: spares, suppliers, and customers in one view."
TAB_NAMES = ("Control room", "Ask the copilot", "Approvals", "How it works")
CUSTOM = "Custom time"


def _sidebar() -> None:
    with st.sidebar:
        st.header("Demo clock")
        names = [s.label for s in p.SCENARIOS] + [CUSTOM]
        choice = st.radio("Scenario", names, key="scenario")
        if choice == CUSTOM:
            day = st.date_input("Date", value=p.SCENARIOS[0].as_of.date(), key="custom-date")
            time = st.time_input("Time (UTC)", value=p.SCENARIOS[0].as_of.time(), key="custom-time")
            st.session_state[AS_OF_KEY] = datetime.combine(day, time)
        else:
            scenario = next(s for s in p.SCENARIOS if s.label == choice)
            st.session_state[AS_OF_KEY] = scenario.as_of
            st.caption(scenario.story)
        st.caption(f"Now: {st.session_state[AS_OF_KEY]:%Y-%m-%d %H:%M} UTC")
        selection = default_selection()
        st.caption(f"Model: {selection.label} ({selection.provider.value}), via the Agent Development Kit.")


def main() -> None:
    st.set_page_config(page_title=PRODUCT_NAME, layout="wide")
    st.title(PRODUCT_NAME)
    st.caption(TAGLINE)
    _sidebar()
    services()
    control, ask, approvals, about = st.tabs(TAB_NAMES)
    with control:
        render_control_room()
    with ask:
        render_ask()
    with approvals:
        render_approvals()
    with about:
        render_about()


main()
