"""The investigation loop with a scripted model on the small plant: tool use, recovery from bad calls, number checks.

Each scenario scripts the model's replies and checks both the outcome and what the model was told.
The OEE value quoted in the answers is read from the tool so the tests do not depend on the seed.
"""
from __future__ import annotations

import json
from datetime import date

from pdm_oee.data_pipeline.llm_client import LLMError
from pdm_oee.services.investigation_service import (
    ANSWER_NOW,
    ANSWERED,
    MODEL_UNAVAILABLE,
    InvestigationService,
)
from pdm_oee.services.investigation_tools import ToolBox
from tests.pdm_oee.investigation.scripted_model import ScriptedModel

CALL = {"action": "call", "tool": "oee_summary",
        "arguments": {"scope_type": "line", "scope_id": "US1-L1", "start": "2025-10-01", "end": "2025-12-01"}}


def call(overrides: dict | None = None) -> str:
    return json.dumps({**CALL, "arguments": {**CALL["arguments"], **(overrides or {})}})


def answer(text: str) -> str:
    return json.dumps({"action": "answer", "text": text})


def quoted_oee(toolbox: ToolBox) -> str:
    result = toolbox.run("oee_summary", {"scope_type": "line", "scope_id": "US1-L1", "start": date(2025, 10, 1), "end": date(2025, 12, 1)})
    return f"{result['oee'] * 100:.1f}%"


def test_tool_then_verified_answer(toolbox: ToolBox) -> None:
    oee = quoted_oee(toolbox)
    model = ScriptedModel([call(), answer(f"OEE on US1-L1 was {oee}.")])
    result = InvestigationService(toolbox, model).ask("What was OEE on US1-L1?")
    assert result.status == ANSWERED and result.verified and result.tools_used == ("oee_summary",)
    assert "Result of oee_summary" in model.calls[1][-1]["content"]


def test_bad_call_is_explained_and_corrected(toolbox: ToolBox) -> None:
    oee = quoted_oee(toolbox)
    model = ScriptedModel([call({"scope_id": "US1-L9"}), "not json", call(), answer(f"It was {oee}.")])
    result = InvestigationService(toolbox, model).ask("OEE?")
    assert result.verified and len(result.problems) == 2
    assert "is not a known line" in model.calls[1][-1]["content"]


def test_invented_number_gets_one_retry_then_is_flagged(toolbox: ToolBox) -> None:
    model = ScriptedModel([call(), answer("OEE was 97.5%."), answer("OEE was 97.5%, honestly.")])
    result = InvestigationService(toolbox, model).ask("OEE?")
    assert result.status == ANSWERED and not result.verified and result.unverified == ("97.5",)
    assert "not returned by any tool" in model.calls[2][-1]["content"]


def test_tool_error_goes_back_to_the_model(toolbox: ToolBox) -> None:
    trend = {"action": "call", "tool": "sensor_trend", "arguments": {"asset_id": "US1-L1-04", "sensor": "spindle_vibration",
                                                                     "start": "2025-10-01", "end": "2025-10-08"}}
    model = ScriptedModel([json.dumps(trend), answer("The conveyor has no spindle sensor.")])
    result = InvestigationService(toolbox, model).ask("Spindle vibration on US1-L1-04?")
    assert result.verified and "its sensors are" in model.calls[1][-1]["content"]


def test_call_budget_and_unreachable_model(toolbox: ToolBox) -> None:
    model = ScriptedModel([call(), call(), answer("Done.")])
    result = InvestigationService(toolbox, model, max_tool_calls=1).ask("OEE?")
    assert result.status == ANSWERED and model.calls[2][-1]["content"] == ANSWER_NOW
    down = InvestigationService(toolbox, ScriptedModel([LLMError("connection refused")])).ask("OEE?")
    assert down.status == MODEL_UNAVAILABLE and down.answer is None
