"""Adapters that move data in and out of the pure core: semantic file loading, synthetic generation, and DuckDB access.

Modules here own all filesystem and database I/O for the project.
They depend on the core package and are called by the services layer.
"""
