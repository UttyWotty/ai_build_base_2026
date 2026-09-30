"""Governance checks on a model-proposed spec beyond compiler validity: governed dimensions and known filter values.

The compiler accepts any reachable attribute, but the conversational layer may only use dimensions in the vocabulary.
Filter values for text dimensions must exist in the data; unknown values come back with close matches as suggestions.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from difflib import get_close_matches

from supply_ontology.core.catalog import SemanticCatalog
from supply_ontology.core.query_spec import QuerySpec

SUGGESTION_COUNT = 3


def governance_problems(
    spec: QuerySpec, catalog: SemanticCatalog, known_values: Mapping[str, Sequence[object]]
) -> list[str]:
    """Problems that make the spec unacceptable for the conversational layer."""
    governed = catalog.vocabulary.dimensions
    problems = [
        f"'{d.name}' is not a governed dimension; use one of: {', '.join(governed)}"
        for d in (*spec.dimensions, *(f.dimension for f in spec.filters)) if d.name not in governed
    ]
    for query_filter in spec.filters:
        values = known_values.get(query_filter.dimension.name)
        if not values:
            continue
        text_values = [str(v) for v in values]
        for value in query_filter.values:
            if str(value) not in text_values:
                close = get_close_matches(str(value), text_values, n=SUGGESTION_COUNT)
                hint = f"; did you mean {', '.join(close)}?" if close else ""
                problems.append(f"value '{value}' does not exist for {query_filter.dimension.name}{hint}")
    return problems
