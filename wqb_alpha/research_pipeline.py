from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .alpha_template import DEFAULT_GA_CONFIG
from .auth import AuthenticationError, BrainAuth, prompt_credentials
from .config import (
    CANDIDATES_DIR,
    HYPOTHESES_DIR,
    OUTPUT_DIR,
    TEMPLATES_DIR,
    ensure_runtime_directories,
)
from .exporter import save_results
from .field_search import FieldRetriever
from .genetic_search import GeneticAlgorithmProcess
from .hypothesis import collect_concepts
from .llm.base import LLMClient
from .operator_search import OperatorRetriever
from .paper_analyzer import PaperAnalyzer
from .paper_reader import PaperReader
from .storage import AlphaStore
from .template_generator import TemplateGenerator
from .template_schema import GeneratedTemplateSpec
from .validator import ValidationReport, validate_generated_template
from .worker import FakeWorker, Worker


@dataclass(frozen=True)
class ResearchArtifacts:
    paper_analysis: Path
    candidate_fields: Path
    candidate_operators: Path
    template_json: Path
    template_python: Path
    simulation_csv: Path | None
    validation: ValidationReport


class ResearchPipeline:
    """End-to-end paper -> LLM -> WQB mapping -> template -> validation -> simulation."""

    def __init__(
        self,
        llm: LLMClient,
        *,
        field_limit: int = 80,
        operator_limit: int = 50,
        max_repairs: int = 2,
    ) -> None:
        ensure_runtime_directories()
        self.llm = llm
        self.paper_reader = PaperReader()
        self.paper_analyzer = PaperAnalyzer(llm)
        self.field_retriever = FieldRetriever()
        self.operator_retriever = OperatorRetriever()
        self.template_generator = TemplateGenerator(llm)
        self.field_limit = int(field_limit)
        self.operator_limit = int(operator_limit)
        self.max_repairs = int(max_repairs)

    @staticmethod
    def _slug(text: str) -> str:
        value = re.sub(r"[^A-Za-z0-9_-]+", "_", text.strip()).strip("_").lower()
        return value[:80] or "paper"

    @staticmethod
    def _write_json(path: Path, data: Any) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    @staticmethod
    def _authenticate_for_real_simulation() -> None:
        auth = BrainAuth(interactive=True)
        try:
            auth.login()
        except AuthenticationError:
            if not (os.getenv("WQB_USERNAME") and os.getenv("WQB_PASSWORD")):
                print("沒有可用的 WQB session cache 或環境帳密，現在互動式輸入。")
                prompt_credentials()
                auth = BrainAuth(interactive=True)
                auth.login(force_relogin=True)
            else:
                raise

    def run(
        self,
        *,
        paper_path: str | Path,
        simulate: str = "none",
        generations: int = 2,
        population: int = 10,
        select_rate: float = 0.5,
        mutation_prob: float = 0.05,
        seed: int = 123,
        reset_db: bool = False,
        single_sim: bool = False,
    ) -> ResearchArtifacts:
        paper = self.paper_reader.read(paper_path)
        slug = self._slug(paper.path.stem)

        print("[1/7] Reading/analyzing paper with LLM...")
        analysis = self.paper_analyzer.analyze(paper)
        analysis_path = self._write_json(HYPOTHESES_DIR / f"{slug}_paper_analysis.json", analysis)

        print("[2/7] Retrieving relevant WQB data fields...")
        concepts = collect_concepts(analysis)
        candidate_fields = self.field_retriever.search_concepts(
            concepts,
            limit=self.field_limit,
        )
        if not candidate_fields:
            raise RuntimeError(
                "No WQB data fields matched the paper concepts. Inspect the paper analysis JSON "
                "and broaden the concepts or lower the retrieval threshold."
            )
        field_path = self._write_json(
            CANDIDATES_DIR / f"{slug}_fields.json",
            {"concepts": concepts, "results": candidate_fields},
        )

        print("[3/7] Retrieving relevant REGULAR operators...")
        candidate_operators = self.operator_retriever.search_for_analysis(
            analysis, limit=self.operator_limit
        )
        operator_path = self._write_json(
            CANDIDATES_DIR / f"{slug}_operators.json",
            {"results": candidate_operators},
        )

        print("[4/7] Asking LLM to design an Alpha template...")
        spec = self.template_generator.generate(
            analysis=analysis,
            candidate_fields=candidate_fields,
            candidate_operators=candidate_operators,
        )

        print("[5/7] Validating generated fields/operators/template...")
        allowed_field_ids = {str(r.get("id")) for r in candidate_fields if r.get("id")}
        allowed_operator_names = {str(r.get("name")) for r in candidate_operators if r.get("name")}
        report = validate_generated_template(
            spec,
            allowed_field_ids=allowed_field_ids,
            allowed_operator_names=allowed_operator_names,
        )
        repairs = 0
        while not report.ok and repairs < self.max_repairs:
            repairs += 1
            print(f"      validation failed; LLM repair attempt {repairs}/{self.max_repairs}")
            spec = self.template_generator.repair(
                spec=spec,
                report=report,
                analysis=analysis,
                candidate_fields=candidate_fields,
                candidate_operators=candidate_operators,
            )
            report = validate_generated_template(
                spec,
                allowed_field_ids=allowed_field_ids,
                allowed_operator_names=allowed_operator_names,
            )
        if not report.ok:
            details = "\n".join(f"- {x}" for x in report.errors)
            raise RuntimeError(f"Generated template still invalid after repair:\n{details}")

        template_json = spec.save_json(TEMPLATES_DIR / f"{slug}_template.json")
        template_python = spec.save_python(TEMPLATES_DIR / f"{slug}_alpha_template.py")

        simulation_csv: Path | None = None
        mode = simulate.lower().strip()
        if mode not in {"none", "fake", "real"}:
            raise ValueError("simulate must be one of: none, fake, real")

        if mode == "none":
            print("[6/7] Simulation skipped (--simulate none).")
            print("[7/7] Research artifacts saved.")
            return ResearchArtifacts(
                paper_analysis=analysis_path,
                candidate_fields=field_path,
                candidate_operators=operator_path,
                template_json=template_json,
                template_python=template_python,
                simulation_csv=None,
                validation=report,
            )

        print(f"[6/7] Running {mode} genetic search/simulation...")
        store = AlphaStore()
        if reset_db:
            store.reset(keep_session_cache=True)
        if mode == "real":
            self._authenticate_for_real_simulation()

        worker_cls = FakeWorker if mode == "fake" else Worker
        ga_config = {
            **DEFAULT_GA_CONFIG,
            "generation": int(generations),
            "population": int(population),
            "select_rate": float(select_rate),
            "mutation_prob": float(mutation_prob),
        }
        process = GeneticAlgorithmProcess(
            name=f"paper_{slug}",
            alpha_template=spec.expression_template,
            alpha_space=spec.alpha_space(),
            alpha_settings=spec.alpha_settings(),
            ga_config=ga_config,
            worker_cls=worker_cls,
            store=store,
            seed=int(seed),
            multi_simulation=not single_sim,
        )
        rows = process.run()
        simulation_csv = save_results(rows, OUTPUT_DIR / f"{slug}_research_results.csv")
        print("[7/7] Research artifacts and simulation results saved.")

        return ResearchArtifacts(
            paper_analysis=analysis_path,
            candidate_fields=field_path,
            candidate_operators=operator_path,
            template_json=template_json,
            template_python=template_python,
            simulation_csv=Path(simulation_csv).resolve(),
            validation=report,
        )
