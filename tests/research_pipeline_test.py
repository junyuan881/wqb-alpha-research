from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from wqb_alpha.llm.mock_client import MockLLMClient
from wqb_alpha.research_pipeline import ResearchPipeline
from wqb_alpha.template_schema import GeneratedTemplateSpec
from wqb_alpha.validator import validate_generated_template


ROOT = PROJECT_ROOT
PAPER = (ROOT / "papers" / "example_factor_paper.txt").resolve()


def main() -> None:
    pipeline = ResearchPipeline(MockLLMClient(), field_limit=80, operator_limit=50)
    artifacts = pipeline.run(paper_path=PAPER, simulate="none")
    assert artifacts.paper_analysis.exists()
    assert artifacts.candidate_fields.exists()
    assert artifacts.candidate_operators.exists()
    assert artifacts.template_json.exists()
    assert artifacts.template_python.exists()
    spec = GeneratedTemplateSpec.load(artifacts.template_json)
    report = validate_generated_template(spec)
    assert report.ok, report.errors
    print("RESEARCH PIPELINE TEST PASS")
    print(artifacts.template_json)


if __name__ == "__main__":
    main()
