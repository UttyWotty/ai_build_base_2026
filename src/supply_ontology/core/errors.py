"""Domain-specific exceptions and the validation issue record for the semantic layer.

Parse errors carry the dotted path of the offending YAML field so authors can find it quickly.
Validation collects every issue before failing, so a single run reports all problems in the catalog.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationIssue:
    """One semantic problem found while validating the ontology or metrics."""

    location: str
    message: str

    def __str__(self) -> str:
        return f"{self.location}: {self.message}"


class SemanticLayerError(Exception):
    """Base class for every error raised by the semantic layer."""


class SemanticParseError(SemanticLayerError):
    """A semantic file does not have the expected shape."""

    def __init__(self, path: str, message: str) -> None:
        super().__init__(f"{path}: {message}")
        self.path = path
        self.detail = message


class CatalogValidationError(SemanticLayerError):
    """The ontology or metrics parsed but are semantically inconsistent."""

    def __init__(self, issues: tuple[ValidationIssue, ...]) -> None:
        listing = "\n".join(f"  - {issue}" for issue in issues)
        super().__init__(f"{len(issues)} semantic catalog issue(s):\n{listing}")
        self.issues = issues


class JoinPathError(SemanticLayerError):
    """No unique declared relationship path exists between two entities."""


class SemanticFileError(SemanticLayerError):
    """A semantic file is missing, unreadable, or not valid YAML."""


class QueryValidationError(SemanticLayerError):
    """A query spec references things the catalog does not allow."""

    def __init__(self, issues: tuple[ValidationIssue, ...]) -> None:
        listing = "\n".join(f"  - {issue}" for issue in issues)
        super().__init__(f"{len(issues)} query issue(s):\n{listing}")
        self.issues = issues
