"""Makes the conform and prediction fixtures available to the alert tests.

The prediction service with the compressed split is built once per session by the prediction fixtures.
Nothing here changes the fixtures.
"""
from __future__ import annotations

from tests.pdm_oee.conform.conftest import conformed, mappings, source_frames
from tests.pdm_oee.prediction.conftest import prediction, small_database

__all__ = ["conformed", "mappings", "prediction", "small_database", "source_frames"]
