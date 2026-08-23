from __future__ import annotations

import os

from .base import LLMClient, LLMError
from .mock_client import MockLLMClient
from .openai_client import OpenAIResponsesClient


def create_llm_client(provider: str | None = None, model: str | None = None) -> LLMClient:
    name = (provider or os.getenv("LLM_PROVIDER") or "openai").strip().lower()
    if name == "openai":
        return OpenAIResponsesClient(model=model)
    if name == "mock":
        return MockLLMClient()
    raise LLMError(f"Unsupported LLM provider: {name}. Supported: openai, mock")


__all__ = [
    "LLMClient",
    "LLMError",
    "MockLLMClient",
    "OpenAIResponsesClient",
    "create_llm_client",
]
