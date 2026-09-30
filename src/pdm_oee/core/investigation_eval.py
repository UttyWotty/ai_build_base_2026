"""Evaluation cases for the investigation layer and the rule that scores an outcome against one.

A case names a question, the tools at least one of which must be used, the terms the answer must mention, and whether
every number must be verified. Scoring is pure, so it is tested without a model.
"""
from __future__ import annotations

from dataclasses import dataclass

from pdm_oee.core.errors import SemanticParseError
from pdm_oee.core.field_readers import (
    as_list,
    as_mapping,
    optional_bool,
    optional_str_list,
    require_str,
)


@dataclass(frozen=True)
class InvestigationCase:
    question: str
    any_of_tools: tuple[str, ...]
    must_mention: tuple[str, ...]
    must_verify: bool


@dataclass(frozen=True)
class InvestigationOutcome:
    tools_used: tuple[str, ...]
    answer: str | None
    verified: bool


def parse_cases(raw: object) -> list[InvestigationCase]:
    root = as_mapping(raw, "investigation")
    cases = []
    for index, item in enumerate(as_list(root.get("cases"), "cases")):
        path = f"cases[{index}]"
        fields = as_mapping(item, path)
        cases.append(InvestigationCase(require_str(fields, "question", path), optional_str_list(fields, "any_of_tools", path),
                                       optional_str_list(fields, "must_mention", path), optional_bool(fields, "must_verify", path, True)))
    if not cases:
        raise SemanticParseError("cases", "at least one case is required")
    return cases


def score(case: InvestigationCase, outcome: InvestigationOutcome) -> list[str]:
    """Problems with the outcome; empty means the case passed."""
    if outcome.answer is None:
        return ["no answer"]
    problems = []
    if case.any_of_tools and not set(case.any_of_tools) & set(outcome.tools_used):
        problems.append(f"used {list(outcome.tools_used)}, expected one of {list(case.any_of_tools)}")
    lowered = outcome.answer.lower()
    problems += [f"answer does not mention '{term}'" for term in case.must_mention if term.lower() not in lowered]
    if case.must_verify and not outcome.verified:
        problems.append("answer has numbers no tool returned")
    return problems
