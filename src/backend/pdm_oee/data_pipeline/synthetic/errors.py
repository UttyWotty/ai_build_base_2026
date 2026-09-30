"""Domain-specific exceptions for the synthetic plant generator.

A GenerationError means the configuration cannot produce a consistent plant, for example a story on a missing asset.
It is raised before any file is written.
"""
from __future__ import annotations


class GenerationError(Exception):
    """The generation configuration is inconsistent."""
