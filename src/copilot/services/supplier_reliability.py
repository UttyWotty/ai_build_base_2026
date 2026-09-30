"""Assesses a supplier's recent delivery record at a point in time, using the governed supplier_otd metric.

The on-time share comes from the supply package's metric compiler, so it is the same number procurement sees,
with the SQL fingerprint to prove it. The expected lateness in days is computed over the same window.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from copilot.core.impact_model import SupplierReliability
from copilot.data_pipeline.impact_queries import expected_days_late, supplier_name
from copilot.data_pipeline.world_store import WorldStore
from supply_ontology.core.enums import FilterOperator
from supply_ontology.core.query_spec import (
    DimensionRef,
    QueryFilter,
    QuerySpec,
    TimeRange,
)
from supply_ontology.services.query_service import QueryService

WINDOW_DAYS = 90
METRIC_ID = "supplier_otd"
SUPPLIER_DIMENSION = DimensionRef("supplier", "supplier_id")


class SupplierReliabilityService:
    """Supplier on-time share and lateness over the window before a given time."""

    def __init__(self, query_service: QueryService, connection_manager: WorldStore) -> None:
        self.query_service = query_service
        self.connection_manager = connection_manager

    def assess(self, supplier_id: str, as_of: datetime) -> SupplierReliability:
        end = as_of.date() - timedelta(days=1)
        start = end - timedelta(days=WINDOW_DAYS - 1)
        spec = QuerySpec((METRIC_ID,), (), (QueryFilter(SUPPLIER_DIMENSION, FilterOperator.EQUALS, (supplier_id,)),),
                         TimeRange(start, end), None)
        result = self.query_service.run(spec)
        value = result.frame[METRIC_ID].iloc[0] if not result.frame.empty else None
        share = None if value is None or value != value else float(value)
        return SupplierReliability(supplier_id, supplier_name(self.connection_manager, supplier_id), share,
                                   round(expected_days_late(self.connection_manager, supplier_id, start, end), 1),
                                   start, end, result.compiled.fingerprint)
