"""Named random streams derived from one seed, so adding a draw in one module never shifts the draws of another.

Each stream is keyed by a stable name (a CRC32 of the text), not by call order.
Every module asks for its own stream; the same seed and name always give the same sequence.
"""
from __future__ import annotations

import zlib

import numpy as np


def stream(seed: int, name: str) -> np.random.Generator:
    """The random generator for one named purpose."""
    return np.random.default_rng([seed, zlib.crc32(name.encode("utf-8"))])
