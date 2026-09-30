"""Result types of the consistency demo: team recipe runs, naive text-to-SQL runs, governed runs, and the report joining them.

The report derives its verdicts (do the naive answers agree, do the governed ones share one SQL fingerprint) from the runs.
The CLI and the UI render these types; they hold no I/O, and answer_value reads the value out of a result frame.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from supply_ontology.core.demo_script import (
    BOUNDARY_METRIC,
    SHARED_METRIC,
    value_spread,
    values_agree,
)
from supply_ontology.core.naive_sql import ANSWER_COLUMN
from supply_ontology.core.query_spec import TimeRange
from supply_ontology.core.team_recipes import TeamRecipe

OUTCOME_ANSWER = "answer"
OUTCOME_CLARIFICATION = "clarification"
OUTCOME_UNANSWERABLE = "unanswerable"


@dataclass(frozen=True)
class NaiveRun:
    """One persona's question through naive text-to-SQL on the raw sources."""

    persona: str
    question: str
    reply: str | None
    sql: str | None
    frame: pd.DataFrame | None
    value: float | None
    error: str | None
    attempts: int


@dataclass(frozen=True)
class GovernedRun:
    """One persona's question through the governed layer."""

    persona: str
    question: str
    outcome: str
    metrics: tuple[str, ...]
    resolved_by: str | None
    value: float | None
    fingerprint: str | None
    sql: str | None
    detail: str | None


@dataclass(frozen=True)
class RecipeRun:
    """One team recipe's answer for the demo period."""

    recipe: TeamRecipe
    value: float | None
    error: str | None


@dataclass(frozen=True)
class RecipeComparison:
    """Every team recipe next to the governed answer for the same period."""

    period: TimeRange
    runs: tuple[RecipeRun, ...]
    governed_metric: str
    governed_value: float | None
    governed_fingerprint: str

    @property
    def recipes_agree(self) -> bool:
        return values_agree([run.value for run in self.runs])

    @property
    def recipes_spread(self) -> float | None:
        return value_spread([run.value for run in self.runs])


@dataclass(frozen=True)
class DemoReport:
    """The three parts of the demo: the problem, the fix, and the boundary."""

    as_of: date
    naive: tuple[NaiveRun, ...]
    governed: tuple[GovernedRun, ...]
    boundary: GovernedRun
    recipes: RecipeComparison | None

    @property
    def naive_agree(self) -> bool:
        return values_agree([run.value for run in self.naive])

    @property
    def naive_spread(self) -> float | None:
        return value_spread([run.value for run in self.naive])

    @property
    def governed_fingerprints(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(run.fingerprint for run in self.governed if run.fingerprint))

    @property
    def governed_consistent(self) -> bool:
        """Every phrasing answered with the shared metric through one identical SQL statement."""
        answered = all(run.metrics == (SHARED_METRIC,) for run in self.governed)
        return answered and len(self.governed_fingerprints) == 1 and values_agree([r.value for r in self.governed])

    @property
    def boundary_distinct(self) -> bool:
        """The supplier question resolved to its own metric, not to the shared one."""
        return self.boundary.metrics == (BOUNDARY_METRIC,)


def answer_value(frame: pd.DataFrame) -> float | None:
    """The naive answer: the `answer` column of the first row, else its first numeric column."""
    if frame.empty:
        return None
    numeric = frame.select_dtypes("number").columns
    column = ANSWER_COLUMN if ANSWER_COLUMN in numeric else (numeric[0] if len(numeric) else None)
    value = None if column is None else frame[column].iloc[0]
    return None if value is None or pd.isna(value) else float(value)
