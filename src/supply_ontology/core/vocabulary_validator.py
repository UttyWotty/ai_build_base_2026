"""Consistency checks for the governed vocabulary against the ontology and metrics.

Dimensions must be existing, non-derived attributes; every phrase must resolve to exactly one meaning across the whole catalog.
Persona jargon may add new phrases for a metric but may never reuse a governed term for a different metric.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from supply_ontology.core.errors import ValidationIssue
from supply_ontology.core.metric_model import Metric
from supply_ontology.core.ontology_model import Ontology
from supply_ontology.core.query_spec import DIMENSION_SEPARATOR
from supply_ontology.core.terms import normalize_term
from supply_ontology.core.vocabulary_model import Vocabulary

MIN_AMBIGUOUS_CANDIDATES = 2


def metric_terms(metrics: Sequence[Metric]) -> dict[str, str]:
    """Normalized governed term (id, label, synonym) -> metric id."""
    return {normalize_term(t): m.id for m in metrics for t in (m.id, m.label, *m.synonyms)}


def validate_vocabulary(vocabulary: Vocabulary, ontology: Ontology, metrics: Sequence[Metric]) -> list[ValidationIssue]:
    """Return every vocabulary problem; an empty list means it is consistent."""
    governed = metric_terms(metrics)
    issues = _check_dimensions(vocabulary, ontology, governed)
    known = {m.id for m in metrics}
    for term, candidates in vocabulary.ambiguous_terms.items():
        issues += _check_ambiguous_term(term, candidates, governed, known)
    for persona in vocabulary.personas.values():
        issues += _check_persona_terms(persona.name, persona.metric_vocabulary, governed, known, vocabulary)
        issues += [
            ValidationIssue(f"persona {persona.name}", f"dimension phrase '{p}' points to ungoverned dimension '{d}'")
            for p, d in persona.dimension_vocabulary.items() if d not in vocabulary.dimensions
        ]
    return issues


def _check_ambiguous_term(
    term: str, candidates: Mapping[str, tuple[str, ...]], governed: Mapping[str, str], known: set[str]
) -> list[ValidationIssue]:
    location = f"ambiguous term '{term}'"
    issues = []
    if len(candidates) < MIN_AMBIGUOUS_CANDIDATES:
        issues.append(ValidationIssue(location, "needs at least two candidate metrics"))
    issues += [ValidationIssue(location, f"unknown metric '{c}'") for c in candidates if c not in known]
    if normalize_term(term) in governed:
        issues.append(ValidationIssue(location, f"is already a governed term for '{governed[normalize_term(term)]}'"))
    owner: dict[str, str] = {}
    for metric_id, words in candidates.items():
        for word in words:
            if owner.setdefault(normalize_term(word), metric_id) != metric_id:
                issues.append(ValidationIssue(location, f"context word '{word}' is shared by '{owner[normalize_term(word)]}' and '{metric_id}'"))
    return issues


def _check_dimensions(vocabulary: Vocabulary, ontology: Ontology, governed: Mapping[str, str]) -> list[ValidationIssue]:
    issues, seen = [], {}
    for name, definition in vocabulary.dimensions.items():
        entity_name, _, attribute_name = name.partition(DIMENSION_SEPARATOR)
        entity = ontology.entity(entity_name)
        attribute = entity.attribute(attribute_name) if entity else None
        if attribute is None:
            issues.append(ValidationIssue(f"dimension {name}", "is not an ontology attribute"))
        elif attribute.derived:
            issues.append(ValidationIssue(f"dimension {name}", "derived attributes cannot be dimensions"))
        for synonym in (definition.label, *definition.synonyms):
            term = normalize_term(synonym)
            if term in governed:
                issues.append(ValidationIssue(f"dimension {name}", f"synonym '{synonym}' is a metric term"))
            if seen.setdefault(term, name) != name:
                issues.append(ValidationIssue(f"dimension {name}", f"synonym '{synonym}' also names '{seen[term]}'"))
    return issues


def _check_persona_terms(
    persona: str, vocabulary_map: Mapping[str, str], governed: Mapping[str, str], known: set[str], vocabulary: Vocabulary
) -> list[ValidationIssue]:
    location = f"persona {persona}"
    issues = []
    ambiguous = {normalize_term(t) for t in vocabulary.ambiguous_terms}
    for phrase, metric_id in vocabulary_map.items():
        term = normalize_term(phrase)
        if metric_id not in known:
            issues.append(ValidationIssue(location, f"phrase '{phrase}' maps to unknown metric '{metric_id}'"))
        if term in governed and governed[term] != metric_id:
            issues.append(ValidationIssue(location, f"phrase '{phrase}' would redefine governed term for '{governed[term]}'"))
        if term in ambiguous:
            issues.append(ValidationIssue(location, f"phrase '{phrase}' is a governed ambiguous term"))
    return issues
