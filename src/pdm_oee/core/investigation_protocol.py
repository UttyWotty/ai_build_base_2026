"""The conversation protocol between the investigation service and the local model.

The system message lists the tools, their parameters, the known ids, and the data period; each reply must be one JSON
object, either a tool call or a final answer. Replies may wrap the JSON in thinking tags or code fences, and a call whose
arguments sit at the top level instead of inside "arguments" is read the same way.
"""
from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from pdm_oee.core.tool_catalog import TOOLS

ChatMessage = dict[str, str]
THINK_PATTERN = re.compile(r"<think>.*?</think>", re.DOTALL)
ACTION_CALL, ACTION_ANSWER = "call", "answer"
CALL_KEYS = frozenset({"action", "tool", "arguments"})
MAX_LISTED = 30

RULES = """You investigate a manufacturing plant's equipment effectiveness and maintenance using governed tools.
Reply with exactly one JSON object and nothing else, either
{"action": "call", "tool": "<tool name>", "arguments": {...}}
or, when you know the answer,
{"action": "answer", "text": "<a short answer for a plant manager>"}.
Rules:
- Use only the tools and ids listed below; never invent ids, sensors, or losses.
- Every number in your answer must be copied from a tool result (percentages as shown, e.g. 82.3%). Do not calculate new numbers.
- Periods are half-open: start is the first day, end is the day after the last day.
- Call tools one at a time; you will see each result before your next reply."""


class ReplyError(Exception):
    """The model's reply is not a valid tool call or answer."""


@dataclass(frozen=True)
class ToolCall:
    tool: str
    arguments: dict


@dataclass(frozen=True)
class FinalAnswer:
    text: str


def system_message(vocabularies: Mapping[str, Sequence[str]], first_day: date, last_day: date) -> ChatMessage:
    tools = "\n".join(f"- {t.name}({', '.join(p.name for p in t.params)}): {t.description}" for t in TOOLS)
    known = "\n".join(f"- {name}: {', '.join(list(values)[:MAX_LISTED])}" for name, values in vocabularies.items())
    body = f"{RULES}\n\nData covers {first_day} to {last_day}.\n\nTools:\n{tools}\n\nKnown values:\n{known}"
    return {"role": "system", "content": body}


def user_message(question: str) -> ChatMessage:
    return {"role": "user", "content": question}


def tool_result_message(tool: str, result: object) -> ChatMessage:
    return {"role": "user", "content": f"Result of {tool}:\n{json.dumps(result, default=str)}"}


def problem_message(problems: Sequence[str]) -> ChatMessage:
    return {"role": "user", "content": "That reply could not be used:\n- " + "\n- ".join(problems) + "\nReply with one corrected JSON object."}


def parse_reply(text: str) -> ToolCall | FinalAnswer:
    """The first JSON object in the reply, as a tool call or a final answer."""
    cleaned = THINK_PATTERN.sub("", text)
    decoder, position = json.JSONDecoder(), cleaned.find("{")
    while position != -1:
        try:
            payload, _ = decoder.raw_decode(cleaned, position)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            return _decision(payload)
        position = cleaned.find("{", position + 1)
    raise ReplyError("Reply must contain one JSON object.")


def _decision(payload: dict) -> ToolCall | FinalAnswer:
    action = payload.get("action")
    if action == ACTION_CALL and isinstance(payload.get("tool"), str) and isinstance(payload.get("arguments", {}), dict):
        # A call written without an "arguments" object carries its arguments at the top level; take them from there.
        arguments = payload["arguments"] if "arguments" in payload else {k: v for k, v in payload.items() if k not in CALL_KEYS}
        return ToolCall(payload["tool"], dict(arguments))
    if action == ACTION_ANSWER and isinstance(payload.get("text"), str) and payload["text"].strip():
        return FinalAnswer(payload["text"].strip())
    raise ReplyError('JSON must be {"action": "call", "tool": ..., "arguments": {...}} or {"action": "answer", "text": ...}.')
