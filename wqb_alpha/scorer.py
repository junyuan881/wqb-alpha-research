from __future__ import annotations

from abc import ABC, abstractmethod

from .alpha import Alpha


class ScorerBase(ABC):
    @abstractmethod
    def get_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def score(self, alpha: Alpha) -> float:
        raise NotImplementedError


class SharpeScorer(ScorerBase):
    def get_name(self) -> str:
        return "sharpe"

    def score(self, alpha: Alpha) -> float:
        return float(alpha.result.get("is", {}).get("sharpe", -100))


class FitnessScorer(ScorerBase):
    def get_name(self) -> str:
        return "fitness"

    def score(self, alpha: Alpha) -> float:
        return float(alpha.result.get("is", {}).get("fitness", -100))
