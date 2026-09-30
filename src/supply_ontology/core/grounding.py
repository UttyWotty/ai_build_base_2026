"""Grounds the parts of a model-proposed spec that the question's wording should decide: time grain, time range, and dimensions.

The model proposes; these rules keep only what the wording supports, so equivalent phrasings produce identical specs.
A grain needs trend wording, a range needs a period phrase or an explicit year, and a dimension needs one of its names.
"""
from __future__ import annotations

import re
from collections.abc import Mapping

from supply_ontology.core.enums import TimeGrain
from supply_ontology.core.query_spec import DimensionRef, TimeRange
from supply_ontology.core.term_matcher import contains_phrase, longest_matches
from supply_ontology.core.terms import normalize_text
from supply_ontology.core.vocabulary_model import Vocabulary

GRAIN_PHRASES: dict[TimeGrain, tuple[str, ...]] = {
    TimeGrain.DAY: ("by day", "daily", "per day", "each day"),
    TimeGrain.WEEK: ("by week", "weekly", "per week", "each week", "week by week"),
    TimeGrain.MONTH: ("by month", "monthly", "per month", "each month", "month by month"),
    TimeGrain.QUARTER: ("by quarter", "quarterly", "per quarter", "each quarter", "quarter by quarter"),
    TimeGrain.YEAR: ("by year", "yearly", "annually", "per year", "each year", "year by year"),
}
# "trend" or "over time" without a unit means a monthly trend.
TREND_PHRASES = ("trend", "over time", "trending")
TREND_DEFAULT_GRAIN = TimeGrain.MONTH
ANCHOR_PHRASES: dict[str, tuple[str, ...]] = {
    "last quarter": ("last quarter", "previous quarter", "prior quarter", "last complete quarter"),
    "this quarter to date": ("this quarter", "current quarter", "quarter to date", "qtd"),
    "last month": ("last month", "previous month", "prior month"),
    "this month to date": ("this month", "current month", "month to date", "mtd"),
    "this year to date": ("this year", "current year", "year to date", "ytd"),
    "last year": ("last year", "previous year", "prior year"),
    "last 12 complete months": ("last 12 months", "past 12 months", "last twelve months", "trailing 12 months", "ltm"),
}
YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")


def requested_time_grain(question: str) -> TimeGrain | None:
    """The grain the wording asks for, or None for a single total."""
    text = normalize_text(question)
    for grain, phrases in GRAIN_PHRASES.items():
        if any(contains_phrase(text, p) for p in phrases):
            return grain
    return TREND_DEFAULT_GRAIN if any(contains_phrase(text, p) for p in TREND_PHRASES) else None


def grounded_time_range(question: str, proposed: TimeRange | None, anchors: Mapping[str, TimeRange]) -> TimeRange | None:
    """An anchor named in the wording wins; an explicit year keeps the model's range; otherwise no range."""
    text = normalize_text(question)
    for anchor, phrases in ANCHOR_PHRASES.items():
        if anchor in anchors and any(contains_phrase(text, p) for p in phrases):
            return anchors[anchor]
    return proposed if YEAR_PATTERN.search(question) else None


PLURAL_SUFFIX = "s"
GROUPING_WORDS = ("by", "per", "for each", "across")
# "by plant and segment": a dimension right after a grouped one, joined by one of these, is grouped too.
CHAIN_CONNECTORS = ("and", "")


def dimension_phrases(vocabulary: Vocabulary, persona: str | None) -> dict[str, str]:
    """Normalized phrase (and its plural) -> governed dimension name, including the persona's words."""
    pairs = [(p, name) for name, d in vocabulary.dimensions.items() for p in (d.label, *d.synonyms)]
    if persona is not None and persona in vocabulary.personas:
        pairs += list(vocabulary.personas[persona].dimension_vocabulary.items())
    phrases = {}
    for phrase, name in pairs:
        normalized = normalize_text(phrase)
        phrases[normalized] = name
        phrases.setdefault(normalized + PLURAL_SUFFIX, name)
    return phrases


def grounded_dimensions(
    question: str, proposed: tuple[DimensionRef, ...], vocabulary: Vocabulary, persona: str | None
) -> tuple[DimensionRef, ...]:
    """Keep proposed dimensions the wording names; add any 'by <dimension>' the model missed."""
    text = normalize_text(question)
    phrases = dimension_phrases(vocabulary, persona)
    matches = longest_matches(text, phrases)
    named = {phrases[p] for p, _ in matches}
    grouped = _grouped(text, [(phrases[p], start, start + len(p)) for p, start in matches])
    kept = [d for d in proposed if d.name in named]
    for name in grouped:
        if name not in {d.name for d in kept}:
            entity, _, attribute = name.partition(".")
            kept.append(DimensionRef(entity, attribute))
    return tuple(kept)


def _grouped(text: str, spans: list[tuple[str, int, int]]) -> list[str]:
    """Dimensions introduced by a grouping word, or chained to one with 'and'."""
    grouped, previous_end = [], None
    for name, start, end in spans:
        after_grouping_word = any(text[:max(start - 1, 0)].endswith(w) for w in GROUPING_WORDS)
        chained = previous_end is not None and text[previous_end:start].strip() in CHAIN_CONNECTORS
        if after_grouping_word or chained:
            grouped.append(name)
            previous_end = end
    return grouped
