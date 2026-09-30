"""Checks the agent's final answer: every number it states must appear in some tool result.

It reuses the plant package's number check, after removing SQL fingerprints (hexadecimal ids, not numbers) and
thousands separators, so "4,486.43" reads as one number.
The result lists the numbers no tool explains; an empty list means the answer is verified.
"""
from __future__ import annotations

import re
from collections.abc import Iterable

from pdm_oee.core.number_check import unverified_numbers

FINGERPRINT_PATTERN = re.compile(r"\b(?=[0-9a-f]*[a-f])[0-9a-f]{8,}\b")
THOUSANDS_PATTERN = re.compile(r"(?<=\d),(?=\d{3}\b)")


def unexplained_numbers(answer: str, question: str, tool_results: Iterable[object]) -> list[str]:
    """Numbers in the answer that no tool result contains."""
    cleaned = THOUSANDS_PATTERN.sub("", FINGERPRINT_PATTERN.sub(" ", answer))
    return unverified_numbers(cleaned, question, tool_results)
