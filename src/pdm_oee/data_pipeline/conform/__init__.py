"""The conform pipeline: source system exports in, one canonical table per entity out, exactly as the catalog defines them.

Every transformation is a pure function over frames; source_reader and conformed_store are the only file I/O.
Anything the source mappings do not declare (a tag, a code, a unit) raises ConformError instead of being guessed.
"""
