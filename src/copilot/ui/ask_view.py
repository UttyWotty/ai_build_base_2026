"""The Ask tab: free questions to the copilot agent at the demo clock, with suggested questions to start from.

Each run shows its answer, the verification badge, and the full tool trace. Runs stay in the session history.
The agent only proposes actions; approvals happen on the Approvals tab.
"""
from __future__ import annotations

import streamlit as st

from copilot.ui.resources import history, run_agent
from copilot.ui.trace_view import render_run

SUGGESTIONS = (
    "Which alerts need attention right now, and what do you recommend?",
    "Two alerts need the same spare. Who gets it, and how is the other one covered?",
    "How reliable has supplier V10001 been lately?",
    "What was the OEE of line US1-L2 in the last 30 days?",
)


def render_ask() -> None:
    st.caption("The copilot answers only from governed tools and marks an answer verified when every number checks out.")
    cols = st.columns(len(SUGGESTIONS))
    clicked = next((q for col, q in zip(cols, SUGGESTIONS) if col.button(q, key=f"suggest-{q}")), None)
    question = st.chat_input("Ask the operations copilot") or clicked
    if question:
        with st.spinner("The copilot is working..."):
            history().append(run_agent(question))
    for index, run in enumerate(reversed(history())):
        with st.chat_message("user"):
            st.markdown(run.question)
        with st.chat_message("assistant"):
            render_run(run, key=f"ask-{index}")
