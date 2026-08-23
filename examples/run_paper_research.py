"""Programmatic example for paper -> template -> fake simulation."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wqb_alpha.llm import create_llm_client
from wqb_alpha.research_pipeline import ResearchPipeline


paper = (ROOT / "papers" / "example_factor_paper.txt").resolve()
llm = create_llm_client("mock")  # Change to "openai" after setting OPENAI_API_KEY.
pipeline = ResearchPipeline(llm)
artifacts = pipeline.run(
    paper_path=paper,
    simulate="fake",
    generations=2,
    population=6,
    reset_db=True,
)
print(artifacts)
