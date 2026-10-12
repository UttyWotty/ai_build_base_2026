"""Tests for operator feedback: validated false-alert verdicts, point-in-time views, and the caution note.

A verdict needs a reason, stays bounded, and cannot predate its alert. Earlier verdicts on the same asset and failure
mode reach later alerts as a caution that never dismisses them; the service and the API keep them in a JSON file.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from copilot.api import server
from copilot.core.alert_feedback import (
    FALSE_ALERT,
    MAX_REASON_CHARS,
    feedback_from_row,
    feedback_row,
    feedback_view,
    new_false_alert,
)
from copilot.core.errors import FeedbackError
from copilot.data_pipeline.record_store import RecordStore
from copilot.services.alert_book import AlertBook
from copilot.services.feedback_service import FeedbackService
from tests.copilot.fixtures import T0

ASSET, MODE = "DE1-L2-04", "gearbox_wear"
RAW_ALERTS = [
    {"alert_id": "AL-1", "asset_id": ASSET, "failure_mode": MODE, "component": "gearbox", "raised_at": "2026-07-20 10:00",
     "deadline_at": "2026-07-25 10:00", "repair_hours": 8, "planned_slot": True, "priority": "P2", "failure_at": ""},
    {"alert_id": "AL-2", "asset_id": ASSET, "failure_mode": MODE, "component": "gearbox", "raised_at": "2026-09-17 04:00",
     "deadline_at": "2026-09-20 04:00", "repair_hours": 8, "planned_slot": True, "priority": "P2", "failure_at": ""},
]


def verdict(alert_id: str, marked: datetime, asset: str = ASSET, mode: str = MODE, reason: str = "Oil was dirty."):
    return new_false_alert(alert_id, asset, mode, marked - timedelta(hours=1), reason, marked)


def test_a_verdict_needs_a_bounded_reason_and_cannot_predate_its_alert() -> None:
    feedback = new_false_alert("AL-1", ASSET, MODE, T0, "  Teeth   intact,\n oil dark. ", T0)
    assert feedback.verdict == FALSE_ALERT and feedback.reason == "Teeth intact, oil dark."
    with pytest.raises(FeedbackError, match="why"):
        new_false_alert("AL-1", ASSET, MODE, T0, "   ", T0)
    with pytest.raises(FeedbackError, match=str(MAX_REASON_CHARS)):
        new_false_alert("AL-1", ASSET, MODE, T0, "x" * (MAX_REASON_CHARS + 1), T0)
    with pytest.raises(FeedbackError, match="not raised yet"):
        new_false_alert("AL-1", ASSET, MODE, T0, "early", T0 - timedelta(minutes=1))


def test_the_view_is_point_in_time_and_matches_asset_and_mode() -> None:
    records = [verdict("AL-1", T0), verdict("AL-9", T0 + timedelta(days=1)),
               verdict("AL-7", T0, asset="US1-L3-02"), verdict("AL-8", T0, mode="main_seal_leak")]
    earlier = frozenset({"AL-1", "AL-7", "AL-8", "AL-9"})
    later = feedback_view(records, "AL-2", ASSET, MODE, T0 + timedelta(days=2), earlier)
    assert [f.alert_id for f in later.similar] == ["AL-9", "AL-1"] and later.own == ()
    before = feedback_view(records, "AL-2", ASSET, MODE, T0 - timedelta(hours=1), earlier)
    assert before.similar == () and before.caution is None
    own = feedback_view(records, "AL-1", ASSET, MODE, T0, frozenset())
    assert [f.alert_id for f in own.own] == ["AL-1"] and own.similar == () and own.caution is None


def test_a_verdict_on_a_later_alert_never_reaches_back() -> None:
    records = [verdict("AL-9", T0)]
    view = feedback_view(records, "AL-2", ASSET, MODE, T0 + timedelta(days=1), frozenset({"AL-1"}))
    assert view.similar == () and view.caution is None


def test_the_caution_asks_for_an_inspection_and_never_dismisses() -> None:
    view = feedback_view([verdict("AL-1", T0)], "AL-2", ASSET, MODE, T0 + timedelta(days=60), frozenset({"AL-1"}))
    assert view.caution is not None
    assert "an earlier alert on DE1-L2-04 (gearbox wear)" in view.caution and "25 Jul" in view.caution
    assert "inspection" in view.caution and "do not dismiss" in view.caution
    assert '"Oil was dirty". Confirm' in view.caution
    two = feedback_view([verdict("AL-1", T0), verdict("AL-3", T0)], "AL-2", ASSET, MODE, T0, frozenset({"AL-1", "AL-3"}))
    assert "2 earlier alerts" in str(two.caution)


def test_rows_round_trip() -> None:
    feedback = verdict("AL-1", T0)
    assert feedback_from_row(feedback_row(feedback)) == feedback


def test_the_service_keeps_verdicts_and_shows_them_to_later_alerts(tmp_path: Path) -> None:
    service = FeedbackService(AlertBook(RAW_ALERTS), RecordStore(tmp_path / "feedback.json"))
    service.mark_false("AL-1", "Gear teeth intact; the oil needed flushing.", datetime(2026, 7, 25, 2, 0))
    view = service.view("AL-2", datetime(2026, 9, 17, 4, 0))
    assert [f.alert_id for f in view.similar] == ["AL-1"] and "flushing" in str(view.caution)
    service.mark_false("AL-2", "Bearing sounded fine.", datetime(2026, 9, 17, 4, 0))
    assert service.view("AL-1", datetime(2026, 9, 18, 0, 0)).similar == ()
    assert service.clear() == 2 and service.view("AL-2", datetime(2026, 9, 17, 4, 0)).similar == ()


class FeedbackOnlyServices:
    def __init__(self, feedback: FeedbackService) -> None:
        self.feedback = feedback


def test_the_api_marks_and_reads_feedback(tmp_path: Path) -> None:
    service = FeedbackService(AlertBook(RAW_ALERTS), RecordStore(tmp_path / "feedback.json"))
    app = server.create_app(lambda: FeedbackOnlyServices(service), tmp_path / "no-build")
    with TestClient(app) as client:
        marked = client.post("/api/alerts/AL-1/feedback", json={"reason": "Teeth intact.", "as_of": "2026-07-25T02:00"})
        assert marked.status_code == 200 and marked.json()["verdict"] == FALSE_ALERT
        later = client.get("/api/alerts/AL-2/feedback", params={"as_of": "2026-09-17T04:00"}).json()
        assert later["similar"][0]["reason"] == "Teeth intact." and "inspection" in later["caution"]
        assert client.post("/api/alerts/AL-1/feedback", json={"reason": " ", "as_of": "2026-07-25T02:00"}).status_code == 400
        assert client.post("/api/alerts/AL-1/feedback", json={"reason": "x", "as_of": "2026-07-01T00:00"}).status_code == 400
        assert client.get("/api/alerts/AL-404/feedback").status_code == 404
