"""The conform pipeline must reconstruct every truth table exactly from the rendered sources.

Each ontology entity is checked separately so a failure names the entity and column that drifted.
Derived attributes are checked for internal consistency with statuses and quantities.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from supply_ontology.data_pipeline.conform.pipeline import conform_sources
from supply_ontology.data_pipeline.semantic_files import load_catalog
from supply_ontology.data_pipeline.synthetic.sources import render_sources
from supply_ontology.data_pipeline.synthetic.world import World

SEMANTIC_DIR = Path(__file__).resolve().parents[3] / "semantic" / "supply"
CATALOG = load_catalog(SEMANTIC_DIR)
TRAILING_WINDOW_DAYS = int(CATALOG.metrics["days_of_inventory"].parameters["trailing_window_days"])


@pytest.fixture(scope="module")
def conformed(small_world: World) -> dict[str, pd.DataFrame]:
    sources = {s.relative_path: s.frame for s in render_sources(small_world)}
    return conform_sources(sources, CATALOG.ontology, TRAILING_WINDOW_DAYS)


@pytest.mark.parametrize("entity", sorted(CATALOG.ontology.entities))
def test_entity_matches_truth(entity: str, conformed: dict[str, pd.DataFrame], small_world: World) -> None:
    truth = small_world.tables[entity]
    key = list(CATALOG.ontology.entities[entity].key)
    actual = conformed[entity][list(truth.columns)].sort_values(key).reset_index(drop=True)
    expected = truth.sort_values(key).reset_index(drop=True)
    pd.testing.assert_frame_equal(actual, expected, check_dtype=False, rtol=1e-9)


def test_columns_follow_ontology_order(conformed: dict[str, pd.DataFrame]) -> None:
    for name, entity in CATALOG.ontology.entities.items():
        assert list(conformed[name].columns) == list(entity.attributes), name


def test_closed_lines_are_complete(conformed: dict[str, pd.DataFrame]) -> None:
    po = conformed["purchase_order_line"]
    closed = po[po["status"] == "closed"]
    assert (closed["qty_received"] == closed["qty_ordered"]).all()
    assert closed["last_receipt_date"].notna().all()
    assert not po[po["status"] == "open"]["last_receipt_date"].notna().any()


def test_landed_cost_is_the_sum_of_its_parts(conformed: dict[str, pd.DataFrame]) -> None:
    receipt = conformed["receipt"]
    parts = receipt["goods_value_usd"] + receipt["freight_allocated_usd"] + receipt["duty_usd"]
    assert (receipt["landed_cost_usd"] - parts).abs().max() < 1e-9
    freight = receipt.groupby("inbound_shipment_id")["freight_allocated_usd"].sum()
    shipment_freight = conformed["shipment"].set_index("shipment_id").loc[freight.index, "freight_cost_usd"]
    assert (freight - shipment_freight).abs().max() < 1e-6


def test_on_time_flags_never_true_without_completion(conformed: dict[str, pd.DataFrame]) -> None:
    lines = conformed["sales_order_line"]
    assert not (lines["is_delivered_complete_by_committed"] & lines["last_delivery_date"].isna()).any()
    assert (lines["qty_on_first_shipment"] <= lines["qty_ordered"]).all()
