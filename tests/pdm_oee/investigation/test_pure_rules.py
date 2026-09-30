"""Pure rules of the investigation layer: tool call validation, reply parsing, the number check, and case scoring.

Every rule is checked with hand-written inputs; each problem message must say what to fix.
No data or model is involved.
"""
from __future__ import annotations

from datetime import date

import pytest

from pdm_oee.core.investigation_eval import (
    InvestigationCase,
    InvestigationOutcome,
    score,
)
from pdm_oee.core.investigation_protocol import (
    FinalAnswer,
    ReplyError,
    ToolCall,
    parse_reply,
)
from pdm_oee.core.number_check import answer_numbers, unverified_numbers
from pdm_oee.core.tool_catalog import validate_call

VOCABULARIES = {"scope_type": ["plant", "site", "line", "asset"], "plant": ["plant"], "line": ["US1-L1"],
                "asset": ["US1-L1-04"], "site": ["US1"], "loss": ["small_stops"], "group": ["asset", "line"], "grain": ["week"]}


def test_valid_call_is_cleaned() -> None:
    clean, problems = validate_call("oee_summary", {"scope_type": "line", "scope_id": "US1-L1", "start": "2026-06-01", "end": "2026-07-01"}, VOCABULARIES)
    assert problems == [] and clean["start"] == date(2026, 6, 1)


@pytest.mark.parametrize("tool, arguments, message", [
    ("oee_magic", {}, "Unknown tool 'oee_magic'"),
    ("oee_summary", {"scope_type": "line", "start": "2026-06-01", "end": "2026-07-01"}, "Missing argument 'scope_id'"),
    ("oee_summary", {"scope_type": "line", "scope_id": "US1-L9", "start": "2026-06-01", "end": "2026-07-01"}, "'US1-L9' is not a known line"),
    ("oee_summary", {"scope_type": "asset", "scope_id": "US1-L1", "start": "2026-06-01", "end": "2026-07-01"}, "is not a known asset"),
    ("oee_summary", {"scope_type": "plant", "scope_id": "plant", "start": "June", "end": "2026-07-01"}, "must be a date"),
    ("oee_summary", {"scope_type": "plant", "scope_id": "plant", "start": "2026-07-01", "end": "2026-06-01"}, "'end' must be after"),
    ("top_loss_contributors", {"loss": "small_stops", "group": "asset", "start": "2026-06-01", "end": "2026-07-01", "limit": 99}, "integer from 1 to 20"),
    ("failures", {"scope_type": "plant", "scope_id": "plant", "start": "2026-06-01", "end": "2026-07-01", "mood": "x"}, "Unknown argument 'mood'"),
])
def test_invalid_calls_explain_themselves(tool: str, arguments: dict, message: str) -> None:
    _, problems = validate_call(tool, arguments, VOCABULARIES)
    assert any(message in p for p in problems), problems


def test_replies_parse_through_thinking_and_fences() -> None:
    assert parse_reply('<think>hm</think>```json\n{"action": "call", "tool": "alerts", "arguments": {"a": 1}}\n```') == ToolCall("alerts", {"a": 1})
    assert parse_reply('Sure. {"action": "answer", "text": "OEE was 82.3%."}') == FinalAnswer("OEE was 82.3%.")
    flat = parse_reply('{"action": "call", "tool": "alerts", "scope_type": "plant", "scope_id": "plant"}')
    assert flat == ToolCall("alerts", {"scope_type": "plant", "scope_id": "plant"})
    with pytest.raises(ReplyError):
        parse_reply('{"action": "dance"}')
    with pytest.raises(ReplyError):
        parse_reply("no json here")


def test_number_check_accepts_quoted_values_and_ignores_ids_and_dates() -> None:
    results = [{"oee": 0.8227, "hours": 274.0}, [{"count": 9}]]
    answer = "US1-L1-04 lost 274 h; OEE was 82.3% (82.27%) from 2026-06-01, with 9 failures in week 2026-W23."
    assert answer_numbers("Asset 10204 on 2026-06-01", "") == []
    assert answer_numbers("created 2026-08-25 10:37:00, closed at 02:00", "") == []
    assert unverified_numbers(answer, "", results) == []
    assert unverified_numbers("OEE was 85% and 3 of 5 assets", "top 5 assets", results) == ["85", "3"]


def test_case_scoring() -> None:
    case = InvestigationCase("q", ("top_loss_contributors",), ("US1-L1-04",), True)
    assert score(case, InvestigationOutcome(("top_loss_contributors",), "US1-L1-04 lost 274 h", True)) == []
    problems = score(case, InvestigationOutcome(("oee_summary",), "It was the conveyor", False))
    assert len(problems) == 3
    assert score(case, InvestigationOutcome((), None, False)) == ["no answer"]
