"""Domain-specific exception for the conform pipeline.

Raised when source data cannot be mapped to canonical form: missing files or columns, unknown codes, or unmapped keys.
Failing loudly is deliberate; silently dropping rows would make governed metrics wrong without anyone noticing.
"""
from __future__ import annotations


class ConformError(Exception):
    """Source data cannot be conformed to the ontology."""
