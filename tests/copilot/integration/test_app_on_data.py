"""Runs the real web app headless on the generated data, with a scripted agent runner, at the bearing scenario.

It checks the headline numbers and the conflict banner, and that drafting a plan shows a verified run.
Skipped when the data has not been generated.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from copilot.services.agent_runner import AgentRun, AgentStep
from copilot.services.settings import BRIDGE_DATA_DIR
from copilot.ui import resources

ROOT = Path(__file__).resolve().parents[3]
APP_PATH = ROOT / "src" / "backend" / "copilot" / "ui" / "app.py"
REPLAY = ROOT / "data" / "pdm" / "alerts" / "replay.json"
TIMEOUT_SECONDS = 300

pytestmark = pytest.mark.skipif(not (ROOT / BRIDGE_DATA_DIR).exists() or not REPLAY.exists(),
                                reason="needs `make data` and `make models`")


def scripted_runner(question: str, tools) -> AgentRun:
    result = tools.list_open_alerts()
    steps = (AgentStep("tool_call", "list_open_alerts", {}), AgentStep("tool_result", "list_open_alerts", result),
             AgentStep("text", "copilot", f"{result['count']} alerts are open."))
    return AgentRun(question, tools.as_of, "scripted", steps, f"{result['count']} alerts are open.", (), 0.1)


def test_bearing_scenario_headline_conflict_and_plan() -> None:
    page = AppTest.from_file(str(APP_PATH), default_timeout=TIMEOUT_SECONDS)
    page.session_state[resources.RUNNER_KEY] = scripted_runner
    page.run()
    assert not page.exception
    metrics = {m.label: m.value for m in page.metric}
    assert metrics["Open alerts"] == "3" and metrics["Alerts in a spare conflict"] == "2"
    assert metrics["Everline Metalworks GmbH on time"] == "66.1%"
    assert page.warning[0].value.startswith("2 alerts need Spindle bearing set (SP-1001) at US1")
    next(b for b in page.button if b.key.startswith("plan-")).click().run()
    assert not page.exception and any("Verified" in s.value for s in page.success)
