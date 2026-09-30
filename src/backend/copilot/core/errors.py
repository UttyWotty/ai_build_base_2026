"""Domain-specific exceptions of the copilot.

Bridge validation collects every broken reference before failing, so one run reports all of them.
Impact errors name the alert or asset that could not be analysed.
"""
from __future__ import annotations


class CopilotError(Exception):
    """Base class for every copilot error."""


class BridgeValidationError(CopilotError):
    """The bridge definition refers to ids that do not exist, or its policies are inconsistent."""

    def __init__(self, issues: list[str]) -> None:
        self.issues = issues
        super().__init__("Bridge definition is invalid:\n" + "\n".join(f"  - {issue}" for issue in issues))


class ImpactError(CopilotError):
    """An impact analysis cannot be computed for the requested alert."""
