"""Converts the raw ontology document (loaded from YAML) into the immutable ontology model.

The parser checks shape only: required fields, field types, enum values, and unknown keys.
Cross-references such as relationship endpoints and key columns are checked later by the ontology validator.
"""
from __future__ import annotations

from supply_ontology.core.enums import AttributeType, Cardinality
from supply_ontology.core.errors import SemanticParseError
from supply_ontology.core.field_readers import (
    as_mapping,
    as_str,
    join_path,
    optional_bool,
    optional_list,
    reject_unknown_keys,
    require_enum,
    require_mapping,
    require_str,
    require_str_list,
)
from supply_ontology.core.ontology_model import (
    Attribute,
    Entity,
    Hierarchy,
    Ontology,
    Relationship,
)

ROOT_PATH = "ontology"
TOP_LEVEL_KEYS = frozenset({"entities", "relationships", "hierarchies"})
ENTITY_KEYS = frozenset({"label", "description", "key", "attributes"})
ATTRIBUTE_KEYS = frozenset({"type", "description", "derived"})
RELATIONSHIP_KEYS = frozenset({"name", "from", "to", "cardinality", "join"})
HIERARCHY_KEYS = frozenset({"name", "entity", "levels"})

# Attributes are physical source columns unless the YAML marks them as derived by the conform pipeline.
DEFAULT_ATTRIBUTE_DERIVED = False


def parse_ontology(raw: object) -> Ontology:
    """Parse the whole ontology document."""
    root = as_mapping(raw, ROOT_PATH)
    reject_unknown_keys(root, TOP_LEVEL_KEYS, ROOT_PATH)
    entities_path = join_path(ROOT_PATH, "entities")
    entities = {
        name: _parse_entity(name, value, join_path(entities_path, name))
        for name, value in require_mapping(root, "entities", ROOT_PATH).items()
    }
    relationships_path = join_path(ROOT_PATH, "relationships")
    relationships = tuple(
        _parse_relationship(item, f"{relationships_path}[{index}]")
        for index, item in enumerate(optional_list(root, "relationships", ROOT_PATH))
    )
    hierarchies_path = join_path(ROOT_PATH, "hierarchies")
    hierarchies = tuple(
        _parse_hierarchy(item, f"{hierarchies_path}[{index}]")
        for index, item in enumerate(optional_list(root, "hierarchies", ROOT_PATH))
    )
    return Ontology(entities=entities, relationships=relationships, hierarchies=hierarchies)


def _parse_entity(name: str, raw: object, path: str) -> Entity:
    fields = as_mapping(raw, path)
    reject_unknown_keys(fields, ENTITY_KEYS, path)
    attributes_path = join_path(path, "attributes")
    attributes = {
        attribute_name: _parse_attribute(
            attribute_name, value, join_path(attributes_path, attribute_name)
        )
        for attribute_name, value in require_mapping(fields, "attributes", path).items()
    }
    return Entity(
        name=name,
        label=require_str(fields, "label", path),
        description=require_str(fields, "description", path),
        key=require_str_list(fields, "key", path),
        attributes=attributes,
    )


def _parse_attribute(name: str, raw: object, path: str) -> Attribute:
    fields = as_mapping(raw, path)
    reject_unknown_keys(fields, ATTRIBUTE_KEYS, path)
    return Attribute(
        name=name,
        data_type=require_enum(fields, "type", path, AttributeType),
        description=require_str(fields, "description", path),
        derived=optional_bool(fields, "derived", path, DEFAULT_ATTRIBUTE_DERIVED),
    )


def _parse_relationship(raw: object, path: str) -> Relationship:
    fields = as_mapping(raw, path)
    reject_unknown_keys(fields, RELATIONSHIP_KEYS, path)
    join_field_path = join_path(path, "join")
    join_columns = tuple(
        (from_column, as_str(to_column, join_path(join_field_path, from_column)))
        for from_column, to_column in require_mapping(fields, "join", path).items()
    )
    if not join_columns:
        raise SemanticParseError(join_field_path, "must declare at least one column pair")
    return Relationship(
        name=require_str(fields, "name", path),
        from_entity=require_str(fields, "from", path),
        to_entity=require_str(fields, "to", path),
        cardinality=require_enum(fields, "cardinality", path, Cardinality),
        join_columns=join_columns,
    )


def _parse_hierarchy(raw: object, path: str) -> Hierarchy:
    fields = as_mapping(raw, path)
    reject_unknown_keys(fields, HIERARCHY_KEYS, path)
    return Hierarchy(
        name=require_str(fields, "name", path),
        entity=require_str(fields, "entity", path),
        levels=require_str_list(fields, "levels", path),
    )
