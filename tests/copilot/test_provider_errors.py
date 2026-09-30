"""Tests for provider error handling: plain-language classification, and the fallback to a backup Gemini model.

A quota error on the first model restarts the run on the next backup and says so; an error on the last model ends
the run with the plain-language message and its kind.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import errors

from copilot.core.provider_errors import IssueKind, classify
from copilot.services import agent_runner
from llm_gateway.selection import ModelSelection, Provider
from tests.copilot.test_agent_layer import FakeTools, ScriptedLlm

QUOTA = "429 RESOURCE_EXHAUSTED. Quota exceeded for metric: generate_content_free_tier_requests, limit: 20, model: gemini-a"


def test_classification_names_the_cause_and_the_next_step() -> None:
    quota = classify(QUOTA, "gemini-x")
    assert quota.kind is IssueKind.QUOTA and "gemini-a" in quota.message and quota.try_another_model and quota.stops_autopilot
    busy = classify("503 UNAVAILABLE. This model is currently experiencing high demand.", "gemini-x")
    assert busy.kind is IssueKind.OVERLOADED and not busy.try_another_model and not busy.stops_autopilot
    assert classify("400 INVALID_ARGUMENT. API key not valid.", "g").kind is IssueKind.AUTH
    assert classify("404 NOT_FOUND. models/gemini-2.5-flash is no longer available", "g").kind is IssueKind.MODEL_UNAVAILABLE
    assert classify("boom", "g").kind is IssueKind.OTHER


class QuotaLlm(BaseLlm):
    async def generate_content_async(self, llm_request: LlmRequest, stream: bool = False) -> AsyncGenerator[LlmResponse, None]:
        raise errors.ClientError(429, {"error": {"code": 429, "message": QUOTA, "status": "RESOURCE_EXHAUSTED"}})
        yield  # pragma: no cover


def models_by_name(selection: ModelSelection) -> BaseLlm:
    return QuotaLlm(model=selection.model) if selection.model == "gemini-a" else ScriptedLlm(model=selection.model)


def test_a_quota_error_falls_back_to_the_next_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_runner, "adk_model", models_by_name)
    monkeypatch.setattr(agent_runner, "GEMINI_FALLBACK_MODELS", ("gemini-b",))
    run = agent_runner.run_copilot("How many?", FakeTools(), ModelSelection(Provider.GEMINI, "gemini-a", "", 5.0))
    assert run.model == "gemini-b" and run.answer == "There are 2 open alerts." and not run.error
    assert [s.kind for s in run.steps if s.kind == "notice"] == []  # notices are streamed, not part of the answer's steps


def test_the_last_model_failing_ends_with_a_plain_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_runner, "adk_model", models_by_name)
    monkeypatch.setattr(agent_runner, "GEMINI_FALLBACK_MODELS", ())
    run = agent_runner.run_copilot("How many?", FakeTools(), ModelSelection(Provider.GEMINI, "gemini-a", "", 5.0))
    assert run.error_kind == "quota" and "used up" in run.error_message and run.error.startswith("429")
