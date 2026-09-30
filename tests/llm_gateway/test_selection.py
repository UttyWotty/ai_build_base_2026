"""Tests for resolving the provider, model, and endpoint of a run from settings and overrides.

The model default follows the chosen provider, and overrides always win over settings.
Unknown providers are rejected with the list of supported ones.
"""
from __future__ import annotations

import pytest

from llm_gateway.selection import (
    ModelDefaults,
    ModelSelectionError,
    Provider,
    resolve_selection,
)

DEFAULTS = ModelDefaults("gemini", "gemini-x", "local-y", "http://127.0.0.1:8080/v1", 30.0)


def test_defaults_resolve_to_the_configured_provider_and_its_model() -> None:
    selection = resolve_selection(DEFAULTS)
    assert selection.provider is Provider.GEMINI and selection.model == "gemini-x" and selection.label == "gemini-x"


def test_switching_provider_switches_the_default_model() -> None:
    selection = resolve_selection(DEFAULTS, provider="local")
    assert selection.provider is Provider.LOCAL and selection.model == "local-y"
    assert selection.base_url == "http://127.0.0.1:8080/v1" and selection.timeout_seconds == 30.0


def test_overrides_win_and_provider_names_are_case_insensitive() -> None:
    selection = resolve_selection(DEFAULTS, provider=" LOCAL ", model="other", base_url="http://h:1/v1")
    assert (selection.provider, selection.model, selection.base_url) == (Provider.LOCAL, "other", "http://h:1/v1")


def test_unknown_provider_is_rejected() -> None:
    with pytest.raises(ModelSelectionError, match="gemini, local"):
        resolve_selection(DEFAULTS, provider="openai")
