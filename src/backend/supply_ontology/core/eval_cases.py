"""Evaluation cases for the natural-language layer and the rule that scores an outcome against one.

A case names a persona, a question, and the expected outcome; optional details (dimensions, grain, anchor, filters) must match when given.
Scoring is pure: it compares a small summary of the service response, so it can be tested without a model.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from supply_ontology.core.calendar_anchors import calendar_anchors
from supply_ontology.core.field_readers import (
    as_list,
    as_mapping,
    optional_str,
    optional_str_list,
    reject_unknown_keys,
    require_str,
    require_str_list,
)

EXPECT_ANSWER, EXPECT_CLARIFY, EXPECT_REFUSE = "answer", "clarify", "refuse"
# Outcome when the model could not be reached; it never matches an expectation.
OUTCOME_ERROR = "error"
CASE_KEYS = frozenset({"persona", "question", "expect", "metrics", "dimensions", "time_grain", "anchor", "filters"})


@dataclass(frozen=True)
class EvalCase:
    persona: str
    question: str
    expect: str
    metrics: tuple[str, ...]
    dimensions: tuple[str, ...] | None
    time_grain: str | None
    anchor: str | None
    filters: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class OutcomeSummary:
    """The comparable parts of a service response."""

    action: str
    metrics: tuple[str, ...]
    dimensions: tuple[str, ...]
    time_grain: str | None
    time_range: tuple[date, date] | None
    filters: tuple[tuple[str, str], ...]


def parse_cases(raw: object) -> list[EvalCase]:
    """Parse the evaluation document."""
    cases = []
    root = as_mapping(raw, "evaluation")
    reject_unknown_keys(root, frozenset({"cases"}), "evaluation")
    for index, item in enumerate(as_list(root.get("cases"), "evaluation.cases")):
        path = f"cases[{index}]"
        fields = as_mapping(item, path)
        reject_unknown_keys(fields, CASE_KEYS, path)
        filters = tuple(
            (require_str(as_mapping(f, path), "dimension", path), str(as_mapping(f, path)["value"]))
            for f in as_list(fields.get("filters", []), f"{path}.filters")
        )
        cases.append(EvalCase(
            persona=require_str(fields, "persona", path), question=require_str(fields, "question", path),
            expect=require_str(fields, "expect", path), metrics=optional_str_list(fields, "metrics", path),
            dimensions=require_str_list(fields, "dimensions", path) if "dimensions" in fields else None,
            time_grain=optional_str(fields, "time_grain", path), anchor=optional_str(fields, "anchor", path), filters=filters,
        ))
    return cases


def score(case: EvalCase, outcome: OutcomeSummary, as_of: date) -> list[str]:
    """Mismatches between the expectation and the outcome; empty means the case passed."""
    if outcome.action != case.expect:
        return [f"expected {case.expect}, got {outcome.action}"]
    if case.expect != EXPECT_ANSWER:
        return []
    problems = []
    if outcome.metrics != case.metrics:
        problems.append(f"metrics {list(outcome.metrics)} != {list(case.metrics)}")
    if case.dimensions is not None and set(outcome.dimensions) != set(case.dimensions):
        problems.append(f"dimensions {list(outcome.dimensions)} != {list(case.dimensions)}")
    if case.time_grain is not None and outcome.time_grain != case.time_grain:
        problems.append(f"time_grain {outcome.time_grain} != {case.time_grain}")
    if case.anchor is not None:
        anchor = calendar_anchors(as_of)[case.anchor]
        if outcome.time_range != (anchor.start, anchor.end):
            problems.append(f"time_range {outcome.time_range} != {case.anchor}")
    for expected in case.filters:
        if expected not in outcome.filters:
            problems.append(f"missing filter {expected[0]} = {expected[1]}")
    return problems
