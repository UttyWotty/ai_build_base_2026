"""Checks that every number in an answer was returned by a tool, so the model cannot state a figure it made up.

Dates, times of day, ids, and numbers already in the question are ignored. A number matches a tool value when it equals the value,
or the value as a percentage, after rounding to the answer's own number of decimals (to the nearest unit at most).
"""
from __future__ import annotations

import re
from collections.abc import Iterable

DATE_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{4}-W\d{2}\b|\b\d{4}-\d{2}\b|\b\d{1,2}:\d{2}(?::\d{2})?\b")
ID_PATTERN = re.compile(r"\b[A-Z]{2,}\d*-[A-Z0-9-]+\b|\b\d{5,}\b")
NUMBER_PATTERN = re.compile(r"(?<![\w.])-?\d+(?:[.,]\d+)?")
PERCENT = 100


def answer_numbers(text: str, question: str) -> list[str]:
    """Numbers stated in the answer that need a source (not dates, ids, or numbers from the question)."""
    stripped = ID_PATTERN.sub(" ", DATE_PATTERN.sub(" ", text))
    asked = set(NUMBER_PATTERN.findall(ID_PATTERN.sub(" ", DATE_PATTERN.sub(" ", question))))
    return [n.replace(",", ".") for n in NUMBER_PATTERN.findall(stripped) if n not in asked]


def tool_values(results: Iterable[object]) -> list[float]:
    """Every number anywhere inside the tool results."""
    values: list[float] = []

    def walk(item: object) -> None:
        if isinstance(item, bool):
            return
        if isinstance(item, (int, float)):
            values.append(float(item))
        elif isinstance(item, dict):
            for inner in item.values():
                walk(inner)
        elif isinstance(item, (list, tuple)):
            for inner in item:
                walk(inner)

    for result in results:
        walk(result)
    return values


def unverified_numbers(answer: str, question: str, results: Iterable[object]) -> list[str]:
    """Numbers in the answer that no tool value explains."""
    values = tool_values(results)
    missing = []
    for text in answer_numbers(answer, question):
        decimals = len(text.split(".")[1]) if "." in text else 0
        number = float(text)
        if not any(round(v, decimals) == number or round(v * PERCENT, decimals) == number for v in values):
            missing.append(text)
    return missing
