"""The naming rule for identifiers in the plant model and metric catalog.

Asset classes, components, sensors, failure modes, losses, reason codes, measures, and metrics are lowercase snake_case.
Enforcing this at validation time means later SQL and file paths never need to quote or escape them.
"""
from __future__ import annotations

import re

IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
IDENTIFIER_RULE = "must be lowercase snake_case (letters, digits, underscores; starts with a letter)"


def is_valid_identifier(name: str) -> bool:
    """Return True when the name is safe to use unquoted in SQL."""
    return IDENTIFIER_PATTERN.fullmatch(name) is not None
