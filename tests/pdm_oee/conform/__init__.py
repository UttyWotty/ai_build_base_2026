"""Tests for the conform pipeline: every canonical table equals its truth table, and undeclared data fails loudly.

The small plant's rendered sources are conformed in memory; one test also goes through real files.
The comparison helper normalises row order and dtypes but never tolerates a different value.
"""
