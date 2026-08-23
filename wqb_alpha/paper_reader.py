from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


SUPPORTED_TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".rst", ".tex"}


@dataclass(frozen=True)
class PaperSource:
    path: Path
    kind: str
    text: str | None

    @property
    def name(self) -> str:
        return self.path.name


class PaperReader:
    """Prepare a research paper for the LLM layer.

    PDFs are passed directly to the OpenAI Responses API, which can ingest PDF text
    and page images. Plain-text formats are read locally in full and sent as input text.
    """

    def read(self, path: str | Path) -> PaperSource:
        paper_path = Path(path).expanduser().resolve()
        if not paper_path.exists() or not paper_path.is_file():
            raise FileNotFoundError(f"Paper not found: {paper_path}")
        suffix = paper_path.suffix.lower()
        if suffix == ".pdf":
            return PaperSource(path=paper_path, kind="pdf", text=None)
        if suffix in SUPPORTED_TEXT_SUFFIXES:
            text = paper_path.read_text(encoding="utf-8", errors="replace")
            return PaperSource(path=paper_path, kind="text", text=text)
        raise ValueError(
            f"Unsupported paper format {suffix!r}. Use PDF, TXT, MD, RST, or TEX."
        )
