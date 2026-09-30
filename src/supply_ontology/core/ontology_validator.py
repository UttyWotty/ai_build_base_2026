"""Semantic consistency checks for a parsed ontology.

Checks cover identifier naming, entity keys, relationship endpoints and join columns, hierarchies, and join-path ambiguity.
All problems are returned together as ValidationIssue records rather than raised one at a time.
"""
from __future__ import annotations

from collections import Counter

from supply_ontology.core.errors import ValidationIssue
from supply_ontology.core.identifiers import IDENTIFIER_RULE, is_valid_identifier
from supply_ontology.core.join_paths import describe_path, find_ambiguous_paths
from supply_ontology.core.ontology_model import (
    Entity,
    Hierarchy,
    Ontology,
    Relationship,
)

MIN_HIERARCHY_LEVELS = 2


def validate_ontology(ontology: Ontology) -> list[ValidationIssue]:
    """Return every consistency problem in the ontology; an empty list means it is valid."""
    issues: list[ValidationIssue] = []
    for entity in ontology.entities.values():
        issues.extend(_check_entity(entity))
    issues.extend(_check_duplicate_names("relationship", [r.name for r in ontology.relationships]))
    for relationship in ontology.relationships:
        issues.extend(_check_relationship(relationship, ontology))
    issues.extend(_check_duplicate_names("hierarchy", [h.name for h in ontology.hierarchies]))
    for hierarchy in ontology.hierarchies:
        issues.extend(_check_hierarchy(hierarchy, ontology))
    for ambiguous in find_ambiguous_paths(ontology):
        options = "; ".join(describe_path(path) for path in ambiguous.paths)
        issues.append(
            ValidationIssue(
                f"entity {ambiguous.start}",
                f"reaches '{ambiguous.target}' by more than one path ({options})",
            )
        )
    return issues


def _check_entity(entity: Entity) -> list[ValidationIssue]:
    location = f"entity {entity.name}"
    issues = [
        ValidationIssue(location, f"name '{name}' {IDENTIFIER_RULE}")
        for name in (entity.name, *entity.attributes)
        if not is_valid_identifier(name)
    ]
    if not entity.key:
        issues.append(ValidationIssue(location, "key must list at least one attribute"))
    for column in entity.key:
        if entity.attribute(column) is None:
            issues.append(ValidationIssue(location, f"key column '{column}' is not an attribute"))
    if len(set(entity.key)) != len(entity.key):
        issues.append(ValidationIssue(location, "key lists a column more than once"))
    return issues


def _check_duplicate_names(kind: str, names: list[str]) -> list[ValidationIssue]:
    return [
        ValidationIssue(f"{kind} {name}", f"{kind} name is declared {count} times")
        for name, count in sorted(Counter(names).items())
        if count > 1
    ]


def _check_relationship(relationship: Relationship, ontology: Ontology) -> list[ValidationIssue]:
    location = f"relationship {relationship.name}"
    child = ontology.entity(relationship.from_entity)
    parent = ontology.entity(relationship.to_entity)
    missing = [
        ValidationIssue(location, f"entity '{name}' is not declared")
        for name, entity in ((relationship.from_entity, child), (relationship.to_entity, parent))
        if entity is None
    ]
    if child is None or parent is None:
        return missing
    issues: list[ValidationIssue] = []
    if not is_valid_identifier(relationship.name):
        issues.append(ValidationIssue(location, f"name {IDENTIFIER_RULE}"))
    for child_column, parent_column in relationship.join_columns:
        issues.extend(_check_join_pair(location, child, child_column, parent, parent_column))
    parent_columns = {parent_column for _, parent_column in relationship.join_columns}
    if parent_columns != set(parent.key):
        issues.append(
            ValidationIssue(location, f"must join on the full key of '{parent.name}' {list(parent.key)}")
        )
    return issues


def _check_join_pair(
    location: str, child: Entity, child_column: str, parent: Entity, parent_column: str
) -> list[ValidationIssue]:
    child_attribute = child.attribute(child_column)
    parent_attribute = parent.attribute(parent_column)
    issues = [
        ValidationIssue(location, f"'{entity.name}.{column}' is not an attribute")
        for entity, column, attribute in (
            (child, child_column, child_attribute),
            (parent, parent_column, parent_attribute),
        )
        if attribute is None
    ]
    if child_attribute and parent_attribute and child_attribute.data_type != parent_attribute.data_type:
        issues.append(
            ValidationIssue(
                location,
                f"type mismatch: '{child.name}.{child_column}' is {child_attribute.data_type.value}, "
                f"'{parent.name}.{parent_column}' is {parent_attribute.data_type.value}",
            )
        )
    return issues


def _check_hierarchy(hierarchy: Hierarchy, ontology: Ontology) -> list[ValidationIssue]:
    location = f"hierarchy {hierarchy.name}"
    entity = ontology.entity(hierarchy.entity)
    if entity is None:
        return [ValidationIssue(location, f"entity '{hierarchy.entity}' is not declared")]
    issues = [
        ValidationIssue(location, f"level '{level}' is not an attribute of '{entity.name}'")
        for level in hierarchy.levels
        if entity.attribute(level) is None
    ]
    if len(hierarchy.levels) < MIN_HIERARCHY_LEVELS:
        issues.append(ValidationIssue(location, f"needs at least {MIN_HIERARCHY_LEVELS} levels"))
    if len(set(hierarchy.levels)) != len(hierarchy.levels):
        issues.append(ValidationIssue(location, "lists a level more than once"))
    return issues
