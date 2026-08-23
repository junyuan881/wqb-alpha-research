from __future__ import annotations

import copy
import random
from pathlib import Path

import numpy as np

from .alpha import Alpha
from .alpha_list import AlphaList
from .alpha_template import ALPHA_SETTINGS, ALPHA_SPACE, ALPHA_TEMPLATE, DEFAULT_GA_CONFIG
from .scorer import ScorerBase, SharpeScorer
from .storage import AlphaStore
from .template_engine import TemplateEngine
from .worker import FakeWorker, Worker


class GeneticAlgorithmProcess:
    def __init__(
        self,
        name: str,
        scorer: ScorerBase | None = None,
        alpha_template: str = ALPHA_TEMPLATE,
        alpha_space: dict[str, list[str]] = ALPHA_SPACE,
        alpha_settings: dict = ALPHA_SETTINGS,
        ga_config: dict | None = None,
        worker_cls=Worker,
        store: AlphaStore | None = None,
        seed: int | None = 123,
        multi_simulation: bool = True,
    ) -> None:
        self.name = name
        self.scorer = scorer or SharpeScorer()
        self.alpha_settings = copy.deepcopy(alpha_settings)
        self.ga_config = {**DEFAULT_GA_CONFIG, **(ga_config or {})}
        self.worker_cls = worker_cls
        self.store = store or AlphaStore()
        self.rng = random.Random(seed)
        self.seed = seed
        self.multi_simulation = multi_simulation
        self.engine = TemplateEngine(alpha_template, alpha_space)
        self._alpha_lists: list[AlphaList] = []
        self._generation_genes: list[dict[str, dict[str, str]]] = []

    def generate_alpha_name(self, generation: int, index: int) -> str:
        return f"{self.name}_{generation}_{index}"

    def _worker(self):
        if self.worker_cls is FakeWorker:
            return FakeWorker(
                multi_simulation=self.multi_simulation,
                store=self.store,
                seed=self.rng.randrange(1, 2**31 - 1),
            )
        return self.worker_cls(
            multi_simulation=self.multi_simulation,
            store=self.store,
        )

    def sim_alphas(self, alphas: list[Alpha]) -> dict[str, float]:
        alpha_list = AlphaList(alphas, store=self.store)
        self._alpha_lists.append(alpha_list)
        alpha_list.persist_missing()
        self._worker().run()
        alpha_list.sim_and_wait()
        alpha_dict = alpha_list.get_alphas()
        return {filename: self.scorer.score(alpha) for filename, alpha in alpha_dict.items()}

    def _generation_iter(self, generation: int, genes: list[dict[str, str]] | None) -> dict[str, float]:
        population = int(self.ga_config["population"])
        if not genes:
            genes = [self.engine.random_gene(self.rng) for _ in range(population)]

        gene_map: dict[str, dict[str, str]] = {}
        alphas: list[Alpha] = []
        for index, gene in enumerate(genes):
            name = self.generate_alpha_name(generation, index)
            gene_map[name] = gene.copy()
            expression = self.engine.render(gene)
            payload = copy.deepcopy(self.alpha_settings)
            payload["regular"] = expression
            alphas.append(Alpha(name=name, payload=payload))

        self._generation_genes.append(gene_map)
        return self.sim_alphas(alphas)

    def _select(self, scores: dict[str, float]) -> list[str]:
        if not scores:
            return []
        threshold = float(
            np.quantile(list(scores.values()), float(self.ga_config["select_rate"]))
        )
        return [name for name, score in scores.items() if score >= threshold]

    def run(self) -> list[dict]:
        scores = self._generation_iter(0, None)
        total_generations = int(self.ga_config["generation"])
        for generation in range(1, total_generations):
            survivors = self._select(scores)
            previous = self._generation_genes[-1]
            parents = []
            for filename in survivors:
                alpha_name = Path(filename).stem
                if alpha_name in previous:
                    parents.append(previous[alpha_name])
            if not parents:
                parents = list(previous.values())

            genes = []
            for _ in range(int(self.ga_config["population"])):
                child = self.engine.crossover(parents, self.rng)
                child = self.engine.mutate(
                    child,
                    float(self.ga_config["mutation_prob"]),
                    self.rng,
                )
                genes.append(child)
            scores = self._generation_iter(generation, genes)
        return self.get_all_results()

    def get_all_results(self) -> list[dict]:
        rows = []
        for generation, alpha_list in enumerate(self._alpha_lists):
            genes = self._generation_genes[generation]
            for filename, alpha in alpha_list.get_alphas().items():
                metrics = alpha.result.get("is", {}) if isinstance(alpha.result, dict) else {}
                row = {
                    "generation": generation,
                    "filename": filename,
                    "name": alpha.name,
                    "stage": alpha.stage.value,
                    "expression": alpha.payload.get("regular", ""),
                    "sharpe": metrics.get("sharpe", -100),
                    "fitness": metrics.get("fitness", -100),
                    "turnover": metrics.get("turnover"),
                    "returns": metrics.get("returns"),
                    "drawdown": metrics.get("drawdown"),
                    "margin": metrics.get("margin"),
                    "pipeline_error": alpha.result.get("pipelineError") if isinstance(alpha.result, dict) else None,
                }
                for key, value in genes.get(alpha.name, {}).items():
                    row[f"gene_{key.strip('<>')}"] = value
                rows.append(row)
        return rows
