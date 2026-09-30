"""Pure domain core of the semantic layer: ontology and metric models, parsing, and validation.

Nothing in this package performs I/O; parsers receive already-loaded Python structures and validators return issue lists.
Higher layers (data_pipeline, services) load files and call into this package, never the other way around.
"""
