"""The real command center page, run headless with the small plant, temporary files, and a scripted model.

Covers the first render (every tab, no model call), approving a draft, and asking a question end to end.
AppTest runs the page in-process, so no server is started.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from streamlit.testing.v1 import AppTest

from pdm_oee.core.catalog import PlantCatalog
from pdm_oee.data_pipeline.cmms_outbox import read_outbox
from pdm_oee.services.investigation_tools import ToolBox
from pdm_oee.services.oee_service import OEEService
from pdm_oee.ui import resources as keys
from tests.pdm_oee.investigation.scripted_model import ScriptedModel

APP_PATH = Path(__file__).resolve().parents[3] / "src" / "backend" / "pdm_oee" / "ui" / "app.py"
TIMEOUT_SECONDS = 120


def start(catalog: PlantCatalog, oee: OEEService, files: dict, replies: list[str]) -> tuple[AppTest, ScriptedModel]:
    model = ScriptedModel(replies)
    page = AppTest.from_file(str(APP_PATH), default_timeout=TIMEOUT_SECONDS)
    page.session_state[keys.CATALOG_KEY] = catalog
    page.session_state[keys.OEE_KEY] = oee
    page.session_state[keys.TOOLBOX_KEY] = ToolBox(catalog, oee, [])
    page.session_state[keys.OUTBOX_KEY] = files["outbox"]
    page.session_state[keys.REPLAY_KEY] = files["replay"]
    page.session_state[keys.MODEL_DIR_KEY] = files["models"]
    page.session_state[keys.LLM_CLIENT_KEY] = model
    return page.run(), model


def test_first_render_shows_every_tab_without_calling_the_model(catalog: PlantCatalog, small_oee: OEEService, files: dict) -> None:
    page, model = start(catalog, small_oee, files, [])
    assert not page.exception
    assert [t.label for t in page.tabs] == ["Alert queue", "Asset health", "OEE and losses", "Ask", "Prediction model"]
    metrics = {m.label: m.value for m in page.metric}
    assert metrics["Waiting"] == "2" and metrics["P1"] == "1" and metrics["OEE, test period"] == "81.0%"
    assert page.expander[0].label.startswith("P1  US1-L2-01  Spindle bearing wear")
    assert model.calls == []


def test_approving_a_draft_updates_the_outbox(catalog: PlantCatalog, small_oee: OEEService, files: dict) -> None:
    page, _ = start(catalog, small_oee, files, [])
    next(b for b in page.button if b.key == "approve-AL-1").click().run()
    assert not page.exception
    assert {d["alert_id"]: d["status"] for d in read_outbox(files["outbox"])} == {"AL-1": "approved", "AL-2": "draft"}


def test_asking_shows_a_verified_answer_and_its_tool_calls(catalog: PlantCatalog, small_oee: OEEService, files: dict) -> None:
    tools = ToolBox(catalog, small_oee, [])
    oee = tools.oee_summary("plant", "plant", date(2025, 10, 1), date(2025, 12, 1))["oee"]
    call = {"action": "call", "tool": "oee_summary", "arguments": {"scope_type": "plant", "scope_id": "plant",
                                                                   "start": "2025-10-01", "end": "2025-12-01"}}
    answer = {"action": "answer", "text": f"Plant OEE was {oee * 100:.1f}%."}
    page, model = start(catalog, small_oee, files, [json.dumps(call), json.dumps(answer)])
    page.text_input[0].input("What was plant OEE in October and November 2025?")
    page.button[-1].click().run()
    assert not page.exception and len(model.calls) == 2
    assert any("Every number in this answer comes from a tool result." in s.value for s in page.success)
    assert any(e.label.startswith("oee_summary(") for e in page.expander)
