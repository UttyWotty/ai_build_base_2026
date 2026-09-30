"""The consistency demo's script: which persona phrasings are asked, what each part must show, and the agreement rule.

Three teams ask for customer on-time delivery in their own words; a fourth question asks about suppliers instead.
Answers agree when they are all present and lie within a stated tolerance of each other.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

SHARED_METRIC = "otd"
# Calendar anchor the demo questions name; team recipes and the governed reference use the same period.
DEMO_PERIOD_ANCHOR = "last quarter"
BOUNDARY_METRIC = "supplier_otd"
# Two rates agree when they differ by less than a twentieth of a percentage point, below the precision anyone reports.
AGREEMENT_TOLERANCE = 0.0005


@dataclass(frozen=True)
class DemoQuestion:
    """One persona's phrasing of a demo question."""

    persona: str
    question: str


SAME_QUESTION = (
    DemoQuestion("planning", "What was our service level last quarter?"),
    DemoQuestion("procurement", "How did customer delivery performance look last quarter?"),
    DemoQuestion("logistics", "What was the customer on time delivery rate last quarter?"),
)
BOUNDARY_QUESTION = DemoQuestion("logistics", "Were we on time for suppliers last quarter?")


def values_agree(values: Sequence[float | None], tolerance: float = AGREEMENT_TOLERANCE) -> bool:
    """True when every value is present and the largest and smallest differ by less than the tolerance."""
    if not values or any(v is None for v in values):
        return False
    present = [v for v in values if v is not None]
    return max(present) - min(present) < tolerance


def value_spread(values: Sequence[float | None]) -> float | None:
    """Largest minus smallest of the present values, or None when fewer than two are present."""
    present = [v for v in values if v is not None]
    return max(present) - min(present) if len(present) > 1 else None
