"""Normalization of business terms so synonyms compare equal regardless of case and punctuation.

Hyphens, underscores, and runs of whitespace all collapse to a single space.
normalize_term is used for collision checks; normalize_text additionally drops punctuation for matching questions.
"""
from __future__ import annotations

import re

_SEPARATOR_PATTERN = re.compile(r"[-_\s]+")
_TERM_SEPARATOR = " "


def normalize_term(text: str) -> str:
    """Return the canonical comparison form of a business term."""
    return _SEPARATOR_PATTERN.sub(_TERM_SEPARATOR, text.strip().lower()).strip()


_NON_WORD_PATTERN = re.compile(r"[^a-z0-9]+")


def normalize_text(text: str) -> str:
    """Lower-case text with every run of non-alphanumeric characters collapsed to one space (for phrase matching)."""
    return _NON_WORD_PATTERN.sub(_TERM_SEPARATOR, text.lower()).strip()
