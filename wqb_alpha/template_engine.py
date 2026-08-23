from __future__ import annotations

import random


class TemplateEngine:
    def __init__(self, template: str, alpha_space: dict[str, list[str]]) -> None:
        self.template = template
        self.alpha_space = alpha_space

    def render(self, gene: dict[str, str]) -> str:
        expression = self.template
        for key, value in gene.items():
            expression = expression.replace(key, value)
        unresolved = [key for key in self.alpha_space if key in expression]
        if unresolved:
            raise ValueError(f"Unresolved template placeholders: {unresolved}")
        return expression

    def random_gene(self, rng: random.Random | None = None) -> dict[str, str]:
        rng = rng or random.Random()
        return {key: rng.choice(values) for key, values in self.alpha_space.items()}

    def mutate(
        self,
        gene: dict[str, str],
        mutation_prob: float,
        rng: random.Random | None = None,
    ) -> dict[str, str]:
        rng = rng or random.Random()
        out = gene.copy()
        for key, values in self.alpha_space.items():
            if rng.random() < mutation_prob:
                out[key] = rng.choice(values)
        return out

    def crossover(
        self,
        parents: list[dict[str, str]],
        rng: random.Random | None = None,
    ) -> dict[str, str]:
        if not parents:
            raise ValueError("At least one parent is required")
        rng = rng or random.Random()
        return {key: rng.choice(parents)[key] for key in self.alpha_space}
