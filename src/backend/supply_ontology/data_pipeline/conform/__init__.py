"""Conform pipeline: turns messy source-system exports into canonical ontology entity tables.

Every transformation here is a pure function over pandas frames; reading sources and writing results live in thin adapters.
Derived attributes are computed exactly as their descriptions in semantic/ontology.yaml define them.
"""
