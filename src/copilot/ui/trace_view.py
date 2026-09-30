"""Renders one agent run: the answer, whether its numbers were verified, and every tool call with its result.

Both the control room and the Ask tab show runs this way, so the trace always looks the same.
The raw tool results are shown as JSON, which is exactly what the model saw.
"""
from __future__ import annotations

import streamlit as st

from copilot.services.agent_runner import AgentRun

VERIFIED_TEXT = "Verified: every number in this answer comes from a tool result."


def render_run(run: AgentRun, key: str) -> None:
    st.markdown(run.answer or "_No answer._")
    if run.verified:
        st.success(VERIFIED_TEXT)
    else:
        st.warning(f"Not verified: {', '.join(run.unexplained_numbers) or 'no answer'} not found in any tool result.")
    calls = [s for s in run.steps if s.kind == "tool_call"]
    results = [s for s in run.steps if s.kind == "tool_result"]
    with st.expander(f"Trace: {len(calls)} tool calls, {run.seconds:g} s, model {run.model}"):
        for index, call in enumerate(calls):
            st.markdown(f"**{index + 1}. {call.name}** `{call.payload}`")
            result = next((r for r in results if r.name == call.name), None)
            if result is not None:
                st.json(result.payload, expanded=False)
