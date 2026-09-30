"""Deterministic binding of governed terms in a question: longest match wins, and bound metrics cannot be overridden.

The index holds every governed metric term, the persona's jargon, and the ambiguous terms with their candidate metrics.
Matching is on whole words after normalisation, so "supplier on time delivery" beats both "on time delivery" and "on time".
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from supply_ontology.core.catalog import SemanticCatalog
from supply_ontology.core.terms import normalize_text

WORD_PAD = " "


@dataclass(frozen=True)
class TermMatch:
    """One governed phrase found in the question; ambiguous phrases may be settled by context words."""

    term: str
    start: int
    metrics: tuple[str, ...]
    ambiguous: bool
    settled_by: str | None = None

    @property
    def end(self) -> int:
        return self.start + len(self.term)


@dataclass(frozen=True)
class TermMatches:
    """Result of matching: metrics bound by unambiguous terms, and ambiguous phrases left to resolve."""

    bound_metrics: tuple[str, ...]
    ambiguous: tuple[TermMatch, ...]
    matches: tuple[TermMatch, ...]


TermIndex = dict[str, tuple[tuple[str, ...], bool]]
ContextIndex = dict[str, dict[str, tuple[str, ...]]]


def build_term_index(catalog: SemanticCatalog, persona: str | None) -> TermIndex:
    """Normalized phrase -> (metric ids, is_ambiguous) for the catalog plus one persona's vocabulary."""
    index: TermIndex = {}
    for metric in catalog.metrics.values():
        for term in (metric.id, metric.label, *metric.synonyms):
            index[normalize_text(term)] = ((metric.id,), False)
    if persona is not None and persona in catalog.vocabulary.personas:
        for phrase, metric_id in catalog.vocabulary.personas[persona].metric_vocabulary.items():
            index[normalize_text(phrase)] = ((metric_id,), False)
    for term, candidates in catalog.vocabulary.ambiguous_terms.items():
        index[normalize_text(term)] = (tuple(candidates), True)
    return index


def build_context_index(catalog: SemanticCatalog) -> ContextIndex:
    """Normalized ambiguous phrase -> candidate metric -> normalized context words."""
    return {
        normalize_text(term): {m: tuple(normalize_text(w) for w in words) for m, words in candidates.items()}
        for term, candidates in catalog.vocabulary.ambiguous_terms.items()
    }


def longest_matches(text: str, phrases: Iterable[str]) -> list[tuple[str, int]]:
    """Whole-word occurrences of phrases in normalized text, longest first, without overlaps, in text order."""
    padded = f"{WORD_PAD}{text}{WORD_PAD}"
    found = []
    for phrase in set(phrases):
        position = padded.find(f"{WORD_PAD}{phrase}{WORD_PAD}")
        while position != -1:
            found.append((phrase, position))
            position = padded.find(f"{WORD_PAD}{phrase}{WORD_PAD}", position + 1)
    chosen: list[tuple[str, int]] = []
    for phrase, start in sorted(found, key=lambda item: (-len(item[0]), item[1])):
        if all(start + len(phrase) <= s or start >= s + len(p) for p, s in chosen):
            chosen.append((phrase, start))
    return sorted(chosen, key=lambda item: item[1])


def contains_phrase(text: str, phrase: str) -> bool:
    """Whole-word containment on normalized text."""
    return f"{WORD_PAD}{phrase}{WORD_PAD}" in f"{WORD_PAD}{text}{WORD_PAD}"


def match_terms(question: str, index: TermIndex, context: ContextIndex) -> TermMatches:
    """Find governed phrases, keep the longest non-overlapping ones, settle ambiguity by context, split bound from open."""
    text = normalize_text(question)
    chosen = [
        _settle(TermMatch(term, start, index[term][0], index[term][1]), text, context)
        for term, start in longest_matches(text, index)
    ]
    bound = tuple(dict.fromkeys(m.metrics[0] for m in chosen if not m.ambiguous))
    return TermMatches(bound, tuple(m for m in chosen if m.ambiguous), tuple(chosen))


def _settle(match: TermMatch, text: str, context: ContextIndex) -> TermMatch:
    """Bind an ambiguous match when context words point to exactly one candidate."""
    if not match.ambiguous:
        return match
    hits = {m: w for m, words in context.get(match.term, {}).items() for w in words if contains_phrase(text, w)}
    if len(hits) != 1:
        return match
    metric_id, word = next(iter(hits.items()))
    return TermMatch(match.term, match.start, (metric_id,), False, settled_by=word)
