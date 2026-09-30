"""Answers business questions with governed metrics: bind terms deterministically, let the model fill in the rest, validate, run.

Wording that matches a governed term fixes the metric; the model only chooses dimensions, filters, and time, from a closed catalog.
An invalid reply gets exactly one retry with the validation problems; ambiguous wording yields a clarifying question.
"""
from __future__ import annotations

from collections.abc import Sequence

from supply_ontology.core.calendar_anchors import calendar_anchors
from supply_ontology.core.catalog import SemanticCatalog
from supply_ontology.core.errors import QueryValidationError, SemanticParseError
from supply_ontology.core.grounding import (
    grounded_dimensions,
    grounded_time_range,
    requested_time_grain,
)
from supply_ontology.core.model_response import (
    ClarifyDecision,
    ModelOutputError,
    QueryDecision,
    UnsupportedDecision,
    parse_decision,
)
from supply_ontology.core.prompt_builder import (
    build_retry_message,
    build_system_message,
    build_user_message,
)
from supply_ontology.core.query_spec import QuerySpec
from supply_ontology.core.query_spec_parser import parse_query_spec
from supply_ontology.core.query_validator import validate_query
from supply_ontology.core.spec_governance import governance_problems
from supply_ontology.core.term_matcher import (
    TermMatches,
    build_context_index,
    build_term_index,
    match_terms,
)
from supply_ontology.data_pipeline.llm_client import (
    LLMClient,
    LLMError,
    build_llm_client,
)
from supply_ontology.services.nl_models import (
    MODEL_UNAVAILABLE,
    NO_VALID_QUERY,
    NOT_SUPPORTED,
    RESOLVED_BY_MODEL,
    RESOLVED_BY_WORDING,
    Answer,
    Clarification,
    NLResponse,
    Unanswerable,
)
from supply_ontology.services.query_service import QueryService

MAX_ATTEMPTS = 2
DISTINCT_SQL = "SELECT DISTINCT {attribute} AS value FROM {entity} WHERE {attribute} IS NOT NULL ORDER BY 1"


class NLService:
    """Question in, governed answer (or clarification) out."""

    def __init__(self, catalog: SemanticCatalog, query_service: QueryService, llm_client: LLMClient | None = None) -> None:
        self.catalog = catalog
        self.query_service = query_service
        self.llm_client = llm_client or build_llm_client()
        self.dimension_values = self._load_dimension_values()
        self.anchors = calendar_anchors(query_service.as_of)
        self.context_index = build_context_index(catalog)
        self.system_message = build_system_message(catalog, query_service.as_of, self.dimension_values)

    def ask(self, question: str, persona: str | None) -> NLResponse:
        """Answer one question as one persona."""
        matches = match_terms(question, build_term_index(self.catalog, persona), self.context_index)
        messages = [self.system_message, build_user_message(question, persona, self.catalog, matches)]
        replies: list[str] = []
        for _ in range(MAX_ATTEMPTS):
            try:
                reply = self.llm_client.complete(messages)
            except LLMError as error:
                return Unanswerable(question, persona, str(error), tuple(replies), MODEL_UNAVAILABLE)
            replies.append(reply)
            outcome = self._interpret(question, persona, reply, matches, tuple(replies))
            if not isinstance(outcome, list):
                return outcome
            messages += [{"role": "assistant", "content": reply}, build_retry_message(outcome)]
        return Unanswerable(question, persona, "No valid query after retry: " + "; ".join(outcome), tuple(replies), NO_VALID_QUERY)

    def _interpret(
        self, question: str, persona: str | None, reply: str, matches: TermMatches, replies: tuple[str, ...]
    ) -> NLResponse | list[str]:
        """A final response, or the list of problems to send back for a retry."""
        try:
            decision = parse_decision(reply)
        except ModelOutputError as error:
            return [str(error)]
        if isinstance(decision, UnsupportedDecision) and not matches.bound_metrics:
            return Unanswerable(question, persona, decision.reason, replies, NOT_SUPPORTED)
        if isinstance(decision, ClarifyDecision):
            about_metrics = any(o in self.catalog.metrics for o in decision.options)
            if matches.bound_metrics and about_metrics:
                return [f"The wording already binds {', '.join(matches.bound_metrics)}; do not ask which metric. Reply with a query."]
            options = decision.options if matches.bound_metrics else tuple(o for o in decision.options if o in self.catalog.metrics)
            return Clarification(question, persona, decision.question, options or self._ambiguous_options(matches), replies)
        if not isinstance(decision, QueryDecision):
            return [f"The wording binds {', '.join(matches.bound_metrics)}; reply with a query using exactly those metrics."]
        try:
            spec = self._ground(parse_query_spec(decision.spec), matches, question, persona)
        except SemanticParseError as error:
            return [str(error)]
        problems = self._problems(spec, matches)
        if problems:
            return problems
        how = RESOLVED_BY_WORDING if matches.bound_metrics else RESOLVED_BY_MODEL
        try:
            result = self.query_service.run(spec)
        except QueryValidationError as error:
            return [issue.message for issue in error.issues]
        return Answer(question, persona, how, tuple(m.term for m in matches.matches), result, replies)

    def _ground(self, spec: QuerySpec, matches: TermMatches, question: str, persona: str | None) -> QuerySpec:
        """Wording decides metrics (when bound), grain, range, and dimensions; the model's proposal only fills gaps."""
        return QuerySpec(
            metrics=matches.bound_metrics or spec.metrics,
            dimensions=grounded_dimensions(question, spec.dimensions, self.catalog.vocabulary, persona),
            filters=spec.filters,
            time_range=grounded_time_range(question, spec.time_range, self.anchors),
            time_grain=requested_time_grain(question),
        )

    def _problems(self, spec: QuerySpec, matches: TermMatches) -> list[str]:
        problems = [issue.message for issue in validate_query(spec, self.catalog)]
        problems += governance_problems(spec, self.catalog, self.dimension_values)
        candidates = {m for match in matches.ambiguous for m in match.metrics}
        if candidates and not matches.bound_metrics:
            problems += [f"'{m}' is not one of the meanings of the ambiguous wording ({', '.join(sorted(candidates))})"
                         for m in spec.metrics if m not in candidates]
        return problems

    def _ambiguous_options(self, matches: TermMatches) -> tuple[str, ...]:
        return tuple(dict.fromkeys(m for match in matches.ambiguous for m in match.metrics))

    def _load_dimension_values(self) -> dict[str, Sequence[object]]:
        values = {}
        for name in self.catalog.vocabulary.dimensions:
            entity, _, attribute = name.partition(".")
            frame = self.query_service.connection_manager.execute(DISTINCT_SQL.format(entity=entity, attribute=attribute))
            values[name] = frame["value"].tolist()
        return values
