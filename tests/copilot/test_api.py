"""Tests for the HTTP API with a fake services bundle and a scripted agent stream.

They cover the health check staying light, the overview headline, 404 for unknown alerts, the approval flow, and the
server-sent events of an agent run. No data, no model, and no network are involved.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from copilot.api import server
from copilot.api.endpoints import agent as agent_endpoint
from copilot.api.static_site import mount_frontend
from copilot.core.value_backtest import case_value, summarise
from copilot.data_pipeline.proposal_store import ProposalStore
from copilot.services.agent_runner import AgentRun, AgentStep
from tests.copilot.fixtures import T0
from tests.copilot.test_presenters import IMPACT
from tests.copilot.test_value_backtest import report as value_report

ALERT = {"alert_id": "AL-2", "asset_id": "US1-L2-01", "line_id": "US1-L2", "failure_mode": "spindle_bearing_wear",
         "raised_at": "2026-07-25 02:00", "repair_deadline": "2026-07-28 02:00", "priority": "P2"}


class FakeTools:
    def __init__(self, as_of: datetime) -> None:
        self.as_of = as_of

    def safe(self, method):
        def call(*args):
            try:
                return method(*args)
            except KeyError as error:
                return {"error": f"Unknown alert {error}"}
        return call

    def list_open_alerts(self) -> dict:
        return {"as_of": self.as_of.strftime("%Y-%m-%d %H:%M"), "count": 1, "alerts": [ALERT]}

    def analyse_alert_impact(self, alert_id: str) -> dict:
        if alert_id != "AL-2":
            raise KeyError(alert_id)
        return IMPACT

    def get_sensor_evidence(self, alert_id: str) -> dict:
        return {"alert_id": alert_id, "sensors": []}


class FakeValue:
    def track_record(self):
        case = case_value(value_report(), T0 + timedelta(hours=30))
        return [case], summarise([case])


class FakeOutcomes:
    def outcomes(self, now):
        return []


class FakeServices:
    def __init__(self, proposals: ProposalStore) -> None:
        self.proposals = proposals
        self.value = FakeValue()
        self.outcomes = FakeOutcomes()

    def tools_at(self, as_of: datetime) -> FakeTools:
        return FakeTools(as_of)


@pytest.fixture()
def client(tmp_path: Path):
    store = ProposalStore(tmp_path / "proposals.json")
    store._write([{"proposal_id": "PR-AL-2-1", "alert_id": "AL-2", "status": "pending"}])
    with TestClient(server.create_app(lambda: FakeServices(store), tmp_path / "no-build")) as test_client:
        yield test_client


def test_health_is_light_and_engine_status_reports_readiness(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    status = client.get("/api/engine-status").json()
    assert status["ready"] is True and status["provider"] in {"gemini", "local"}


def test_overview_carries_the_headline_and_each_alerts_recommendation(client: TestClient) -> None:
    body = client.get("/api/overview", params={"as_of": "2026-07-25T02:00"}).json()
    assert body["headline"] == {"open_alerts": 1, "alerts_in_spare_conflict": 1, "downtime_avoided_hours": 180.3,
                                "cost_avoided_usd": 93175.0}
    assert body["alerts"][0]["recommended"]["kind"] == "transfer" and body["alerts"][0]["conflict"]
    assert client.get("/api/scenarios").json()["scenarios"][0]["id"] == "bearing-squeeze"


def test_unknown_alerts_and_bad_clocks_are_client_errors(client: TestClient) -> None:
    assert client.get("/api/alerts/NOPE/impact").status_code == 404
    assert client.get("/api/overview", params={"as_of": "yesterday"}).status_code == 400


def test_a_person_approves_a_proposal(client: TestClient) -> None:
    assert client.get("/api/proposals").json()["proposals"][0]["status"] == "pending"
    assert client.post("/api/proposals/PR-AL-2-1/status", json={"status": "approved"}).json()["status"] == "approved"
    assert client.post("/api/proposals/PR-AL-2-1/status", json={"status": "done"}).status_code == 400


def test_agent_run_streams_steps_then_the_checked_answer(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    modes = []

    async def scripted(question, tools, selection, mode):
        modes.append(mode)
        yield AgentStep("tool_call", "list_open_alerts", {})
        yield AgentStep("tool_result", "list_open_alerts", {"count": 1})
        yield AgentRun(question, tools.as_of, "scripted", (), "1 alert is open.", (), 0.1)

    monkeypatch.setattr(agent_endpoint, "stream_copilot", scripted)
    response = client.post("/api/agent/stream", json={"question": "How many?", "as_of": "2026-07-25T02:00"})
    events = [json.loads(line[len("data: "):]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert [e["type"] for e in events] == ["tool_call", "tool_result", "done"]
    assert events[-1]["verified"] is True and events[-1]["answer"] == "1 alert is open."
    client.post("/api/agent/stream", json={"question": "Plan it", "mode": "team"})
    assert modes == ["single", "team"]
    assert client.post("/api/agent/stream", json={"question": "x", "mode": "crowd"}).status_code == 400


def test_the_built_frontend_is_served_with_client_side_routes(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<div id=root></div>")
    (dist / "assets" / "app.js").write_text("console.log(1)")
    (dist / "favicon.svg").write_text("<svg/>")
    app = server.create_app(lambda: FakeServices(ProposalStore(tmp_path / "p.json")), dist)
    assert not mount_frontend(server.create_app(frontend_dir=tmp_path / "none"), tmp_path / "none")
    with TestClient(app) as test_client:
        assert test_client.get("/approvals").text == "<div id=root></div>"
        assert test_client.get("/assets/app.js").text == "console.log(1)"
        assert test_client.get("/favicon.svg").text == "<svg/>"
        assert test_client.get("/api/unknown").status_code == 404
        assert test_client.get("/health").json() == {"status": "ok"}


def test_track_record_reports_the_net_value_and_the_method(client: TestClient) -> None:
    body = client.get("/api/value").json()
    assert body["summary"]["real_failures"] == 1 and body["summary"]["hours_saved"] == 144.0
    assert body["cases"][0]["recommended_kind"] == "transfer" and len(body["method"]) == 4


def test_outcomes_and_reset(client: TestClient) -> None:
    assert client.get("/api/proposals/outcomes", params={"as_of": "2026-07-26T12:00"}).json() == {"outcomes": []}
    assert client.post("/api/proposals/reset").json() == {"removed": 1}
    assert client.get("/api/proposals").json()["proposals"] == []
