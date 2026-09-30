"""Domain-specific exceptions for synthetic data generation.

Configuration problems (for example more entities requested than unique names available) raise GenerationError.
Keeping these separate from semantic-layer errors makes failures easy to attribute.
"""
from __future__ import annotations


class GenerationError(Exception):
    """The generation config cannot produce a consistent world."""
