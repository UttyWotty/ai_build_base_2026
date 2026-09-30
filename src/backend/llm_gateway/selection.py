"""Resolves which provider, model, and endpoint a run uses, from settings plus optional per-run overrides.

Resolution is pure: settings values are passed in, so the rules are testable without touching the environment.
A command-line override wins over the setting; an unknown provider raises ModelSelectionError.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ModelSelectionError(ValueError):
    """The requested provider or model cannot be resolved."""


class Provider(str, Enum):
    """Supported model providers."""

    GEMINI = "gemini"
    LOCAL = "local"


@dataclass(frozen=True)
class ModelSelection:
    """One resolved model choice."""

    provider: Provider
    model: str
    # Only used by the local provider.
    base_url: str
    timeout_seconds: float

    @property
    def label(self) -> str:
        """Human-readable name, used in captions and report file names."""
        return self.model


@dataclass(frozen=True)
class ModelDefaults:
    """The settings the resolution starts from."""

    provider: str
    gemini_model: str
    local_model: str
    local_base_url: str
    timeout_seconds: float


def resolve_selection(defaults: ModelDefaults, provider: str | None = None, model: str | None = None,
                      base_url: str | None = None) -> ModelSelection:
    """Apply per-run overrides to the defaults; the model default follows the chosen provider."""
    name = (provider or defaults.provider).strip().lower()
    try:
        chosen = Provider(name)
    except ValueError as error:
        known = ", ".join(p.value for p in Provider)
        raise ModelSelectionError(f"Unknown model provider {name!r}; expected one of: {known}") from error
    default_model = defaults.gemini_model if chosen is Provider.GEMINI else defaults.local_model
    return ModelSelection(chosen, model or default_model, base_url or defaults.local_base_url, defaults.timeout_seconds)
