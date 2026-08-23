from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path
from typing import Any

import requests

from .base import LLMClient, LLMError


class OpenAIResponsesClient(LLMClient):
    """Minimal OpenAI Responses API client implemented with requests only.

    It supports:
    - structured JSON output via text.format/json_schema
    - direct PDF input using input_file + base64 data URI
    - normal text/Markdown input

    No OpenAI SDK dependency is required.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        max_retries: int = 3,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "").strip()
        if not self.api_key:
            raise LLMError(
                "OPENAI_API_KEY is missing. Put it in the environment or a local .env file."
            )
        self.model = (model or os.getenv("LLM_MODEL") or "gpt-5.6").strip()
        self.base_url = (
            base_url or os.getenv("OPENAI_API_BASE") or "https://api.openai.com/v1"
        ).rstrip("/")
        self.timeout = float(timeout or os.getenv("LLM_REQUEST_TIMEOUT", "180"))
        self.max_retries = max(1, int(max_retries))

    @staticmethod
    def _file_part(file_path: Path) -> dict[str, Any]:
        suffix = file_path.suffix.lower()
        if suffix != ".pdf":
            raise LLMError(
                f"Direct file input currently expects PDF. Got: {file_path.name}. "
                "Text/Markdown files are sent as text by paper_reader.py."
            )
        size = file_path.stat().st_size
        if size >= 50 * 1024 * 1024:
            raise LLMError(
                f"PDF is {size / (1024 * 1024):.1f} MB. OpenAI file inputs must be under 50 MB."
            )
        encoded = base64.b64encode(file_path.read_bytes()).decode("ascii")
        return {
            "type": "input_file",
            "filename": file_path.name,
            "file_data": f"data:application/pdf;base64,{encoded}",
        }

    @staticmethod
    def _extract_output_text(payload: dict[str, Any]) -> str:
        # The REST response exposes generated text inside output -> message -> content.
        chunks: list[str] = []
        for item in payload.get("output", []) or []:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            for content in item.get("content", []) or []:
                if not isinstance(content, dict):
                    continue
                if content.get("type") in {"output_text", "text"} and isinstance(
                    content.get("text"), str
                ):
                    chunks.append(content["text"])
        if chunks:
            return "\n".join(chunks).strip()
        # Be tolerant of wrappers/proxies that expose output_text directly.
        if isinstance(payload.get("output_text"), str):
            return payload["output_text"].strip()
        raise LLMError("Responses API returned no output text")

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
        user_content: list[dict[str, Any]] = []
        if file_path is not None:
            path = Path(file_path).expanduser().resolve()
            if not path.exists():
                raise LLMError(f"Paper file not found: {path}")
            user_content.append(self._file_part(path))
        user_content.append({"type": "input_text", "text": user_text})

        body = {
            "model": self.model,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                }
            },
            "max_output_tokens": int(max_output_tokens),
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.post(
                    f"{self.base_url}/responses",
                    headers=headers,
                    json=body,
                    timeout=self.timeout,
                )
                if response.status_code >= 400:
                    detail = response.text[:4000]
                    if response.status_code in {408, 409, 429} or response.status_code >= 500:
                        raise LLMError(
                            f"OpenAI API temporary error {response.status_code}: {detail}"
                        )
                    raise LLMError(f"OpenAI API error {response.status_code}: {detail}")
                payload = response.json()
                if payload.get("status") == "incomplete":
                    reason = (payload.get("incomplete_details") or {}).get("reason")
                    raise LLMError(f"OpenAI response incomplete: {reason}")
                text = self._extract_output_text(payload)
                try:
                    result = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise LLMError(f"Structured output was not valid JSON: {exc}") from exc
                if not isinstance(result, dict):
                    raise LLMError("Structured output root must be a JSON object")
                return result
            except (requests.RequestException, LLMError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(min(2 ** (attempt - 1), 8))
        raise LLMError(f"OpenAI request failed after {self.max_retries} attempts: {last_error}")
