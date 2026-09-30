"""Tests for the Gemini adapter against an in-memory fake of the google-genai client.

They check the request it builds, retries on rate limits with backoff, and immediate failure on other client errors.
An empty reply is reported with its finish reason instead of returning blank text.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from google.genai import errors, types

from llm_gateway.client import LLMError
from llm_gateway.gemini import GeminiClient
from llm_gateway.retry import RetryPolicy

MESSAGES = [{"role": "system", "content": "Be exact."}, {"role": "user", "content": "How many?"}]


@dataclass
class FakeModels:
    """Replays scripted outcomes: a reply text, None for an empty reply, or an exception to raise."""

    outcomes: list[object]
    calls: list[dict[str, object]] = field(default_factory=list)

    def generate_content(self, model: str, contents: list[types.Content],
                         config: types.GenerateContentConfig) -> types.GenerateContentResponse:
        self.calls.append({"model": model, "contents": contents, "config": config})
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        if outcome is None:
            return types.GenerateContentResponse(candidates=[types.Candidate(finish_reason=types.FinishReason.SAFETY)])
        return types.GenerateContentResponse(candidates=[types.Candidate(
            content=types.Content(role="model", parts=[types.Part(text=str(outcome))]))])


@dataclass
class FakeGenaiClient:
    models: FakeModels


def rate_limited() -> errors.ClientError:
    return errors.ClientError(429, {"error": {"code": 429, "message": "quota", "status": "RESOURCE_EXHAUSTED"}})


def make_client(outcomes: list[object], sleeps: list[float]) -> tuple[GeminiClient, FakeModels]:
    models = FakeModels(outcomes)
    client = GeminiClient("gemini-test", 10.0, retry_policy=RetryPolicy(retries=2, base_delay_seconds=1.0),
                          client=FakeGenaiClient(models), sleep=sleeps.append)
    return client, models


def test_request_carries_the_system_instruction_turns_and_settings() -> None:
    client, models = make_client(["42"], [])
    assert client.complete(MESSAGES) == "42"
    call = models.calls[0]
    assert call["model"] == "gemini-test"
    assert call["config"].system_instruction == "Be exact." and call["config"].temperature == 0.0
    assert [(c.role, c.parts[0].text) for c in call["contents"]] == [("user", "How many?")]


def test_rate_limits_are_retried_with_backoff() -> None:
    sleeps: list[float] = []
    client, models = make_client([rate_limited(), rate_limited(), "ok"], sleeps)
    assert client.complete(MESSAGES) == "ok" and sleeps == [1.0, 2.0] and len(models.calls) == 3


def test_retries_run_out_with_an_llm_error() -> None:
    client, _ = make_client([rate_limited(), rate_limited(), rate_limited()], [])
    with pytest.raises(LLMError, match="request failed"):
        client.complete(MESSAGES)


def test_other_client_errors_fail_at_once() -> None:
    forbidden = errors.ClientError(403, {"error": {"code": 403, "message": "denied", "status": "PERMISSION_DENIED"}})
    client, models = make_client([forbidden, "never"], [])
    with pytest.raises(LLMError, match="denied"):
        client.complete(MESSAGES)
    assert len(models.calls) == 1


def test_an_empty_reply_reports_its_finish_reason() -> None:
    client, _ = make_client([None], [])
    with pytest.raises(LLMError, match="SAFETY"):
        client.complete(MESSAGES)


def test_malformed_messages_raise_llm_error_before_any_request() -> None:
    client, models = make_client(["never"], [])
    with pytest.raises(LLMError):
        client.complete([{"role": "system", "content": "no question"}])
    assert models.calls == []
