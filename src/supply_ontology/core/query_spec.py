"""The structured query spec: which metrics, sliced by which dimensions, filtered how, over which time range and grain.

This is the only thing the natural-language layer produces; the compiler turns it into SQL deterministically.
Dimensions are always written entity.attribute, so a spec is readable and cannot name raw source columns.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from supply_ontology.core.enums import FilterOperator, TimeGrain
from supply_ontology.core.metric_model import FilterValue

DIMENSION_SEPARATOR = "."
ALIAS_SEPARATOR = "__"


@dataclass(frozen=True)
class DimensionRef:
    """An attribute of an ontology entity used to group or filter."""

    entity: str
    attribute: str

    @property
    def name(self) -> str:
        """entity.attribute form used in specs and prompts."""
        return f"{self.entity}{DIMENSION_SEPARATOR}{self.attribute}"

    @property
    def alias(self) -> str:
        """Column alias used in compiled SQL and result frames."""
        return f"{self.entity}{ALIAS_SEPARATOR}{self.attribute}"


@dataclass(frozen=True)
class QueryFilter:
    """A user-chosen filter on a dimension."""

    dimension: DimensionRef
    operator: FilterOperator
    values: tuple[FilterValue, ...]


@dataclass(frozen=True)
class TimeRange:
    """Inclusive date range applied to each metric's own time dimension."""

    start: date
    end: date


@dataclass(frozen=True)
class QuerySpec:
    """A complete, catalog-bound query request."""

    metrics: tuple[str, ...]
    dimensions: tuple[DimensionRef, ...]
    filters: tuple[QueryFilter, ...]
    time_range: TimeRange | None
    time_grain: TimeGrain | None

    def to_dict(self) -> dict[str, object]:
        """Canonical JSON-ready form, used for display and for the spec parser round trip."""
        return {
            "metrics": list(self.metrics),
            "dimensions": [d.name for d in self.dimensions],
            "filters": [
                {"dimension": f.dimension.name, "operator": f.operator.value, "value": list(f.values)}
                for f in self.filters
            ],
            "time_range": None if self.time_range is None else {
                "start": self.time_range.start.isoformat(), "end": self.time_range.end.isoformat()
            },
            "time_grain": None if self.time_grain is None else self.time_grain.value,
        }
