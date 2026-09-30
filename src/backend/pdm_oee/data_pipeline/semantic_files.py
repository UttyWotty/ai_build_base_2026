"""Filesystem adapter that loads the governed catalog files (plant, losses, measures, metrics) and builds the catalog.

YAML is parsed with a loader that rejects duplicate mapping keys, which the default loader silently overwrites.
Parsing and validation are delegated to the pure core; this module only reads files and reports I/O errors.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode

from pdm_oee.core.catalog import PlantCatalog, build_catalog
from pdm_oee.core.errors import CatalogValidationError, SemanticFileError
from pdm_oee.core.loss_parser import parse_losses
from pdm_oee.core.metric_parser import parse_measures, parse_metric
from pdm_oee.core.plant_parser import parse_plant
from pdm_oee.core.source_mapping_model import SourceMappings
from pdm_oee.core.source_mapping_parser import parse_source_mappings
from pdm_oee.core.source_mapping_validator import validate_source_mappings

PLANT_FILENAME = "plant.yaml"
LOSSES_FILENAME = "losses.yaml"
MEASURES_FILENAME = "measures.yaml"
METRICS_DIRNAME = "metrics"
METRIC_FILE_PATTERN = "*.yaml"
SOURCE_MAPPINGS_FILENAME = "source_mappings.yaml"
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


def load_catalog(semantic_dir: Path) -> PlantCatalog:
    """Load every catalog file under `semantic_dir` into a validated catalog."""
    metric_files = sorted((semantic_dir / METRICS_DIRNAME).glob(METRIC_FILE_PATTERN))
    if not metric_files:
        raise SemanticFileError(f"No metric files found in {semantic_dir / METRICS_DIRNAME}")
    return build_catalog(
        parse_plant(load_yaml_document(semantic_dir / PLANT_FILENAME)),
        parse_losses(load_yaml_document(semantic_dir / LOSSES_FILENAME)),
        parse_measures(load_yaml_document(semantic_dir / MEASURES_FILENAME)),
        [parse_metric(load_yaml_document(path), path.name) for path in metric_files],
    )


def load_source_mappings(semantic_dir: Path, catalog: PlantCatalog) -> SourceMappings:
    """Load the source mappings and validate them against the catalog."""
    mappings = parse_source_mappings(load_yaml_document(semantic_dir / SOURCE_MAPPINGS_FILENAME))
    issues = validate_source_mappings(mappings, catalog)
    if issues:
        raise CatalogValidationError(tuple(issues))
    return mappings
