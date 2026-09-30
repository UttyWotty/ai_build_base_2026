"""Fixtures for the command center page tests: the small plant's services and temporary outbox, replay, and model files.

The drafts and reports are hand-written, so the page tests know exactly what should appear.
The conform fixtures build the small plant once per session.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.data_pipeline.cmms_outbox import write_outbox
from pdm_oee.data_pipeline.duckdb_adapter import DuckDBConnectionManager
from pdm_oee.services.oee_service import OEEService
from tests.pdm_oee.conform.conftest import conformed, mappings, source_frames

__all__ = ["conformed", "mappings", "source_frames"]
EVIDENCE = [{"sensor": "spindle_vibration", "label": "Spindle vibration", "unit": "mm_per_s", "mean_24h": 3.5,
             "normal_low": 0.4, "normal_high": 2.8}]


def draft(alert_id: str, priority: str) -> dict:
    return {"alert_id": alert_id, "asset_id": "US1-L2-01", "failure_mode": "spindle_bearing_wear", "component": "spindle_bearing",
            "raised_at": "2025-11-10 08:00:00", "score": 0.99, "deadline_at": "2025-11-13 08:00:00", "criticality": "A",
            "priority": priority, "slot_start": None, "slot_end": None, "planned_slot": False, "repair_hours": 10.0,
            "recommended_action": "Replace the spindle bearing set.", "outcome": "new_draft", "attached_wo_id": None, "evidence": EVIDENCE}


@pytest.fixture(scope="session")
def small_oee(conformed: dict, catalog: PlantCatalog) -> OEEService:
    database = DuckDBConnectionManager()
    for name, frame in conformed.items():
        database.register_frame(name, frame)
    return OEEService(catalog, database)


@pytest.fixture
def files(tmp_path: Path) -> dict[str, Path]:
    outbox = write_outbox([draft("AL-1", "P1"), draft("AL-2", "P3")], tmp_path / "outbox.json")
    replay = tmp_path / "replay.json"
    lift = {"oee_before": 0.80, "oee_after": 0.81, "availability_before": 0.90, "availability_after": 0.91,
            "recovered_minutes": 600.0, "inspection_minutes": 60.0, "assumptions": ["A stated assumption."]}
    replay.write_text(json.dumps({"alerts": [], "lift": lift}), encoding="utf-8")
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    result = {"caught_failures": 3, "evaluable_failures": 4, "false_alerts_per_asset_month": 0.2, "late_alerts": 1, "median_lead_hours": 70.0}
    report = {"blocks": {"fit": "a", "validation": "b", "test": "c"}, "test": {"model": result, "baseline": result}}
    (model_dir / "failure_model.json").write_text(json.dumps(report), encoding="utf-8")
    return {"outbox": outbox, "replay": replay, "models": model_dir}
