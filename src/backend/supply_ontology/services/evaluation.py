"""Runs evaluation cases through the natural-language service and scores each outcome.

Each response is reduced to an OutcomeSummary so the pure scoring rule can compare it with the case.
The report records per-case results, timings, and overall accuracy for one model.
"""
from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass

from supply_ontology.core.eval_cases import (
    EXPECT_ANSWER,
    EXPECT_CLARIFY,
    EXPECT_REFUSE,
    OUTCOME_ERROR,
    EvalCase,
    OutcomeSummary,
    score,
)
from supply_ontology.services.nl_models import (
    MODEL_UNAVAILABLE,
    Answer,
    Clarification,
    NLResponse,
)
from supply_ontology.services.nl_service import NLService


@dataclass(frozen=True)
class CaseResult:
    case: EvalCase
    outcome: OutcomeSummary
    detail: str
    problems: tuple[str, ...]
    seconds: float
    model_calls: int

    @property
    def passed(self) -> bool:
        return not self.problems


def summarize(response: NLResponse) -> OutcomeSummary:
    """Reduce a response to its comparable parts."""
    if isinstance(response, Answer):
        spec = response.result.spec
        return OutcomeSummary(
            action=EXPECT_ANSWER, metrics=spec.metrics, dimensions=tuple(d.name for d in spec.dimensions),
            time_grain=None if spec.time_grain is None else spec.time_grain.value,
            time_range=None if spec.time_range is None else (spec.time_range.start, spec.time_range.end),
            filters=tuple((f.dimension.name, str(v)) for f in spec.filters for v in f.values),
        )
    if isinstance(response, Clarification):
        return OutcomeSummary(EXPECT_CLARIFY, (), (), None, None, ())
    action = OUTCOME_ERROR if response.kind == MODEL_UNAVAILABLE else EXPECT_REFUSE
    return OutcomeSummary(action, (), (), None, None, ())


def run_cases(service: NLService, cases: Sequence[EvalCase]) -> list[CaseResult]:
    """Ask every case and score it."""
    results = []
    for case in cases:
        started = time.perf_counter()
        response = service.ask(case.question, case.persona)
        elapsed = time.perf_counter() - started
        outcome = summarize(response)
        detail = response.reason if hasattr(response, "reason") else getattr(response, "prompt", "")
        results.append(CaseResult(case, outcome, detail, tuple(score(case, outcome, service.query_service.as_of)),
                                  elapsed, len(response.model_replies)))
    return results
