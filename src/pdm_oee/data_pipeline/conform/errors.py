"""The domain-specific exception of the conform pipeline.

ConformError means the sources contain something the governed mappings do not explain.
The message names the file, the value, and what was expected, so the mapping or the source can be fixed.
"""
from __future__ import annotations


class ConformError(Exception):
    """The sources cannot be conformed without guessing."""
