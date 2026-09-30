"""Graph logic over declared relationships: enumerate join paths, detect ambiguity, and resolve a unique path.

Relationships are traversed only in their declared child-to-parent direction, which keeps joins fan-out free.
The validator uses ambiguity detection at load time; the query compiler uses path resolution at query time.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from supply_ontology.core.errors import JoinPathError
from supply_ontology.core.ontology_model import Ontology, Relationship

JoinPath = tuple[Relationship, ...]
MIN_AMBIGUOUS_PATH_COUNT = 2


@dataclass(frozen=True)
class AmbiguousPath:
    """Two or more distinct declared paths lead from one entity to another."""

    start: str
    target: str
    paths: tuple[JoinPath, ...]


def outgoing_relationships(ontology: Ontology) -> dict[str, tuple[Relationship, ...]]:
    """Group relationships by the child entity they start from."""
    grouped: dict[str, list[Relationship]] = defaultdict(list)
    for relationship in ontology.relationships:
        grouped[relationship.from_entity].append(relationship)
    return {entity: tuple(edges) for entity, edges in grouped.items()}


def enumerate_paths(ontology: Ontology, start: str) -> dict[str, list[JoinPath]]:
    """Return every simple path from `start` to each reachable entity."""
    edges = outgoing_relationships(ontology)
    found: dict[str, list[JoinPath]] = defaultdict(list)
    stack: list[tuple[str, JoinPath, frozenset[str]]] = [(start, (), frozenset({start}))]
    while stack:
        entity, path, visited = stack.pop()
        for relationship in edges.get(entity, ()):
            if relationship.to_entity in visited:
                continue
            extended = path + (relationship,)
            found[relationship.to_entity].append(extended)
            stack.append((relationship.to_entity, extended, visited | {relationship.to_entity}))
    return dict(found)


def find_ambiguous_paths(ontology: Ontology) -> list[AmbiguousPath]:
    """List every (start, target) pair reachable by more than one declared path."""
    ambiguous: list[AmbiguousPath] = []
    for start in sorted(ontology.entities):
        for target, paths in sorted(enumerate_paths(ontology, start).items()):
            if len(paths) >= MIN_AMBIGUOUS_PATH_COUNT:
                ambiguous.append(AmbiguousPath(start, target, tuple(paths)))
    return ambiguous


def describe_path(path: JoinPath) -> str:
    """Render a join path as a readable chain of relationship names."""
    return " -> ".join(relationship.name for relationship in path)


def resolve_join_path(ontology: Ontology, start: str, target: str) -> JoinPath:
    """Return the unique declared path from `start` to `target`, or raise JoinPathError."""
    if start == target:
        return ()
    paths = enumerate_paths(ontology, start).get(target, [])
    if not paths:
        raise JoinPathError(f"No declared relationship path from '{start}' to '{target}'")
    if len(paths) >= MIN_AMBIGUOUS_PATH_COUNT:
        options = "; ".join(describe_path(path) for path in paths)
        raise JoinPathError(f"Ambiguous paths from '{start}' to '{target}': {options}")
    return paths[0]
