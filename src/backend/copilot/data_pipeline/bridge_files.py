"""Loads the governed bridge document from the semantic directory.

Only parsing happens here; cross-checks against both worlds need their data and run in the bridge builder service.
The YAML loader rejects duplicate keys, like every other governed file in the repository.
"""
from __future__ import annotations

from pathlib import Path

from copilot.core.bridge_model import BridgeCatalog
from copilot.core.bridge_parser import parse_bridge
from pdm_oee.data_pipeline.semantic_files import load_yaml_document

BRIDGE_FILENAME = "bridge.yaml"


def load_bridge(semantic_dir: Path) -> BridgeCatalog:
    """Parse semantic/bridge/bridge.yaml."""
    return parse_bridge(load_yaml_document(semantic_dir / BRIDGE_FILENAME))
