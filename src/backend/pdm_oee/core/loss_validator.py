"""Consistency checks for the loss taxonomy, so every minute and every part lands in exactly one loss.

Each source fixes its factor: stop reasons are availability, short stops and the speed gap are performance, scrap is quality.
Derived sources are used by exactly one loss; stop-reason losses need at least one reason, and reasons may only point at them.
"""
from __future__ import annotations

from collections import Counter

from pdm_oee.core.enums import Factor, LossSource
from pdm_oee.core.errors import ValidationIssue
from pdm_oee.core.identifiers import IDENTIFIER_RULE, is_valid_identifier
from pdm_oee.core.loss_model import LossTaxonomy

SOURCE_FACTOR: dict[LossSource, Factor] = {
    LossSource.STOP_REASON: Factor.AVAILABILITY,
    LossSource.SHORT_STOP: Factor.PERFORMANCE,
    LossSource.SPEED_GAP: Factor.PERFORMANCE,
    LossSource.STARTUP_SCRAP: Factor.QUALITY,
    LossSource.PRODUCTION_SCRAP: Factor.QUALITY,
}


def validate_losses(taxonomy: LossTaxonomy) -> list[ValidationIssue]:
    """Every problem in the loss taxonomy."""
    names = [*taxonomy.losses, *taxonomy.planned_stop_reasons, *taxonomy.loss_reasons]
    issues = [ValidationIssue("losses", f"name '{n}' {IDENTIFIER_RULE}") for n in names if not is_valid_identifier(n)]
    for loss in taxonomy.losses.values():
        if SOURCE_FACTOR[loss.source] is not loss.factor:
            issues.append(ValidationIssue(f"losses.{loss.id}", f"source {loss.source.value} belongs to "
                                          f"{SOURCE_FACTOR[loss.source].value}, not {loss.factor.value}"))
    used = Counter(loss.source for loss in taxonomy.losses.values())
    for source in LossSource:
        if source is not LossSource.STOP_REASON and used[source] != 1:
            issues.append(ValidationIssue("losses", f"source {source.value} must be used by exactly one loss, not {used[source]}"))
    issues += _check_reasons(taxonomy)
    return issues


def _check_reasons(taxonomy: LossTaxonomy) -> list[ValidationIssue]:
    issues = [ValidationIssue(f"loss_reasons.{r}", "is also a planned stop reason")
              for r in taxonomy.loss_reasons if r in taxonomy.planned_stop_reasons]
    for reason in taxonomy.loss_reasons.values():
        loss = taxonomy.losses.get(reason.loss)
        if loss is None:
            issues.append(ValidationIssue(f"loss_reasons.{reason.id}", f"unknown loss '{reason.loss}'"))
        elif loss.source is not LossSource.STOP_REASON:
            issues.append(ValidationIssue(f"loss_reasons.{reason.id}",
                                          f"loss '{loss.id}' is derived from {loss.source.value}, not from stop reasons"))
    booked = {r.loss for r in taxonomy.loss_reasons.values()}
    issues += [ValidationIssue(f"losses.{loss.id}", "no loss reason is booked to it")
               for loss in taxonomy.losses.values() if loss.source is LossSource.STOP_REASON and loss.id not in booked]
    if not taxonomy.planned_stop_reasons:
        issues.append(ValidationIssue("planned_stop_reasons", "at least one planned stop reason is required"))
    return issues
