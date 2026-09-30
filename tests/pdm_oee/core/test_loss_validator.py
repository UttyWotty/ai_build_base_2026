"""The loss validator: factors fixed by source, derived sources used once, and reasons booked only to stop-reason losses.

Each test breaks one thing in a valid taxonomy and expects the matching issue.
The unbroken taxonomy must produce no issues at all.
"""
from __future__ import annotations

from pdm_oee.core.loss_parser import parse_losses
from pdm_oee.core.loss_validator import validate_losses
from tests.pdm_oee.core.catalog_fixtures import RawDocument, raw_losses


def issues_for(document: RawDocument) -> list[str]:
    return [str(issue) for issue in validate_losses(parse_losses(document))]


def test_valid_taxonomy_has_no_issues() -> None:
    assert issues_for(raw_losses()) == []


def test_source_fixes_the_factor() -> None:
    document = raw_losses()
    document["losses"]["small_stops"]["factor"] = "availability"
    assert issues_for(document) == ["losses.small_stops: source short_stop belongs to performance, not availability"]


def test_each_derived_source_is_used_exactly_once() -> None:
    document = raw_losses()
    del document["losses"]["reduced_speed"]
    document["losses"]["scrap_again"] = {"label": "Scrap", "factor": "quality", "source": "production_scrap"}
    issues = issues_for(document)
    assert "losses: source speed_gap must be used by exactly one loss, not 0" in issues
    assert "losses: source production_scrap must be used by exactly one loss, not 2" in issues


def test_reasons_point_only_at_stop_reason_losses() -> None:
    document = raw_losses()
    document["loss_reasons"]["jam"] = {"label": "Jam", "loss": "small_stops"}
    document["loss_reasons"]["fire"] = {"label": "Fire", "loss": "disasters"}
    issues = issues_for(document)
    assert "loss_reasons.jam: loss 'small_stops' is derived from short_stop, not from stop reasons" in issues
    assert "loss_reasons.fire: unknown loss 'disasters'" in issues


def test_stop_reason_loss_needs_a_reason_and_names_are_exclusive() -> None:
    document = raw_losses()
    document["losses"]["external_stops"] = {"label": "External", "factor": "availability", "source": "stop_reason"}
    document["loss_reasons"]["scheduled_break"] = {"label": "Break", "loss": "breakdowns"}
    issues = issues_for(document)
    assert "losses.external_stops: no loss reason is booked to it" in issues
    assert "loss_reasons.scheduled_break: is also a planned stop reason" in issues


def test_planned_stop_reasons_are_required() -> None:
    document = raw_losses()
    document["planned_stop_reasons"] = {}
    assert issues_for(document) == ["planned_stop_reasons: at least one planned stop reason is required"]
