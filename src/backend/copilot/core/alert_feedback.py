"""Operator feedback on alerts: a person marks an alert as false, and later alerts on the same asset and failure mode
carry that note. Feedback never hides or closes an alert, because the same machine can still fail later; it asks for
an inspection before money is spent. Everything here is pure and point-in-time.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from copilot.core.errors import FeedbackError

FALSE_ALERT = "false_alert"
MAX_REASON_CHARS = 300
TIME_FORMAT = "%Y-%m-%d %H:%M"
DATE_FORMAT = "%d %b"


@dataclass(frozen=True)
class AlertFeedback:
    """One operator verdict on one alert, given at the demo clock."""

    alert_id: str
    asset_id: str
    failure_mode: str
    verdict: str
    reason: str
    marked_at: datetime


@dataclass(frozen=True)
class FeedbackView:
    """What an alert shows: its own verdicts, earlier verdicts on the same asset and mode, and the resulting note."""

    own: tuple[AlertFeedback, ...]
    similar: tuple[AlertFeedback, ...]
    caution: str | None


def new_false_alert(alert_id: str, asset_id: str, failure_mode: str, raised_at: datetime, reason: str,
                    marked_at: datetime) -> AlertFeedback:
    """A validated false-alert verdict; the reason is required, bounded, and cannot predate the alert."""
    text = " ".join(reason.split())
    if not text:
        raise FeedbackError("Say why the alert is false, for example what the inspection showed.")
    if len(text) > MAX_REASON_CHARS:
        raise FeedbackError(f"Keep the reason under {MAX_REASON_CHARS} characters.")
    if marked_at < raised_at:
        raise FeedbackError(f"Alert {alert_id} was not raised yet at {marked_at.strftime(TIME_FORMAT)}.")
    return AlertFeedback(alert_id, asset_id, failure_mode, FALSE_ALERT, text, marked_at)


def feedback_view(records: list[AlertFeedback], alert_id: str, asset_id: str, failure_mode: str, now: datetime,
                  earlier_alerts: frozenset[str]) -> FeedbackView:
    """Verdicts known at `now`, newest first: this alert's own, and those on earlier alerts of the same asset and mode.

    `earlier_alerts` holds the ids of alerts raised before this one; a verdict on a later alert never reaches back.
    """
    known = sorted((r for r in records if r.marked_at <= now), key=lambda r: r.marked_at, reverse=True)
    own = tuple(r for r in known if r.alert_id == alert_id)
    similar = tuple(r for r in known if r.alert_id in earlier_alerts
                    and r.asset_id == asset_id and r.failure_mode == failure_mode)
    return FeedbackView(own, similar, caution_note(similar))


def caution_note(similar: tuple[AlertFeedback, ...]) -> str | None:
    """A note for people and agents: check before spending, never dismiss."""
    if not similar:
        return None
    latest = similar[0]
    count = "an earlier alert" if len(similar) == 1 else f"{len(similar)} earlier alerts"
    return (f"An operator marked {count} on {latest.asset_id} ({latest.failure_mode.replace('_', ' ')}) as false, "
            f"most recently on {latest.marked_at.strftime(DATE_FORMAT)}: \"{latest.reason.rstrip('.')}\". Confirm with an "
            "inspection before spending on an express option; do not dismiss this alert, because the same machine "
            "can still fail.")


def feedback_row(feedback: AlertFeedback) -> dict[str, object]:
    """A JSON-ready row for the API, the store, and the agent."""
    return {"alert_id": feedback.alert_id, "asset_id": feedback.asset_id, "failure_mode": feedback.failure_mode,
            "verdict": feedback.verdict, "reason": feedback.reason,
            "marked_at": feedback.marked_at.strftime(TIME_FORMAT)}


def feedback_from_row(row: dict[str, object]) -> AlertFeedback:
    return AlertFeedback(str(row["alert_id"]), str(row["asset_id"]), str(row["failure_mode"]), str(row["verdict"]),
                         str(row["reason"]), datetime.strptime(str(row["marked_at"]), TIME_FORMAT))


def view_dict(view: FeedbackView) -> dict[str, object]:
    return {"own": [feedback_row(f) for f in view.own], "similar": [feedback_row(f) for f in view.similar],
            "caution": view.caution}
