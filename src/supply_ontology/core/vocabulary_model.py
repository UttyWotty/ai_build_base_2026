"""Governed business vocabulary: queryable dimensions with business names, ambiguous terms, and team personas.

Dimensions give ontology attributes the names people use; ambiguous terms list the metrics a vague phrase could mean.
Personas add each team's jargon, which must map onto the same governed metrics and can never redefine them.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class DimensionDefinition:
    """A governed query dimension (entity.attribute) with its business label and synonyms."""

    name: str
    label: str
    synonyms: tuple[str, ...]


@dataclass(frozen=True)
class Persona:
    """A team's vocabulary: phrases mapped to metric ids and to governed dimensions."""

    name: str
    label: str
    description: str
    metric_vocabulary: Mapping[str, str]
    dimension_vocabulary: Mapping[str, str]
    example_questions: tuple[str, ...]


@dataclass(frozen=True)
class Vocabulary:
    """Everything the natural-language layer may use beyond the ontology and metrics."""

    dimensions: Mapping[str, DimensionDefinition]
    # ambiguous phrase -> candidate metric id -> context words that select that candidate
    ambiguous_terms: Mapping[str, Mapping[str, tuple[str, ...]]]
    personas: Mapping[str, Persona]


EMPTY_VOCABULARY = Vocabulary(dimensions={}, ambiguous_terms={}, personas={})
