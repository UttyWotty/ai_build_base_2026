"""Parses a language model reply into one of three decisions: run a query spec, ask a clarifying question, or decline.

Replies may wrap JSON in thinking tags or code fences; only the first complete JSON object is used.
Anything else raises ModelOutputError with a message that can be sent back to the model.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from supply_ontology.core.errors import SemanticLayerError

THINK_PATTERN = re.compile(r"<think>.*?</think>", re.DOTALL)
ACTION_QUERY, ACTION_CLARIFY, ACTION_UNSUPPORTED = "query", "clarify", "unsupported"


class ModelOutputError(SemanticLayerError):
    """The model's reply is not a valid decision."""


@dataclass(frozen=True)
class QueryDecision:
    spec: dict[str, object]


@dataclass(frozen=True)
class ClarifyDecision:
    question: str
    options: tuple[str, ...]


@dataclass(frozen=True)
class UnsupportedDecision:
    reason: str


ModelDecision = QueryDecision | ClarifyDecision | UnsupportedDecision


def extract_json_object(text: str) -> dict[str, object]:
    """Return the first JSON object in the text, ignoring thinking blocks, fences, and prose around it."""
    cleaned = THINK_PATTERN.sub("", text)
    decoder = json.JSONDecoder()
    position = cleaned.find("{")
    while position != -1:
        try:
            parsed, _ = decoder.raw_decode(cleaned, position)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            return parsed
        position = cleaned.find("{", position + 1)
    raise ModelOutputError("Reply must contain one JSON object.")


def parse_decision(text: str) -> ModelDecision:
    """Turn a model reply into a decision."""
    payload = extract_json_object(text)
    action = payload.get("action")
    if action == ACTION_QUERY and isinstance(payload.get("spec"), dict):
        return QueryDecision(spec=payload["spec"])
    if action == ACTION_CLARIFY and isinstance(payload.get("question"), str):
        options = payload.get("options", [])
        return ClarifyDecision(payload["question"], tuple(str(o) for o in options) if isinstance(options, list) else ())
    if action == ACTION_UNSUPPORTED:
        return UnsupportedDecision(str(payload.get("reason", "")))
    raise ModelOutputError('JSON must have "action" of "query" (with "spec"), "clarify" (with "question"), or "unsupported".')
