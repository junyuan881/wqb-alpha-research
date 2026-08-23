from __future__ import annotations

from typing import Any


PAPER_ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "research_question": {"type": "string"},
        "summary": {"type": "string"},
        "tradable_claims": {
            "type": "array",
            "minItems": 1,
            "maxItems": 8,
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "source_hint": {"type": "string"},
                    "hypothesis": {"type": "string"},
                    "economic_intuition": {"type": "string"},
                    "predictor_concepts": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 10,
                        "items": {"type": "string"},
                    },
                    "expected_direction": {
                        "type": "string",
                        "enum": ["POSITIVE", "NEGATIVE", "NONLINEAR", "UNKNOWN"],
                    },
                    "horizon": {"type": "string"},
                    "implementation_notes": {"type": "string"},
                },
                "required": [
                    "id",
                    "source_hint",
                    "hypothesis",
                    "economic_intuition",
                    "predictor_concepts",
                    "expected_direction",
                    "horizon",
                    "implementation_notes",
                ],
                "additionalProperties": False,
            },
        },
        "global_concepts": {
            "type": "array",
            "minItems": 1,
            "maxItems": 20,
            "items": {"type": "string"},
        },
        "risks": {
            "type": "array",
            "maxItems": 12,
            "items": {"type": "string"},
        },
    },
    "required": [
        "title",
        "research_question",
        "summary",
        "tradable_claims",
        "global_concepts",
        "risks",
    ],
    "additionalProperties": False,
}


def collect_concepts(analysis: dict[str, Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    candidates = list(analysis.get("global_concepts", []) or [])
    for claim in analysis.get("tradable_claims", []) or []:
        candidates.extend(claim.get("predictor_concepts", []) or [])
    for value in candidates:
        text = str(value).strip()
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            out.append(text)
    return out
