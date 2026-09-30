"""Runs the consistency demo: the same question per persona through naive text-to-SQL, then through the governed layer.

Naive runs show the model the raw source tables and execute whatever read-only SQL it writes; governed runs use NLService.
Both share one language model client, so the only difference between the two halves is the governed layer itself.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date

import pandas as pd

from supply_ontology.core.demo_script import (
    BOUNDARY_QUESTION,
    SAME_QUESTION,
    DemoQuestion,
)
from supply_ontology.core.naive_sql import (
    NO_VALUE_PROBLEM,
    NaiveSqlError,
    build_naive_messages,
    build_naive_retry_message,
    extract_select,
)
from supply_ontology.core.team_recipes import TeamRecipe
from supply_ontology.data_pipeline.llm_client import LLMClient, LLMError
from supply_ontology.data_pipeline.raw_source_database import (
    RawQueryError,
    RawSourceDatabase,
)
from supply_ontology.services.demo_models import (
    OUTCOME_ANSWER,
    OUTCOME_CLARIFICATION,
    OUTCOME_UNANSWERABLE,
    DemoReport,
    GovernedRun,
    NaiveRun,
    answer_value,
)
from supply_ontology.services.nl_models import Answer, Clarification
from supply_ontology.services.nl_service import NLService
from supply_ontology.services.recipe_comparison import compare_recipes

# The naive path gets the same single retry the governed path gets, so the comparison is fair.
MAX_NAIVE_ATTEMPTS = 2


class ConsistencyDemo:
    """The problem, the fix, and the boundary, run end to end."""

    def __init__(
        self, nl_service: NLService, raw_database: RawSourceDatabase, llm_client: LLMClient | None = None,
        recipes: Sequence[TeamRecipe] = (),
    ) -> None:
        """`llm_client` defaults to the NL service's own client; with no `recipes` the report has no recipe comparison."""
        self.nl_service = nl_service
        self.raw_database = raw_database
        self.llm_client = llm_client or nl_service.llm_client
        self.recipes = tuple(recipes)

    def run(self) -> DemoReport:
        """Ask every demo question both ways."""
        as_of = self.nl_service.query_service.as_of
        return DemoReport(
            as_of=as_of,
            naive=tuple(self.run_naive(q, as_of) for q in SAME_QUESTION),
            governed=tuple(self.run_governed(q) for q in SAME_QUESTION),
            boundary=self.run_governed(BOUNDARY_QUESTION),
            recipes=compare_recipes(self.recipes, self.raw_database, self.nl_service.query_service) if self.recipes else None,
        )

    def run_naive(self, question: DemoQuestion, as_of: date) -> NaiveRun:
        """One question through naive text-to-SQL, with one retry on a failed or empty query; failures are recorded."""
        persona = self.nl_service.catalog.vocabulary.personas[question.persona]
        messages = build_naive_messages(self.raw_database.tables, as_of, persona, question.question)
        reply = sql = frame = problem = None
        for attempt in range(1, MAX_NAIVE_ATTEMPTS + 1):
            try:
                reply = self.llm_client.complete(messages)
            except LLMError as error:
                return NaiveRun(question.persona, question.question, reply, sql, None, None, str(error), attempt)
            sql, frame, problem = self._try_sql(reply)
            if problem is None:
                return NaiveRun(question.persona, question.question, reply, sql, frame, answer_value(frame), None, attempt)
            messages = [*messages, {"role": "assistant", "content": reply}, build_naive_retry_message(problem)]
        return NaiveRun(question.persona, question.question, reply, sql, frame, None, problem, MAX_NAIVE_ATTEMPTS)

    def _try_sql(self, reply: str) -> tuple[str | None, pd.DataFrame | None, str | None]:
        """The statement, its result, and the problem to send back (None when it produced a value)."""
        try:
            sql = extract_select(reply)
        except NaiveSqlError as error:
            return None, None, str(error)
        try:
            frame = self.raw_database.run_select(sql)
        except RawQueryError as error:
            return sql, None, str(error)
        return sql, frame, (NO_VALUE_PROBLEM if answer_value(frame) is None else None)

    def run_governed(self, question: DemoQuestion) -> GovernedRun:
        """One question through the governed layer."""
        response = self.nl_service.ask(question.question, question.persona)
        if isinstance(response, Answer):
            result = response.result
            return GovernedRun(
                question.persona, question.question, OUTCOME_ANSWER, result.spec.metrics, response.resolved_by,
                single_metric_value(result.frame, result.spec.metrics), result.compiled.fingerprint, result.compiled.sql, None,
            )
        if isinstance(response, Clarification):
            return GovernedRun(question.persona, question.question, OUTCOME_CLARIFICATION, response.options,
                               None, None, None, None, response.prompt)
        return GovernedRun(question.persona, question.question, OUTCOME_UNANSWERABLE, (), None, None, None, None, response.reason)


def single_metric_value(frame: pd.DataFrame, metrics: tuple[str, ...]) -> float | None:
    """The value of a one-metric, one-row governed result, else None."""
    if len(metrics) != 1 or len(frame) != 1:
        return None
    value = frame[metrics[0]].iloc[0]
    return None if pd.isna(value) else float(value)
