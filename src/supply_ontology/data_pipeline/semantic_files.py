"""Filesystem adapter that loads the semantic YAML files and builds the validated catalog.

YAML is parsed with a loader that rejects duplicate mapping keys, which the default loader silently overwrites.
Parsing and validation are delegated to the pure core; this module only reads files and reports I/O errors.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode

from supply_ontology.core.catalog import SemanticCatalog, build_catalog
from supply_ontology.core.errors import SemanticFileError
from supply_ontology.core.metric_parser import parse_metric
from supply_ontology.core.ontology_parser import parse_ontology
from supply_ontology.core.vocabulary_parser import parse_vocabulary

ONTOLOGY_FILENAME = "ontology.yaml"
METRICS_DIRNAME = "metrics"
METRIC_FILE_PATTERN = "*.yaml"
DIMENSIONS_FILENAME = "dimensions.yaml"
AMBIGUITY_FILENAME = "ambiguity.yaml"
PERSONAS_FILENAME = "personas.yaml"
FILE_ENCODING = "utf-8"


class _UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that fails on duplicate keys instead of keeping the last one."""


def _construct_unique_mapping(loader: _UniqueKeyLoader, node: MappingNode, deep: bool = False) -> dict[object, object]:
    loader.flatten_mapping(node)
    seen: set[object] = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise ConstructorError(None, None, f"duplicate key {key!r}", key_node.start_mark)
        seen.add(key)
    return loader.construct_mapping(node, deep=deep)


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


def load_yaml_document(path: Path) -> object:
    """Read one YAML file, rejecting duplicate keys."""
    try:
        text = path.read_text(encoding=FILE_ENCODING)
    except OSError as error:
        raise SemanticFileError(f"Cannot read {path}: {error}") from error
    try:
        return yaml.load(text, Loader=_UniqueKeyLoader)
    except yaml.YAMLError as error:
        raise SemanticFileError(f"Invalid YAML in {path}: {error}") from error


def load_catalog(semantic_dir: Path) -> SemanticCatalog:
    """Load the ontology, every metric file, and the vocabulary under `semantic_dir` into a validated catalog."""
    ontology = parse_ontology(load_yaml_document(semantic_dir / ONTOLOGY_FILENAME))
    metric_files = sorted((semantic_dir / METRICS_DIRNAME).glob(METRIC_FILE_PATTERN))
    if not metric_files:
        raise SemanticFileError(f"No metric files found in {semantic_dir / METRICS_DIRNAME}")
    metrics = [parse_metric(load_yaml_document(path), path.name) for path in metric_files]
    vocabulary = parse_vocabulary(
        load_yaml_document(semantic_dir / DIMENSIONS_FILENAME),
        load_yaml_document(semantic_dir / AMBIGUITY_FILENAME),
        load_yaml_document(semantic_dir / PERSONAS_FILENAME),
    )
    return build_catalog(ontology, metrics, vocabulary)
