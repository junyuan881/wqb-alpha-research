from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import LLMClient


class MockLLMClient(LLMClient):
    """Deterministic offline LLM used to test the entire research pipeline."""

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
        if schema_name == "paper_analysis":
            return {
                "title": "Mock Cash Flow and Leverage Research",
                "research_question": "Whether cash-flow strength relative to debt predicts future returns.",
                "summary": "The mock paper argues that firms with improving cash-flow quality relative to leverage may earn different subsequent returns.",
                "tradable_claims": [
                    {
                        "id": "H1",
                        "source_hint": "Main empirical hypothesis",
                        "hypothesis": "Cash-flow strength relative to debt contains a cross-sectional return signal.",
                        "economic_intuition": "Cash generation can reveal balance-sheet resilience before it is fully reflected in prices.",
                        "predictor_concepts": [
                            "free cash flow",
                            "operating cash flow",
                            "net debt",
                            "leverage",
                        ],
                        "expected_direction": "POSITIVE",
                        "horizon": "1-6 months",
                        "implementation_notes": "Compare a cash-flow measure with a debt measure, standardize through time, then neutralize broad groups.",
                    }
                ],
                "global_concepts": [
                    "free cash flow",
                    "operating cash flow",
                    "net debt",
                    "leverage",
                    "financial strength",
                ],
                "risks": ["Accounting data are stale and can contain missing observations."],
            }

        if schema_name in {"alpha_template", "alpha_template_repair"}:
            return {
                "name": "cashflow_debt_resilience",
                "description": "Backfilled cash flow minus debt, standardized over time and group-neutralized.",
                "source_hypothesis_id": "H1",
                "expression_template": (
                    "cash = ts_backfill(<cash_field>, <backfill_days>);\n"
                    "debt = ts_backfill(<debt_field>, <backfill_days>);\n"
                    "raw = subtract(cash, debt);\n"
                    "signal = ts_zscore(raw, <lookback>);\n"
                    "neutral = group_neutralize(signal, <group>);\n"
                    "ts_decay_linear(neutral, <decay_days>)"
                ),
                "variables": [
                    {
                        "placeholder": "<cash_field>",
                        "kind": "FIELD",
                        "values": ["free_cash_flow_firm", "free_cash_flow_annual"],
                        "rationale": "Cash-flow proxies present in the GLB catalog.",
                    },
                    {
                        "placeholder": "<debt_field>",
                        "kind": "FIELD",
                        "values": ["fnd23_net_debt", "net_debt_annual"],
                        "rationale": "Debt/leverage proxies present in the GLB catalog.",
                    },
                    {
                        "placeholder": "<backfill_days>",
                        "kind": "PARAMETER",
                        "values": ["21", "63", "126"],
                        "rationale": "Reasonable missing-data lookbacks.",
                    },
                    {
                        "placeholder": "<lookback>",
                        "kind": "PARAMETER",
                        "values": ["21", "63", "126", "252"],
                        "rationale": "Short-to-long time-series standardization horizons.",
                    },
                    {
                        "placeholder": "<group>",
                        "kind": "GROUP",
                        "values": ["market", "sector", "industry", "subindustry"],
                        "rationale": "Broad group controls.",
                    },
                    {
                        "placeholder": "<decay_days>",
                        "kind": "PARAMETER",
                        "values": ["5", "10", "21"],
                        "rationale": "Turnover/smoothing variants.",
                    },
                ],
                "design_notes": [
                    "Static operators are limited to the supplied REGULAR operator catalog.",
                    "The template exposes fields and horizons to the genetic search rather than changing the economic story.",
                ],
            }
        raise ValueError(f"MockLLMClient does not implement schema_name={schema_name}")
