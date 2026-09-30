"""Immutable data model for the supply chain ontology: entities, attributes, relationships, and hierarchies.

Instances are produced by the ontology parser and are never mutated afterwards.
The model carries no validation logic; consistency checks live in the ontology validator.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from supply_ontology.core.enums import AttributeType, Cardinality


@dataclass(frozen=True)
class Attribute:
    """A named, typed business attribute of an entity."""

    name: str
    data_type: AttributeType
    description: str
    derived: bool


@dataclass(frozen=True)
class Entity:
    """A business entity with a primary key and its attributes."""

    name: str
    label: str
    description: str
    key: tuple[str, ...]
    attributes: Mapping[str, Attribute]

    def attribute(self, name: str) -> Attribute | None:
        """Return the attribute with this name, or None when it is not declared."""
        return self.attributes.get(name)


@dataclass(frozen=True)
class Relationship:
    """A declared join from a child entity to a parent entity."""

    name: str
    from_entity: str
    to_entity: str
    cardinality: Cardinality
    join_columns: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Hierarchy:
    """An ordered drill path over attributes of one entity, coarsest level first."""

    name: str
    entity: str
    levels: tuple[str, ...]


@dataclass(frozen=True)
class Ontology:
    """The complete set of entities, relationships, and hierarchies."""

    entities: Mapping[str, Entity]
    relationships: tuple[Relationship, ...]
    hierarchies: tuple[Hierarchy, ...]

    def entity(self, name: str) -> Entity | None:
        """Return the entity with this name, or None when it is not declared."""
        return self.entities.get(name)
