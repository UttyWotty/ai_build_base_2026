"""Tests for the query spec parser, validator, and SQL compiler.

Golden tests execute compiled SQL on an in-memory DuckDB loaded with a tiny hand-built world.
Every expected value is derived by hand in golden_world.py, never by running the implementation.
"""
