"""The OEE service on the small synthetic plant: identities hold on every asset-shift and the stories show.

Conformed tables are loaded into an in-memory DuckDB, as the service would read them from Parquet.
A x P x Q must equal OEE per asset-shift, and the waterfall must reconcile for any filter.
"""
from __future__ import annotations

import numpy as np
import pytest

from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.data_pipeline.duckdb_adapter import DuckDBConnectionManager
from pdm_oee.services.oee_service import OEEService


@pytest.fixture(scope="module")
def service(conformed: dict, catalog: PlantCatalog) -> OEEService:
    database = DuckDBConnectionManager()
    for name, frame in conformed.items():
        database.register_frame(name, frame)
    return OEEService(catalog, database)


def test_factors_multiply_to_oee_everywhere(service: OEEService) -> None:
    rows = service.metrics(["availability", "performance", "quality", "oee"], ["asset_id", "shift_id"])
    rows = rows.dropna()
    assert len(rows) > 1000
    assert np.allclose(rows["availability"] * rows["performance"] * rows["quality"], rows["oee"])


def test_waterfall_reconciles_for_any_filter(service: OEEService) -> None:
    for filters in (None, {"line_id": "US1-L1"}, {"asset_id": "DE1-L2-01"}):
        steps = service.loss_waterfall(filters=filters)
        assert steps["minutes"].iloc[:-1].sum() == pytest.approx(steps["minutes"].iloc[-1], abs=1e-6)


def test_small_stop_conveyor_loses_performance(service: OEEService) -> None:
    rows = service.metrics(["performance"], ["asset_id"]).set_index("asset_id")["performance"]
    conveyors = [a for a in rows.index if a.endswith("-04")]
    assert rows["US1-L1-04"] < min(rows[c] for c in conveyors if c != "US1-L1-04") - 0.1


def test_no_performance_above_one_and_reliability_answers(service: OEEService) -> None:
    assert service.performance_anomalies().empty
    dates = service.measures["shift_date"]
    table = service.reliability(min(dates), max(dates), ["asset_id"])
    assert (table["mtbf"].dropna() > 0).all() and (table["mttr"].dropna() > 0).all()
