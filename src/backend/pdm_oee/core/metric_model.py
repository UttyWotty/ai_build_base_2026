"""Measures and metrics: every base quantity is declared once, and every metric is one ratio of two measures.

A measure fixes its grain, unit, and precise definition; the OEE engine computes measures exactly as defined here.
A metric names its numerator and denominator, so two metrics that share a measure can never compute it differently.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from pdm_oee.core.enums import Grain, MeasureUnit, MetricFormat, Team


@dataclass(frozen=True)
class Measure:
    """A base quantity computed at one grain, such as run time per asset and shift."""

    id: str
    label: str
    grain: Grain
    unit: MeasureUnit
    definition: str
    parameters: Mapping[str, float]


@dataclass(frozen=True)
class Metric:
    """A governed metric: sum(numerator) / sum(denominator) at any roll-up level."""

    id: str
    label: str
    description: str
    owner: Team
    numerator: str
    denominator: str
    value_format: MetricFormat
    synonyms: tuple[str, ...]
    not_to_be_confused_with: tuple[str, ...]
    source: str
