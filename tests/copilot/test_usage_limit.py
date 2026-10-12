"""Tests for the public demo's usage limit: sliding-window caps per visitor and in total, and how the API refuses.

A refused call is not counted, a window frees its oldest call, and a cap of 0 is off. The agent stream refuses with
one finished event of kind "limit", so pages and the autopilot treat it as an error; photo uploads get 429.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from copilot.api import server
from copilot.core.usage_limit import (
    OFF,
    TOTAL,
    VISITOR,
    UsageLimiter,
    UsageLimits,
    limit_message,
)

T0 = datetime(2026, 10, 12, 9, 0)
HOUR = timedelta(hours=1)


def test_the_visitor_cap_frees_up_as_the_window_slides() -> None:
    limiter = UsageLimiter(UsageLimits(per_visitor=2, total=10, window=HOUR))
    assert limiter.check("a", T0).allowed and limiter.check("a", T0 + timedelta(minutes=10)).allowed
    refused = limiter.check("a", T0 + timedelta(minutes=20))
    assert not refused.allowed and refused.scope == VISITOR and refused.retry_after_seconds == 40 * 60
    assert limiter.check("b", T0 + timedelta(minutes=20)).allowed
    assert limiter.check("a", T0 + HOUR + timedelta(seconds=1)).allowed


def test_the_total_cap_holds_across_visitors_and_refusals_are_not_counted() -> None:
    limiter = UsageLimiter(UsageLimits(per_visitor=OFF, total=2, window=HOUR))
    assert limiter.check("a", T0).allowed and limiter.check("b", T0).allowed
    assert [limiter.check("c", T0).scope for _ in range(3)] == [TOTAL, TOTAL, TOTAL]
    assert limiter.check("c", T0 + HOUR + timedelta(seconds=1)).allowed


def test_caps_of_zero_are_off() -> None:
    limiter = UsageLimiter(UsageLimits(per_visitor=OFF, total=OFF, window=HOUR))
    assert all(limiter.check("a", T0).allowed for _ in range(100))


def test_messages_say_which_cap_and_how_long_to_wait() -> None:
    limits = UsageLimits(per_visitor=10, total=60, window=HOUR)
    limiter = UsageLimiter(UsageLimits(per_visitor=1, total=60, window=HOUR))
    limiter.check("a", T0)
    visitor = limit_message(limiter.check("a", T0 + timedelta(minutes=30, seconds=10)), limits)
    assert "10 AI runs per visitor per 60 minutes" in visitor and "about 30 minutes" in visitor
    full = UsageLimiter(UsageLimits(OFF, 1, HOUR))
    full.check("a", T0)
    total = limit_message(full.check("b", T0), limits)
    assert "limit of 60 AI runs per 60 minutes" in total and "about 60 minutes" in total


class NoServices:
    pass


def app_with(tmp_path: Path, limits: UsageLimits) -> TestClient:
    return TestClient(server.create_app(lambda: NoServices(), tmp_path / "no-build", UsageLimiter(limits)))


def test_the_agent_stream_refuses_with_one_finished_limit_event(tmp_path: Path, monkeypatch) -> None:
    from copilot.api.endpoints import agent as agent_endpoint
    monkeypatch.setattr(agent_endpoint, "tools_at", lambda request, as_of: None)
    with app_with(tmp_path, UsageLimits(per_visitor=OFF, total=OFF, window=HOUR)) as open_client:
        assert open_client.post("/api/agent/stream", json={"question": "q", "mode": "nope"}).status_code == 400
    with app_with(tmp_path, UsageLimits(per_visitor=0, total=1, window=HOUR)) as client:
        client.app.state.limiter.check("someone-else", datetime.now(timezone.utc))
        body = client.post("/api/agent/stream", json={"question": "Which alerts?"}).text
        events = [json.loads(line[6:]) for line in body.splitlines() if line.startswith("data: ")]
        assert len(events) == 1 and events[0]["type"] == "done" and events[0]["error_kind"] == "limit"
        assert "limit of 1 AI runs" in events[0]["error_message"]


def test_photo_inspections_get_429_with_retry_after(tmp_path: Path) -> None:
    with app_with(tmp_path, UsageLimits(per_visitor=1, total=OFF, window=HOUR)) as client:
        client.app.state.limiter.check("testclient", datetime.now(timezone.utc))
        response = client.post("/api/alerts/AL-1/inspection", json={"mime_type": "image/jpeg", "data_base64": ""},
                               headers={"x-forwarded-for": "testclient, 10.0.0.1"})
        assert response.status_code == 429 and int(response.headers["retry-after"]) > 0
        assert "per visitor" in response.json()["detail"]
