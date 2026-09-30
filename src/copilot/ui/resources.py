"""Shared resources for the web app, kept in Streamlit's session state so tests can inject their own.

The services bundle loads once per session; the agent runner is a function, so tests can swap in a scripted one.
The demo clock lives here too, because every view reads it.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import streamlit as st

from copilot.services.agent_runner import AgentRun, run_copilot
from copilot.services.agent_tools import CopilotTools
from copilot.services.factory import CopilotServices, default_services
from llm_gateway.factory import default_selection

SERVICES_KEY = "copilot_services"
RUNNER_KEY = "copilot_runner"
AS_OF_KEY = "copilot_as_of"
HISTORY_KEY = "copilot_history"

AgentRunnerFn = Callable[[str, CopilotTools], AgentRun]


@st.cache_resource(show_spinner="Loading the plant, the supply network, and the bridge...")
def _cached_services() -> CopilotServices:
    return default_services()


def services() -> CopilotServices:
    if SERVICES_KEY not in st.session_state:
        st.session_state[SERVICES_KEY] = _cached_services()
    return st.session_state[SERVICES_KEY]


def tools() -> CopilotTools:
    return services().tools_at(as_of())


def as_of() -> datetime:
    return st.session_state[AS_OF_KEY]


def run_agent(question: str) -> AgentRun:
    """Run the copilot with the configured model, or the injected runner."""
    runner: AgentRunnerFn = st.session_state.get(RUNNER_KEY) or (
        lambda q, t: run_copilot(q, t, default_selection()))
    return runner(question, tools())


def history() -> list[AgentRun]:
    return st.session_state.setdefault(HISTORY_KEY, [])
