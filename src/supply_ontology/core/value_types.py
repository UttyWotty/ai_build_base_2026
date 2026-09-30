"""Compatibility between literal filter values and attribute data types.

Both governed metric filters and user query filters use this rule, so a value accepted in one place is accepted in the other.
Booleans are never accepted as numbers, and dates must be ISO-8601 strings or date objects.
"""
from __future__ import annotations

from datetime import date

from supply_ontology.core.enums import AttributeType


def value_matches_type(value: object, data_type: AttributeType) -> bool:
    """Return True when the literal can be compared with an attribute of this type."""
    if isinstance(value, bool):
        return data_type == AttributeType.BOOLEAN
    if data_type == AttributeType.STRING:
        return isinstance(value, str)
    if data_type == AttributeType.INTEGER:
        return isinstance(value, int)
    if data_type == AttributeType.DECIMAL:
        return isinstance(value, (int, float))
    if data_type == AttributeType.DATE:
        return isinstance(value, date) or (isinstance(value, str) and _is_iso_date(value))
    return False


def _is_iso_date(text: str) -> bool:
    try:
        date.fromisoformat(text)
    except ValueError:
        return False
    return True
