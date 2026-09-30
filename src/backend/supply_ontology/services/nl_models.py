"""Result types of the natural-language service: an answer, a clarifying question, or a reasoned refusal.

Every outcome records how the metrics were resolved and the raw model replies, so answers can be audited.
The UI and the demo render these types; they carry no behaviour.
"""
from __future__ import annotations

from dataclasses import dataclass

from supply_ontology.services.query_service import QueryResult

RESOLVED_BY_WORDING = "wording"
RESOLVED_BY_MODEL = "model"
# Why a question went unanswered.
MODEL_UNAVAILABLE = "model_unavailable"
NO_VALID_QUERY = "no_valid_query"
NOT_SUPPORTED = "not_supported"


@dataclass(frozen=True)
class Answer:
    """A governed answer to a question."""

    question: str
    persona: str | None
    resolved_by: str
    matched_terms: tuple[str, ...]
    result: QueryResult
    model_replies: tuple[str, ...]


@dataclass(frozen=True)
class Clarification:
    """The question could mean several metrics; the user must choose."""

    question: str
    persona: str | None
    prompt: str
    options: tuple[str, ...]
    model_replies: tuple[str, ...]


@dataclass(frozen=True)
class Unanswerable:
    """No governed metric answers the question, or no valid spec could be produced."""

    question: str
    persona: str | None
    reason: str
    model_replies: tuple[str, ...]
    kind: str


NLResponse = Answer | Clarification | Unanswerable
