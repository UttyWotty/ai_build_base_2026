"""The validated governed catalog: the plant model, the loss taxonomy, and the measures and metrics.

Building the catalog runs every check and refuses to produce a catalog if any issue exists.
Downstream code can therefore assume every reference inside a PlantCatalog resolves.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from pdm_oee.core.errors import CatalogValidationError
from pdm_oee.core.loss_model import LossTaxonomy
from pdm_oee.core.loss_validator import validate_losses
from pdm_oee.core.metric_model import Measure, Metric
from pdm_oee.core.metric_validator import validate_metrics
from pdm_oee.core.plant_model import PlantModel
from pdm_oee.core.plant_validator import validate_plant


@dataclass(frozen=True)
class PlantCatalog:
    """Everything governed, validated together."""

    plant: PlantModel
    losses: LossTaxonomy
    measures: Mapping[str, Measure]
    metrics: Mapping[str, Metric]

    def metric(self, metric_id: str) -> Metric | None:
        """Return the metric with this id, or None when it is not defined."""
        return self.metrics.get(metric_id)


def build_catalog(
    plant: PlantModel, losses: LossTaxonomy, measures: Mapping[str, Measure], metrics: Sequence[Metric],
) -> PlantCatalog:
    """Validate everything and return the catalog, or raise CatalogValidationError listing all issues."""
    issues = [*validate_plant(plant), *validate_losses(losses), *validate_metrics(measures, metrics)]
    if issues:
        raise CatalogValidationError(tuple(issues))
    return PlantCatalog(plant=plant, losses=losses, measures=dict(measures), metrics={m.id: m for m in metrics})
