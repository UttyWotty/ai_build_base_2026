"""Parses the losses document (losses, planned stop reasons, loss reasons) into a LossTaxonomy.

Shape errors name the dotted path of the offending field; unknown fields are rejected to catch typos.
Whether each reason points at a suitable loss is checked by the loss validator.
"""
from __future__ import annotations

from pdm_oee.core.enums import Factor, LossSource
from pdm_oee.core.field_readers import (
    as_mapping,
    reject_unknown_keys,
    require_enum,
    require_mapping,
    require_str,
)
from pdm_oee.core.loss_model import Loss, LossReason, LossTaxonomy, PlannedStopReason

ROOT_KEYS = frozenset({"losses", "planned_stop_reasons", "loss_reasons"})
LOSS_KEYS = frozenset({"label", "factor", "source"})
PLANNED_KEYS = frozenset({"label"})
REASON_KEYS = frozenset({"label", "loss"})


def parse_losses(raw: object) -> LossTaxonomy:
    """Turn the losses document into a LossTaxonomy."""
    root = as_mapping(raw, "losses")
    reject_unknown_keys(root, ROOT_KEYS, "losses")
    losses = {}
    for name, value in require_mapping(root, "losses", "").items():
        path = f"losses.{name}"
        fields = as_mapping(value, path)
        reject_unknown_keys(fields, LOSS_KEYS, path)
        losses[name] = Loss(name, require_str(fields, "label", path), require_enum(fields, "factor", path, Factor),
                            require_enum(fields, "source", path, LossSource))
    planned = {}
    for name, value in require_mapping(root, "planned_stop_reasons", "").items():
        path = f"planned_stop_reasons.{name}"
        fields = as_mapping(value, path)
        reject_unknown_keys(fields, PLANNED_KEYS, path)
        planned[name] = PlannedStopReason(name, require_str(fields, "label", path))
    reasons = {}
    for name, value in require_mapping(root, "loss_reasons", "").items():
        path = f"loss_reasons.{name}"
        fields = as_mapping(value, path)
        reject_unknown_keys(fields, REASON_KEYS, path)
        reasons[name] = LossReason(name, require_str(fields, "label", path), require_str(fields, "loss", path))
    return LossTaxonomy(losses=losses, planned_stop_reasons=planned, loss_reasons=reasons)
