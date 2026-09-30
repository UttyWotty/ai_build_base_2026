"""Re-exports the service fixtures (catalog and the conformed small world) for the UI tests.

The UI tests inject these into the page's session state instead of loading data/conformed.
Fixtures are session-scoped and read-only.
"""
from __future__ import annotations

from tests.supply_ontology.services.conftest import catalog, conformed_database

__all__ = ["catalog", "conformed_database"]
