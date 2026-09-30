"""Ask: a question for the local model, answered through governed tools, with the numbers' verification shown.

The model is contacted only when a question is submitted. Every tool call and its result can be inspected under the answer.
An answer whose numbers could not all be traced to a tool is shown with a warning.
"""
from __future__ import annotations

import streamlit as st

from pdm_oee.ui.resources import investigation

RESULT_KEY = "last_investigation"
EXAMPLE = "Why did quality drop on line DE1-L2 in summer 2026?"


def render_ask() -> None:
    with st.form("ask"):
        question = st.text_input("Question", placeholder=EXAMPLE)
        if st.form_submit_button("Investigate") and question.strip():
            with st.spinner("Investigating with governed tools"):
                st.session_state[RESULT_KEY] = investigation().ask(question.strip())
    result = st.session_state.get(RESULT_KEY)
    if result is None:
        return
    st.markdown(f"**{result.question}**")
    if result.answer is None:
        st.warning(f"No answer ({result.status}). {' '.join(result.problems)}")
        return
    st.write(result.answer)
    if result.verified:
        st.success("Every number in this answer comes from a tool result.")
    else:
        st.warning(f"These numbers could not be traced to a tool result: {', '.join(result.unverified)}")
    for step in result.steps:
        with st.expander(f"{step.tool}({', '.join(f'{k}={v}' for k, v in step.arguments.items())})"):
            st.json(step.result)
