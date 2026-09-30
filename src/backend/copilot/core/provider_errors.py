"""Turns a model provider's raw error into a plain-language issue: what happened, and what a person can do about it.

Quota limits and unknown models are worth retrying on another model; an overloaded model is worth retrying later;
a key or permission problem needs a person. The raw text stays available for the details view.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

MODEL_PATTERN = re.compile(r"model:\s*([\w.\-]+)")


class IssueKind(str, Enum):
    QUOTA = "quota"
    OVERLOADED = "overloaded"
    AUTH = "auth"
    MODEL_UNAVAILABLE = "model_unavailable"
    OTHER = "other"


@dataclass(frozen=True)
class ProviderIssue:
    kind: IssueKind
    message: str

    @property
    def try_another_model(self) -> bool:
        return self.kind in (IssueKind.QUOTA, IssueKind.MODEL_UNAVAILABLE)

    @property
    def stops_autopilot(self) -> bool:
        return self.kind in (IssueKind.QUOTA, IssueKind.AUTH)


def classify(raw: str, model: str) -> ProviderIssue:
    """The issue behind a provider error text."""
    text = raw.upper()
    named = MODEL_PATTERN.search(raw)
    which = named.group(1) if named else model
    if "429" in text or "RESOURCE_EXHAUSTED" in text or "QUOTA" in text:
        return ProviderIssue(IssueKind.QUOTA,
                             f"The Gemini quota for {which} is used up. The free tier allows about 20 requests per model "
                             "per day and resets daily. Add backup models in GEMINI_FALLBACK_MODELS, switch GEMINI_MODEL, "
                             "or use a paid key or Vertex AI.")
    if "503" in text or "UNAVAILABLE" in text or "OVERLOADED" in text:
        return ProviderIssue(IssueKind.OVERLOADED,
                             f"Gemini ({which}) is overloaded right now. This is on Google's side and usually passes "
                             "within minutes; try again shortly.")
    if "401" in text or "403" in text or "API_KEY" in text or "API KEY" in text or "PERMISSION_DENIED" in text \
            or "UNAUTHENTICATED" in text:
        return ProviderIssue(IssueKind.AUTH,
                             "Gemini refused the credentials. Check GEMINI_API_KEY locally, or the service account's "
                             "Vertex AI role on Google Cloud.")
    if "404" in text or "NOT_FOUND" in text:
        return ProviderIssue(IssueKind.MODEL_UNAVAILABLE,
                             f"The model {which} is not available for this key or region. Choose another GEMINI_MODEL.")
    return ProviderIssue(IssueKind.OTHER, f"The model could not answer ({raw[:120]}).")
