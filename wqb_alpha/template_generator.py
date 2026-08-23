from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import PROMPTS_DIR
from .llm.base import LLMClient
from .template_schema import GeneratedTemplateSpec, TEMPLATE_SPEC_SCHEMA
from .validator import ValidationReport, validate_generated_template


class TemplateGenerator:
    def __init__(
        self,
        llm: LLMClient,
        prompt_path: str | Path | None = None,
        repair_prompt_path: str | Path | None = None,
    ) -> None:
        self.llm = llm
        self.prompt_path = Path(prompt_path or (PROMPTS_DIR / "template_generation.txt")).resolve()
        self.repair_prompt_path = Path(
            repair_prompt_path or (PROMPTS_DIR / "template_repair.txt")
        ).resolve()

    @staticmethod
    def _compact_fields(records: list[dict]) -> list[dict[str, Any]]:
        out = []
        for r in records:
            out.append(
                {
                    "id": r.get("id"),
                    "description": r.get("description"),
                    "dataset": r.get("dataset", {}).get("id"),
                    "type": r.get("type"),
                    "coverage": r.get("coverage"),
                    "retrievalScore": r.get("retrievalScore"),
                }
            )
        return out

    @staticmethod
    def _compact_operators(records: list[dict]) -> list[dict[str, Any]]:
        return [
            {
                "name": r.get("name"),
                "category": r.get("category"),
                "definition": r.get("definition"),
                "description": r.get("description"),
            }
            for r in records
        ]

    def generate(
        self,
        *,
        analysis: dict[str, Any],
        candidate_fields: list[dict],
        candidate_operators: list[dict],
    ) -> GeneratedTemplateSpec:
        system_prompt = self.prompt_path.read_text(encoding="utf-8")
        context = {
            "paper_analysis": analysis,
            "allowed_data_fields": self._compact_fields(candidate_fields),
            "allowed_regular_operators": self._compact_operators(candidate_operators),
            "fixed_environment": {
                "instrumentType": "EQUITY",
                "region": "GLB",
                "delay": 1,
                "universe": "TOPDIV3000",
                "language": "FASTEXPR",
                "type": "REGULAR",
            },
        }
        raw = self.llm.generate_json(
            system_prompt=system_prompt,
            user_text=json.dumps(context, ensure_ascii=False, indent=2),
            schema=TEMPLATE_SPEC_SCHEMA,
            schema_name="alpha_template",
            max_output_tokens=8000,
        )
        return GeneratedTemplateSpec.from_dict(raw)

    def repair(
        self,
        *,
        spec: GeneratedTemplateSpec,
        report: ValidationReport,
        analysis: dict[str, Any],
        candidate_fields: list[dict],
        candidate_operators: list[dict],
    ) -> GeneratedTemplateSpec:
        system_prompt = self.repair_prompt_path.read_text(encoding="utf-8")
        context = {
            "validation_errors": report.errors,
            "validation_warnings": report.warnings,
            "current_template": spec.to_dict(),
            "paper_analysis": analysis,
            "allowed_data_fields": self._compact_fields(candidate_fields),
            "allowed_regular_operators": self._compact_operators(candidate_operators),
        }
        raw = self.llm.generate_json(
            system_prompt=system_prompt,
            user_text=json.dumps(context, ensure_ascii=False, indent=2),
            schema=TEMPLATE_SPEC_SCHEMA,
            schema_name="alpha_template_repair",
            max_output_tokens=8000,
        )
        return GeneratedTemplateSpec.from_dict(raw)
