"""The naming rule for identifiers that the compiler will place into SQL.

Entity, attribute, relationship, hierarchy, and metric names must be lowercase snake_case.
Enforcing this at validation time means compiled SQL never needs to quote or escape identifiers.
"""
from __future__ import annotations

import re

IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
IDENTIFIER_RULE = "must be lowercase snake_case (letters, digits, underscores; starts with a letter)"


def is_valid_identifier(name: str) -> bool:
    """Return True when the name is safe to use unquoted in SQL."""
    return IDENTIFIER_PATTERN.fullmatch(name) is not None
