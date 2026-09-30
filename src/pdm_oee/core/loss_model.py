"""The governed loss taxonomy: losses with their OEE factor and source, planned stop reasons, and loss reasons.

Planned stop reasons remove time from planned production time and are never losses.
Loss reasons are the MES stop reasons that count against availability; the other losses are derived from short stops, speed, and scrap.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from pdm_oee.core.enums import Factor, LossSource


@dataclass(frozen=True)
class Loss:
    """One of the OEE losses."""

    id: str
    label: str
    factor: Factor
    source: LossSource


@dataclass(frozen=True)
class PlannedStopReason:
    """A stop that is planned, so its time is excluded from planned production time."""

    id: str
    label: str


@dataclass(frozen=True)
class LossReason:
    """An unplanned stop reason and the availability loss it is booked to."""

    id: str
    label: str
    loss: str


@dataclass(frozen=True)
class LossTaxonomy:
    """Losses and every stop reason the MES may report."""

    losses: Mapping[str, Loss]
    planned_stop_reasons: Mapping[str, PlannedStopReason]
    loss_reasons: Mapping[str, LossReason]
