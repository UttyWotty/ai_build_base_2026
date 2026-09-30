"""Application services: compose the pure core with the data adapters to answer governed questions.

Services receive their adapters through constructor parameters so tests can substitute in-memory ones.
The API layer (CLI and UI) calls services and never reaches past them into the pipeline.
"""
