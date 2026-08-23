from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class LLMError(RuntimeError):
    """Raised when an LLM provider cannot complete a structured request."""


class LLMClient(ABC):
    @abstractmethod
    def generate_json(
        self,
        *,
        system_prompt: str,
        user_text: str,
        schema: dict[str, Any],
        schema_name: str,
        file_path: str | Path | None = None,
        max_output_tokens: int = 6000,
    ) -> dict[str, Any]:
        raise NotImplementedError
