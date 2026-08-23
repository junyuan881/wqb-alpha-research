from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import PROMPTS_DIR
from .hypothesis import PAPER_ANALYSIS_SCHEMA
from .llm.base import LLMClient
from .paper_reader import PaperSource


class PaperAnalyzer:
    def __init__(
        self,
        llm: LLMClient,
        prompt_path: str | Path | None = None,
    ) -> None:
        self.llm = llm
        self.prompt_path = Path(prompt_path or (PROMPTS_DIR / "paper_analysis.txt")).resolve()

    def analyze(self, paper: PaperSource) -> dict[str, Any]:
        system_prompt = self.prompt_path.read_text(encoding="utf-8")
        if paper.kind == "pdf":
            user_text = (
                "Read the attached research paper carefully. Extract only claims that the paper itself "
                "supports. Focus on empirical relationships that could plausibly be mapped into a stock alpha."
            )
            file_path = paper.path
        else:
            user_text = (
                "Read the research paper text below carefully. Extract only claims supported by the text.\n\n"
                + (paper.text or "")
            )
            file_path = None
        return self.llm.generate_json(
            system_prompt=system_prompt,
            user_text=user_text,
            schema=PAPER_ANALYSIS_SCHEMA,
            schema_name="paper_analysis",
            file_path=file_path,
            max_output_tokens=7000,
        )
