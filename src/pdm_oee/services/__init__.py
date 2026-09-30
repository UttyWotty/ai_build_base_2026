"""Application services: they load conformed data through the DuckDB adapter and answer questions with pure core logic.

Services accept their adapters as optional constructor parameters so tests can pass in-memory databases.
Entry points (CLIs, the UI) call services and never reach adapters directly.
"""
