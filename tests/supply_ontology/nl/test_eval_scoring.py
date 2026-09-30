"""Scoring rule for evaluation cases, including the rule that an unreachable model never counts as a correct refusal.

Cases are parsed from inline documents shaped like evaluation/questions.yaml.
Outcomes are hand-built summaries, so no model or database is involved.
"""
from __future__ import annotations

from datetime import date

from supply_ontology.core.eval_cases import (
    OUTCOME_ERROR,
    OutcomeSummary,
    parse_cases,
    score,
)

AS_OF = date(2026, 9, 27)
CASES = parse_cases({"cases": [
    {"persona": "planning", "question": "q1", "expect": "answer", "metrics": ["otd"], "dimensions": ["plant.plant_id"],
     "anchor": "last quarter", "filters": [{"dimension": "part.category", "value": "Bearings"}]},
    {"persona": "planning", "question": "q2", "expect": "refuse"},
]})
GOOD = OutcomeSummary("answer", ("otd",), ("plant.plant_id",), None, (date(2026, 4, 1), date(2026, 6, 30)),
                      (("part.category", "Bearings"),))


def test_matching_answer_passes() -> None:
    assert score(CASES[0], GOOD, AS_OF) == []


def test_each_detail_is_checked() -> None:
    wrong = OutcomeSummary("answer", ("fill_rate",), (), "month", None, ())
    assert score(CASES[0], wrong, AS_OF) == [
        "metrics ['fill_rate'] != ['otd']", "dimensions [] != ['plant.plant_id']",
        "time_range None != last quarter", "missing filter part.category = Bearings",
    ]


def test_unreachable_model_is_not_a_refusal() -> None:
    assert score(CASES[1], OutcomeSummary(OUTCOME_ERROR, (), (), None, None, ()), AS_OF) == ["expected refuse, got error"]
    assert score(CASES[1], OutcomeSummary("refuse", (), (), None, None, ()), AS_OF) == []
