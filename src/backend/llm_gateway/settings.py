"""Environment-driven model settings shared by every package, each with an explicit default.

LLM_PROVIDER picks the adapter: gemini (AI Studio key or Vertex AI, from the google-genai environment) or local.
The local adapter talks to an OpenAI-compatible server such as mlx_lm.server at LLM_BASE_URL.
"""
from __future__ import annotations

import os

# gemini or local.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
# Gemini model id; credentials come from GEMINI_API_KEY, or from Vertex AI settings on Google Cloud.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
# Backup Gemini models, comma-separated, tried in order when the current one is out of quota or unavailable.
GEMINI_FALLBACK_MODELS = tuple(m.strip() for m in os.getenv("GEMINI_FALLBACK_MODELS", "").split(",") if m.strip())
# Local OpenAI-compatible endpoint and the model that server is serving.
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:8080/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "ailexleon/Huihui-Qwen3.8-27B-abliterated-mlx-6Bit")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "300"))
