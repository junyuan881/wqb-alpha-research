from __future__ import annotations

import argparse
import os
from pathlib import Path

from .alpha_template import DEFAULT_GA_CONFIG
from .auth import AuthenticationError, BrainAuth, login_interactively, prompt_credentials
from .config import load_local_env
from .data_field_catalog import DataFieldCatalog
from .exporter import results_dataframe, save_results
from .genetic_search import GeneticAlgorithmProcess
from .llm import LLMError, create_llm_client
from .operator_catalog import OperatorCatalog
from .research_pipeline import ResearchPipeline
from .storage import AlphaStore
from .template_schema import GeneratedTemplateSpec
from .validator import validate_generated_template, validate_template
from .worker import FakeWorker, Worker


def _print_records(records: list[dict], kind: str) -> None:
    if not records:
        print("No results.")
        return
    if kind == "field":
        for r in records:
            print(
                f"{r.get('id')} | {r.get('type')} | coverage={r.get('coverage')} | "
                f"dataset={r.get('dataset', {}).get('id')} | {r.get('description', '')}"
            )
    else:
        for r in records:
            print(
                f"{r.get('name')} | {r.get('category')} | {r.get('definition')}\n"
                f"  {r.get('description', '')}"
            )


def command_login(args: argparse.Namespace) -> int:
    login_interactively(clear_cache=args.clear_cache)
    return 0


def command_validate(_: argparse.Namespace) -> int:
    report = validate_template()
    print("Template validation:", "PASS" if report.ok else "FAIL")
    for warning in report.warnings:
        print("WARNING:", warning)
    for error in report.errors:
        print("ERROR:", error)
    return 0 if report.ok else 1


def command_validate_generated(args: argparse.Namespace) -> int:
    spec = GeneratedTemplateSpec.load(args.template)
    report = validate_generated_template(spec)
    print("Generated template validation:", "PASS" if report.ok else "FAIL")
    for warning in report.warnings:
        print("WARNING:", warning)
    for error in report.errors:
        print("ERROR:", error)
    return 0 if report.ok else 1


def command_fields(args: argparse.Namespace) -> int:
    catalog = DataFieldCatalog()
    records = catalog.search(
        query=args.query,
        field_type=args.type,
        dataset_id=args.dataset,
        min_coverage=args.min_coverage,
        limit=args.limit,
    )
    _print_records(records, "field")
    return 0


def command_operators(args: argparse.Namespace) -> int:
    catalog = OperatorCatalog()
    records = catalog.search(query=args.query, category=args.category, limit=args.limit)
    _print_records(records, "operator")
    return 0


def _real_worker_auth(args: argparse.Namespace) -> None:
    auth = BrainAuth(interactive=True)
    try:
        auth.login()
    except AuthenticationError:
        if not (os.getenv("WQB_USERNAME") and os.getenv("WQB_PASSWORD")):
            print("沒有可用的 session cache 或環境帳密，現在互動式輸入。")
            prompt_credentials()
            auth = BrainAuth(interactive=True)
            auth.login(force_relogin=True)
        else:
            raise
    if not args.single_sim and auth.permissions and "MULTI_SIMULATION" not in auth.permissions:
        print("帳號沒有 MULTI_SIMULATION 權限，已自動切換 single simulation。")
        args.single_sim = True


def command_run(args: argparse.Namespace) -> int:
    report = validate_template()
    if not report.ok:
        for error in report.errors:
            print("ERROR:", error)
        print("Template/data validation failed. Simulation aborted.")
        return 1

    store = AlphaStore()
    if args.reset_db:
        store.reset(keep_session_cache=True)

    if args.mode == "real":
        _real_worker_auth(args)

    worker_cls = FakeWorker if args.mode == "fake" else Worker
    ga_config = {
        **DEFAULT_GA_CONFIG,
        "generation": args.generations,
        "population": args.population,
        "select_rate": args.select_rate,
        "mutation_prob": args.mutation_prob,
    }
    process = GeneticAlgorithmProcess(
        name=args.name,
        ga_config=ga_config,
        worker_cls=worker_cls,
        store=store,
        seed=args.seed,
        multi_simulation=not args.single_sim,
    )
    rows = process.run()
    output_path = save_results(rows, args.output)
    df = results_dataframe(rows)
    print(df.head(args.head).to_string(index=False))
    print(f"\nCSV saved: {output_path}")

    error_count = sum(row.get("stage") == "error" for row in rows)
    if error_count:
        print(f"ERROR alphas: {error_count}/{len(rows)}")
        print("請查看 CSV 的 pipeline_error 欄，以及 db/error/*.json 的完整錯誤。")
    return 0



def command_run_generated(args: argparse.Namespace) -> int:
    spec = GeneratedTemplateSpec.load(args.template)
    report = validate_generated_template(spec)
    if not report.ok:
        print("Generated template validation: FAIL")
        for error in report.errors:
            print("ERROR:", error)
        return 1

    store = AlphaStore()
    if args.reset_db:
        store.reset(keep_session_cache=True)
    if args.mode == "real":
        _real_worker_auth(args)

    worker_cls = FakeWorker if args.mode == "fake" else Worker
    ga_config = {
        **DEFAULT_GA_CONFIG,
        "generation": args.generations,
        "population": args.population,
        "select_rate": args.select_rate,
        "mutation_prob": args.mutation_prob,
    }
    process = GeneticAlgorithmProcess(
        name=args.name,
        alpha_template=spec.expression_template,
        alpha_space=spec.alpha_space(),
        alpha_settings=spec.alpha_settings(),
        ga_config=ga_config,
        worker_cls=worker_cls,
        store=store,
        seed=args.seed,
        multi_simulation=not args.single_sim,
    )
    rows = process.run()
    output_path = save_results(rows, args.output)
    df = results_dataframe(rows)
    print(df.head(args.head).to_string(index=False))
    print(f"\nCSV saved: {output_path}")
    return 0

