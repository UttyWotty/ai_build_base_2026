"""Pure UI formatting: metric values, definitions, result tables, clarification follow-ups, and the catalog table.

Definitions must match the catalog field by field, because the UI's job is to show which definition answered.
Values follow each metric's declared format.
"""
from __future__ import annotations

import pandas as pd

from supply_ontology.core.enums import MetricFormat
from supply_ontology.ui.presenters import (
    MISSING_VALUE,
    catalog_table,
    clarification_followup,
    display_frame,
    format_value,
    metric_definition,
)
from tests.supply_ontology.nl.conftest import CATALOG


def test_values_follow_the_metric_format() -> None:
    assert format_value(0.7843, MetricFormat.PERCENT) == "78.4%"
    assert format_value(1234.5, MetricFormat.CURRENCY_USD) == "$1,234.50"
    assert format_value(23.46, MetricFormat.DAYS) == "23.5 days"
    assert format_value(None, MetricFormat.PERCENT) == MISSING_VALUE
    assert format_value(float("nan"), MetricFormat.DAYS) == MISSING_VALUE


def test_definition_states_the_governing_rules() -> None:
    definition = metric_definition(CATALOG.metrics["otd"])
    assert definition["Time attribution"] == "committed_date"
    assert definition["Formula"] == "count_if(is_delivered_complete_by_committed) / count(*)"
    assert "cancelled" in definition["Fixed filters"]
    assert "supplier_otd" in definition["Not to be confused with"]


def test_display_frame_keeps_keys_and_formats_metrics() -> None:
    frame = pd.DataFrame({"plant_plant_id": ["US01", "DE01"], "otd": [0.8, None], "otd_numerator": [8, 0]})
    shown = display_frame(frame, ("plant_plant_id",), {"otd": CATALOG.metrics["otd"]})
    assert list(shown.columns) == ["plant_plant_id", CATALOG.metrics["otd"].label]
    assert shown.iloc[:, 1].tolist() == ["80.0%", MISSING_VALUE]


def test_clarification_followup_binds_the_chosen_metric() -> None:
    assert clarification_followup("How are we doing on time?", "supplier_otd") == "How are we doing on time? (supplier_otd)"


def test_catalog_table_lists_every_metric_once() -> None:
    table = catalog_table(CATALOG)
    assert sorted(table["Metric"]) == sorted(CATALOG.metrics)
