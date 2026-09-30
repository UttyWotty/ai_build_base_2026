"""Shared command-line options for choosing the model per run: --provider, --model, and --base-url.

Every option defaults to None, so an absent flag falls back to the settings through the normal resolution.
Command lines in every package use these helpers, so the flags mean the same thing everywhere.
"""
from __future__ import annotations

import argparse

from llm_gateway.factory import default_selection
from llm_gateway.selection import ModelSelection, Provider


def add_model_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the model selection flags to a parser."""
    parser.add_argument("--provider", choices=[p.value for p in Provider], default=None,
                        help="model provider (default: LLM_PROVIDER)")
    parser.add_argument("--model", default=None, help="model id (default: GEMINI_MODEL or LLM_MODEL, per provider)")
    parser.add_argument("--base-url", default=None, help="local OpenAI-compatible endpoint (default: LLM_BASE_URL)")


def selection_from_args(args: argparse.Namespace) -> ModelSelection:
    """The selection the parsed flags ask for."""
    return default_selection(args.provider, args.model, args.base_url)
