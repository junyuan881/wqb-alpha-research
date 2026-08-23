from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .alpha_template import ALPHA_SETTINGS


TEMPLATE_SPEC_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "description": {"type": "string"},
        "source_hypothesis_id": {"type": "string"},
        "expression_template": {"type": "string"},
        "variables": {
            "type": "array",
            "minItems": 1,
            "maxItems": 20,
            "items": {
                "type": "object",
                "properties": {
                    "placeholder": {"type": "string"},
                    "kind": {
                        "type": "string",
                        "enum": ["FIELD", "OPERATOR", "PARAMETER", "GROUP"],
                    },
                    "values": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 20,
                        "items": {"type": "string"},
                    },
                    "rationale": {"type": "string"},
                },
                "required": ["placeholder", "kind", "values", "rationale"],
                "additionalProperties": False,
            },
        },
        "design_notes": {
            "type": "array",
            "maxItems": 12,
            "items": {"type": "string"},
        },
    },
    "required": [
        "name",
        "description",
        "source_hypothesis_id",
        "expression_template",
        "variables",
        "design_notes",
    ],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class TemplateVariable:
    placeholder: str
    kind: str
    values: list[str]
    rationale: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TemplateVariable":
        placeholder = str(data["placeholder"]).strip()
        if not placeholder.startswith("<"):
            placeholder = f"<{placeholder}>"
        if not placeholder.endswith(">"):
            placeholder = f"{placeholder}>"
        return cls(
            placeholder=placeholder,
            kind=str(data["kind"]).upper(),
            values=[str(v) for v in data.get("values", [])],
            rationale=str(data.get("rationale", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "placeholder": self.placeholder,
            "kind": self.kind,
            "values": list(self.values),
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class GeneratedTemplateSpec:
    name: str
    description: str
    source_hypothesis_id: str
    expression_template: str
    variables: list[TemplateVariable]
    design_notes: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GeneratedTemplateSpec":
        return cls(
            name=str(data["name"]).strip(),
            description=str(data.get("description", "")).strip(),
            source_hypothesis_id=str(data.get("source_hypothesis_id", "")).strip(),
            expression_template=str(data["expression_template"]).strip(),
            variables=[TemplateVariable.from_dict(v) for v in data.get("variables", [])],
            design_notes=[str(x) for x in data.get("design_notes", [])],
        )

    @classmethod
    def load(cls, path: str | Path) -> "GeneratedTemplateSpec":
        data = json.loads(Path(path).expanduser().resolve().read_text(encoding="utf-8"))
        return cls.from_dict(data)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "source_hypothesis_id": self.source_hypothesis_id,
            "expression_template": self.expression_template,
            "variables": [v.to_dict() for v in self.variables],
            "design_notes": list(self.design_notes),
        }

    def alpha_space(self) -> dict[str, list[str]]:
        return {v.placeholder: list(v.values) for v in self.variables}

    def variable_kinds(self) -> dict[str, str]:
        return {v.placeholder: v.kind for v in self.variables}

    def alpha_settings(self) -> dict[str, Any]:
        # The LLM is not allowed to silently change the simulation universe/settings.
        return json.loads(json.dumps(ALPHA_SETTINGS))

    def save_json(self, path: str | Path) -> Path:
        output = Path(path).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return output

    def save_python(self, path: str | Path) -> Path:
        output = Path(path).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        source = (
            '"""Auto-generated Alpha template. Do not edit by hand unless you intend to fork it."""\n\n'
            f"ALPHA_TEMPLATE = {self.expression_template!r}\n\n"
            f"ALPHA_SPACE = {self.alpha_space()!r}\n\n"
            "from wqb_alpha.alpha_template import ALPHA_SETTINGS, DEFAULT_GA_CONFIG\n"
        )
        output.write_text(source, encoding="utf-8")
        return output
