"""Parses the three vocabulary documents (dimensions, ambiguous terms, personas) into a Vocabulary.

Shape errors carry the dotted path of the offending field, like the ontology and metric parsers.
Cross-references (metric ids, dimension names, collisions) are checked by the vocabulary validator.
"""
from __future__ import annotations

from supply_ontology.core.field_readers import (
    as_mapping,
    as_str,
    join_path,
    optional_mapping,
    optional_str_list,
    reject_unknown_keys,
    require_mapping,
    require_str,
    require_str_list,
)
from supply_ontology.core.vocabulary_model import (
    DimensionDefinition,
    Persona,
    Vocabulary,
)

DIMENSION_KEYS = frozenset({"label", "synonyms"})
PERSONA_KEYS = frozenset({"label", "description", "metric_vocabulary", "dimension_vocabulary", "example_questions"})


def parse_vocabulary(dimensions_raw: object, ambiguity_raw: object, personas_raw: object) -> Vocabulary:
    """Parse all three documents."""
    return Vocabulary(
        dimensions=_parse_dimensions(dimensions_raw),
        ambiguous_terms=_parse_ambiguity(ambiguity_raw),
        personas=_parse_personas(personas_raw),
    )


def _parse_dimensions(raw: object) -> dict[str, DimensionDefinition]:
    path = "dimensions"
    root = as_mapping(raw, path)
    reject_unknown_keys(root, frozenset({"dimensions"}), path)
    parsed = {}
    for name, value in require_mapping(root, "dimensions", path).items():
        item_path = join_path(path, name)
        fields = as_mapping(value, item_path)
        reject_unknown_keys(fields, DIMENSION_KEYS, item_path)
        parsed[name] = DimensionDefinition(
            name=name, label=require_str(fields, "label", item_path), synonyms=optional_str_list(fields, "synonyms", item_path)
        )
    return parsed


def _parse_ambiguity(raw: object) -> dict[str, dict[str, tuple[str, ...]]]:
    path = "ambiguity"
    root = as_mapping(raw, path)
    reject_unknown_keys(root, frozenset({"ambiguous_terms"}), path)
    terms_path = join_path(path, "ambiguous_terms")
    parsed = {}
    for term, candidates in require_mapping(root, "ambiguous_terms", path).items():
        candidates_path = join_path(terms_path, term)
        mapping = as_mapping(candidates, candidates_path)
        parsed[term] = {metric: require_str_list(mapping, metric, candidates_path) for metric in mapping}
    return parsed


def _parse_personas(raw: object) -> dict[str, Persona]:
    path = "personas"
    root = as_mapping(raw, path)
    reject_unknown_keys(root, frozenset({"personas"}), path)
    parsed = {}
    for name, value in require_mapping(root, "personas", path).items():
        item_path = join_path(path, name)
        fields = as_mapping(value, item_path)
        reject_unknown_keys(fields, PERSONA_KEYS, item_path)
        parsed[name] = Persona(
            name=name,
            label=require_str(fields, "label", item_path),
            description=require_str(fields, "description", item_path),
            metric_vocabulary=_str_map(optional_mapping(fields, "metric_vocabulary", item_path), join_path(item_path, "metric_vocabulary")),
            dimension_vocabulary=_str_map(optional_mapping(fields, "dimension_vocabulary", item_path), join_path(item_path, "dimension_vocabulary")),
            example_questions=optional_str_list(fields, "example_questions", item_path),
        )
    return parsed


def _str_map(raw: object, path: str) -> dict[str, str]:
    return {key: as_str(value, join_path(path, key)) for key, value in as_mapping(raw, path).items()}
