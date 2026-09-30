"""Domain-specific exceptions and the validation issue record for the plant model and metric catalog.

Parse errors carry the dotted path of the offending YAML field so authors can find it quickly.
Validation collects every issue before failing, so a single run reports all problems in the catalog.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationIssue:
    """One semantic problem found while validating the plant model, losses, measures, or metrics."""

    location: str
    message: str

    def __str__(self) -> str:
        return f"{self.location}: {self.message}"


class CatalogError(Exception):
    """Base class for every error raised while loading the governed catalog."""


class SemanticParseError(CatalogError):
    """A catalog file does not have the expected shape."""

    def __init__(self, path: str, message: str) -> None:
        super().__init__(f"{path}: {message}")
        self.path = path
        self.detail = message


class CatalogValidationError(CatalogError):
    """The catalog files parsed but are semantically inconsistent."""

    def __init__(self, issues: tuple[ValidationIssue, ...]) -> None:
        listing = "\n".join(f"  - {issue}" for issue in issues)
        super().__init__(f"{len(issues)} catalog issue(s):\n{listing}")
        self.issues = issues


class SemanticFileError(CatalogError):
    """A catalog file is missing, unreadable, or not valid YAML."""