def command_research(args: argparse.Namespace) -> int:
    try:
        llm = create_llm_client(args.llm_provider, model=args.model)
        pipeline = ResearchPipeline(
            llm,
            field_limit=args.field_limit,
            operator_limit=args.operator_limit,
            max_repairs=args.max_repairs,
        )
        artifacts = pipeline.run(
            paper_path=Path(args.paper).expanduser().resolve(),
            simulate=args.simulate,
            generations=args.generations,
            population=args.population,
            select_rate=args.select_rate,
            mutation_prob=args.mutation_prob,
            seed=args.seed,
            reset_db=args.reset_db,
            single_sim=args.single_sim,
        )
    except (LLMError, RuntimeError, ValueError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print("\n=== Generated research artifacts ===")
    print("Paper analysis :", artifacts.paper_analysis)
    print("Candidate fields:", artifacts.candidate_fields)
    print("Operators      :", artifacts.candidate_operators)
    print("Template JSON  :", artifacts.template_json)
    print("Template Python:", artifacts.template_python)
    if artifacts.simulation_csv:
        print("Simulation CSV :", artifacts.simulation_csv)
    print("Validation     : PASS")
    for warning in artifacts.validation.warnings:
        print("WARNING:", warning)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WorldQuant BRAIN alpha research project")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("login", help="Interactive BRAIN login / Persona flow")
    p.add_argument("--clear-cache", action="store_true")
    p.set_defaults(func=command_login)

    p = sub.add_parser("validate", help="Validate the default hand-written template")
    p.set_defaults(func=command_validate)

    p = sub.add_parser("validate-generated", help="Validate a generated template JSON")
    p.add_argument("template", help="Absolute or relative path to generated template JSON")
    p.set_defaults(func=command_validate_generated)

    p = sub.add_parser("fields", help="Search GLB D1 TOPDIV3000 data fields")
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--type", choices=["MATRIX", "VECTOR"], default=None)
    p.add_argument("--dataset", default=None)
    p.add_argument("--min-coverage", type=float, default=None)
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=command_fields)

    p = sub.add_parser("operators", help="Search REGULAR operators")
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--category", default=None)
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=command_operators)

    p = sub.add_parser("run", help="Run genetic alpha research using the default template")
    p.add_argument("--mode", choices=["fake", "real"], default="fake")
    p.add_argument("--name", default="glb_d1")
    p.add_argument("--generations", type=int, default=2)
    p.add_argument("--population", type=int, default=10)
    p.add_argument("--select-rate", type=float, default=0.5)
    p.add_argument("--mutation-prob", type=float, default=0.05)
    p.add_argument("--seed", type=int, default=123)
    p.add_argument("--single-sim", action="store_true", help="Disable multi-simulation")
    p.add_argument("--reset-db", action="store_true")
    p.add_argument("--output", default="alphas_sorted_by_sharpe.csv")
    p.add_argument("--head", type=int, default=20)
    p.set_defaults(func=command_run)

    p = sub.add_parser("run-generated", help="Run GA/simulation from a previously generated template JSON")
    p.add_argument("template")
    p.add_argument("--mode", choices=["fake", "real"], default="fake")
    p.add_argument("--name", default="generated_alpha")
    p.add_argument("--generations", type=int, default=2)
    p.add_argument("--population", type=int, default=10)
    p.add_argument("--select-rate", type=float, default=0.5)
    p.add_argument("--mutation-prob", type=float, default=0.05)
    p.add_argument("--seed", type=int, default=123)
    p.add_argument("--single-sim", action="store_true")
    p.add_argument("--reset-db", action="store_true")
    p.add_argument("--output", default="generated_template_results.csv")
    p.add_argument("--head", type=int, default=20)
    p.set_defaults(func=command_run_generated)

    p = sub.add_parser(
        "research",
        help="End-to-end: paper -> LLM -> WQB field mapping -> template -> validation -> simulation",
    )
    p.add_argument("--paper", required=True, help="Path to PDF/TXT/MD/RST/TEX research paper")
    p.add_argument("--llm-provider", choices=["openai", "mock"], default=None)
    p.add_argument("--model", default=None, help="OpenAI model; defaults to LLM_MODEL or gpt-5.6")
    p.add_argument("--field-limit", type=int, default=80)
    p.add_argument("--operator-limit", type=int, default=50)
    p.add_argument("--max-repairs", type=int, default=2)
    p.add_argument("--simulate", choices=["none", "fake", "real"], default="none")
    p.add_argument("--generations", type=int, default=2)
    p.add_argument("--population", type=int, default=10)
    p.add_argument("--select-rate", type=float, default=0.5)
    p.add_argument("--mutation-prob", type=float, default=0.05)
    p.add_argument("--seed", type=int, default=123)
    p.add_argument("--single-sim", action="store_true")
    p.add_argument("--reset-db", action="store_true")
    p.set_defaults(func=command_research)
    return parser


def main() -> int:
    load_local_env()
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
