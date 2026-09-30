"""What the command center needs beyond the analytic services: the governed catalog, drafts, the replay, and the model report.

The UI calls these functions instead of reaching the file adapters directly. Paths default to services.settings and can be
passed explicitly, which is how tests point the UI at temporary files.
"""
from __future__ import annotations

from pathlib import Path

from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.data_pipeline.cmms_outbox import read_outbox, set_status
from pdm_oee.data_pipeline.llm_client import LLMClient, build_llm_client
from pdm_oee.data_pipeline.replay_store import read_replay_alerts
from pdm_oee.data_pipeline.semantic_files import load_catalog, load_yaml_document
from pdm_oee.services.settings import (
    MODEL_DIR,
    OUTBOX_PATH,
    REPLAY_PATH,
    SEMANTIC_DIR,
)

__all__ = ["LLMClient", "default_llm_client", "draft_orders", "load_default_catalog", "model_report", "replay_alerts",
           "replay_lift", "update_draft"]
REPORT_FILENAME = "failure_model.json"
LIFT_KEY = "lift"


def load_default_catalog() -> PlantCatalog:
    return load_catalog(SEMANTIC_DIR)


def default_llm_client() -> LLMClient:
    """The configured model (Gemini or local); nothing is sent until a question is asked."""
    return build_llm_client()


def draft_orders(path: Path = OUTBOX_PATH) -> list[dict[str, object]]:
    return read_outbox(path)


def update_draft(alert_id: str, status: str, path: Path = OUTBOX_PATH) -> dict[str, object]:
    return set_status(path, alert_id, status)


def replay_alerts(path: Path = REPLAY_PATH) -> list[dict[str, object]]:
    return read_replay_alerts(path)


def replay_lift(path: Path = REPLAY_PATH) -> dict[str, object] | None:
    if not path.exists():
        return None
    document = load_yaml_document(path)
    return document.get(LIFT_KEY) if isinstance(document, dict) else None


def model_report(model_dir: Path = MODEL_DIR) -> dict[str, object] | None:
    path = model_dir / REPORT_FILENAME
    document = load_yaml_document(path) if path.exists() else None
    return document if isinstance(document, dict) else None
