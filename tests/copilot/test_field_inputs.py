"""Tests for field inputs: strict validation of Gemini's replies, the delivery-date revision, and the sample loader.

A reply outside the schema is rejected; a supplier's new date revises only its own order and only once received.
Sample messages take their received time from the Date header.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from copilot.core.field_inputs import (
    FieldInputError,
    SupplierUpdate,
    parse_inspection,
    parse_supplier_update,
    revise_expected,
)
from copilot.core.impact_model import OpenOrder
from copilot.data_pipeline.field_samples import (
    photo_path,
    sample_messages,
    sample_photos,
)
from tests.copilot.fixtures import T0

ORDER = OpenOrder("SPO-US1-0061", "V10001", 1, datetime(2026, 8, 2, 14, 18), datetime(2026, 8, 4, 14, 18))


def test_inspection_replies_are_validated_and_clamped() -> None:
    finding = parse_inspection({"condition": "severe_wear", "matches_predicted_failure": True, "confidence": 1.7,
                                "observations": ["spalling on the outer race", " "], "advice": "Replace now."}, "AL-2", "A", T0)
    assert finding.confidence == 1.0 and finding.observations == ("spalling on the outer race",)
    with pytest.raises(FieldInputError, match="condition"):
        parse_inspection({"condition": "looks bad", "confidence": 0.5}, "AL-2", "A", T0)


def test_supplier_replies_parse_dates_and_reject_invented_ones() -> None:
    update = parse_supplier_update({"supplier_name": "Everline", "order_reference": "SPO-US1-0061", "change": "delay",
                                    "new_delivery_date": "2026-08-08", "reason": "heat treatment", "confidence": 0.9}, T0)
    assert update.new_delivery_at == datetime(2026, 8, 8, 12, 0)
    none = parse_supplier_update({"change": "no_delivery_change", "new_delivery_date": "", "confidence": 1}, T0)
    assert none.new_delivery_at is None
    with pytest.raises(FieldInputError, match="ISO date"):
        parse_supplier_update({"change": "delay", "new_delivery_date": "next week", "confidence": 1}, T0)


def test_a_new_date_revises_only_its_order_and_only_once_received() -> None:
    update = SupplierUpdate(T0, "Everline", "SPO-US1-0061", "delay", datetime(2026, 8, 8, 12), "", 1.0)
    other = SupplierUpdate(T0, "Orbital", "SPO-US1-0064", "delay", datetime(2026, 9, 1, 12), "", 1.0)
    assert revise_expected(ORDER, [update, other], T0 + timedelta(hours=1)).expected_at == datetime(2026, 8, 8, 12)
    assert revise_expected(ORDER, [update], T0 - timedelta(hours=1)) == ORDER


def test_the_latest_word_wins_and_a_cancelled_order_is_dropped() -> None:
    delay = SupplierUpdate(T0, "Everline", "SPO-US1-0061", "delay", datetime(2026, 8, 8, 12), "", 1.0)
    on_time = SupplierUpdate(T0 + timedelta(hours=2), "Everline", "SPO-US1-0061", "on_time", None, "", 1.0)
    cancelled = SupplierUpdate(T0 + timedelta(hours=4), "Everline", "SPO-US1-0061", "cancelled", None, "", 1.0)
    no_change = SupplierUpdate(T0 + timedelta(hours=6), "Everline", "SPO-US1-0061", "no_delivery_change", None, "", 1.0)
    later = T0 + timedelta(hours=8)
    assert revise_expected(ORDER, [delay, on_time], later).expected_at == max(ORDER.promised_at, later)
    assert revise_expected(ORDER, [delay, on_time, cancelled], later) is None
    assert revise_expected(ORDER, [cancelled], T0) == ORDER
    assert revise_expected(ORDER, [delay, no_change], later).expected_at == datetime(2026, 8, 8, 12)


def test_samples_load_with_their_received_time(tmp_path: Path) -> None:
    (tmp_path / "inbox").mkdir()
    (tmp_path / "photos").mkdir()
    (tmp_path / "inbox" / "01_delay.txt").write_text("From: Everline\nDate: 2026-07-24T09:15\nSubject: Delay\n\nBody")
    (tmp_path / "photos" / "US1-L2-01_bearing.jpg").write_bytes(b"jpg")
    (tmp_path / "photos" / "notes.txt").write_text("not a photo")
    message = sample_messages(tmp_path)[0]
    assert (message.sender, message.received_at, message.subject) == ("Everline", "2026-07-24T09:15", "Delay")
    assert [(p.name, p.asset_id) for p in sample_photos(tmp_path)] == [("US1-L2-01_bearing.jpg", "US1-L2-01")]
    assert photo_path(tmp_path, "../inbox/01_delay.txt") is None and photo_path(tmp_path, "US1-L2-01_bearing.jpg")


def test_repository_samples_are_readable() -> None:
    root = Path(__file__).resolve().parents[2] / "demo" / "field"
    names = [m.name for m in sample_messages(root)]
    assert names == ["01_everline_delay", "02_orbital_confirmation", "03_everline_price_list"]
