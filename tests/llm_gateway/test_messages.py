"""Tests for converting OpenAI-style chat messages into a Gemini system instruction and turns.

System messages join into one instruction and assistant turns take Gemini's model role.
Unknown roles, missing text, and requests without turns are rejected.
"""
from __future__ import annotations

import pytest

from llm_gateway.messages import GeminiTurn, MessageFormatError, to_gemini_request


def test_system_messages_join_and_roles_map() -> None:
    request = to_gemini_request([
        {"role": "system", "content": "Be exact."}, {"role": "system", "content": "Use tools."},
        {"role": "user", "content": "Q1"}, {"role": "assistant", "content": "A1"}, {"role": "user", "content": "Q2"},
    ])
    assert request.system_instruction == "Be exact.\n\nUse tools."
    assert request.turns == (GeminiTurn("user", "Q1"), GeminiTurn("model", "A1"), GeminiTurn("user", "Q2"))


def test_a_request_without_system_messages_has_an_empty_instruction() -> None:
    assert to_gemini_request([{"role": "user", "content": "Q"}]).system_instruction == ""


@pytest.mark.parametrize("messages", [
    [{"role": "tool", "content": "x"}],
    [{"role": "user"}],
    [{"role": "system", "content": "only instructions"}],
])
def test_malformed_requests_are_rejected(messages: list[dict[str, str]]) -> None:
    with pytest.raises(MessageFormatError):
        to_gemini_request(messages)
