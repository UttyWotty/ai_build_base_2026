"""Governed source mappings: how each site's systems print states, reasons, quality, units, and CMMS codes.

The conform step knows the source systems only through these declarations, never through the generator.
A code that is not declared here makes conform fail loudly instead of guessing.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from pdm_oee.core.enums import MachineState, SensorUnit, WorkType


@dataclass(frozen=True)
class SiteMapping:
    """One site's clock and the codes its MES and historian print."""

    site_id: str
    number: int
    timezone: str
    good_quality: tuple[str, ...]
    bad_quality: tuple[str, ...]
    states: Mapping[str, MachineState]
    reasons: Mapping[str, str]


@dataclass(frozen=True)
class PrintedUnit:
    """A unit string as printed, and how to convert it: canonical = (printed + offset) x scale."""

    text: str
    unit: SensorUnit
    offset: float
    scale: float


@dataclass(frozen=True)
class CmmsMapping:
    """Work type codes, failure codes, and the keywords that identify a failure mode when its code is blank."""

    work_types: Mapping[str, WorkType]
    failure_codes: Mapping[str, str]
    failure_keywords: Mapping[str, tuple[str, ...]]


@dataclass(frozen=True)
class SourceMappings:
    """Everything conform needs to read the source systems."""

    sites: Mapping[str, SiteMapping]
    printed_units: Mapping[str, PrintedUnit]
    cmms: CmmsMapping
