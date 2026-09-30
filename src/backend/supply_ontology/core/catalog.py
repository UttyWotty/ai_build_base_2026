"""The validated semantic catalog: one ontology plus the metrics defined over it.

Building the catalog runs every ontology, metric, and vocabulary check and refuses to produce a catalog if any issue exists.
Downstream code can therefore assume every reference inside a SemanticCatalog is resolvable.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from supply_ontology.core.errors import CatalogValidationError
from supply_ontology.core.metric_model import Metric
from supply_ontology.core.metric_validator import validate_metrics
from supply_ontology.core.ontology_model import Ontology
from supply_ontology.core.ontology_validator import validate_ontology
from supply_ontology.core.vocabulary_model import Vocabulary
from supply_ontology.core.vocabulary_validator import validate_vocabulary


@dataclass(frozen=True)
class SemanticCatalog:
    """A consistent ontology and its governed metrics, keyed by metric id."""

    ontology: Ontology
    metrics: Mapping[str, Metric]
    vocabulary: Vocabulary

    def metric(self, metric_id: str) -> Metric | None:
        """Return the metric with this id, or None when it is not defined."""
        return self.metrics.get(metric_id)


def build_catalog(ontology: Ontology, metrics: Sequence[Metric], vocabulary: Vocabulary) -> SemanticCatalog:
    """Validate everything and return the catalog, or raise CatalogValidationError listing all issues."""
    issues = [
        *validate_ontology(ontology),
        *validate_metrics(metrics, ontology),
        *validate_vocabulary(vocabulary, ontology, metrics),
    ]
    if issues:
        raise CatalogValidationError(tuple(issues))
    return SemanticCatalog(ontology=ontology, metrics={metric.id: metric for metric in metrics}, vocabulary=vocabulary)
