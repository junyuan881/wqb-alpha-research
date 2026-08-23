from __future__ import annotations

import math
import re
from collections import defaultdict

from .data_field_catalog import DataFieldCatalog


_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokens(text: str) -> list[str]:
    return [x.lower() for x in _TOKEN_RE.findall(text) if len(x) >= 2]


class FieldRetriever:
    """Rank WQB fields against paper concepts without sending all 28k fields to the LLM."""

    def __init__(self, catalog: DataFieldCatalog | None = None) -> None:
        self.catalog = catalog or DataFieldCatalog()

    @staticmethod
    def _record_text(record: dict) -> tuple[str, str]:
        field_id = str(record.get("id", "")).lower()
        description = str(record.get("description", "")).lower()
        dataset = " ".join(
            [
                str(record.get("dataset", {}).get("id", "")),
                str(record.get("dataset", {}).get("name", "")),
                str(record.get("category", {}).get("name", "")),
                str(record.get("subcategory", {}).get("name", "")),
            ]
        ).lower()
        return field_id, f"{description} {dataset}"

    def _score(self, record: dict, concept: str) -> float:
        field_id, rest = self._record_text(record)
        phrase = concept.lower().strip()
        terms = _tokens(concept)
        if not terms:
            return 0.0
        score = 0.0
        normalized_id = field_id.replace("_", " ")
        if phrase and phrase in normalized_id:
            score += 12.0
        if phrase and phrase in rest:
            score += 8.0
        for term in terms:
            if term in field_id:
                score += 3.5
            if term in rest:
                score += 1.5
        coverage = record.get("coverage")
        if isinstance(coverage, (int, float)):
            score += max(0.0, min(float(coverage), 1.0)) * 1.5
        alpha_count = record.get("alphaCount")
        if isinstance(alpha_count, (int, float)) and alpha_count > 0:
            score += min(math.log1p(float(alpha_count)) / 10.0, 0.6)
        # Direct MATRIX fields are easier to compose in FASTEXPR. VECTOR fields remain eligible,
        # but MATRIX receives a small preference rather than a hard exclusion.
        if str(record.get("type", "")).upper() == "MATRIX":
            score += 0.8
        return score

    def search_concepts(
        self,
        concepts: list[str],
        *,
        limit: int = 80,
        per_concept: int = 15,
        min_coverage: float | None = 0.15,
    ) -> list[dict]:
        best: dict[str, float] = defaultdict(float)
        records_by_id: dict[str, dict] = {}
        for concept in concepts:
            scored: list[tuple[float, dict]] = []
            for record in self.catalog.records:
                coverage = record.get("coverage")
                if min_coverage is not None and isinstance(coverage, (int, float)):
                    if float(coverage) < min_coverage:
                        continue
                score = self._score(record, concept)
                if score > 1.0:
                    scored.append((score, record))
            scored.sort(key=lambda x: x[0], reverse=True)
            for score, record in scored[:per_concept]:
                field_id = str(record.get("id", ""))
                if not field_id:
                    continue
                best[field_id] = max(best[field_id], score)
                records_by_id[field_id] = record

        ranked = sorted(best.items(), key=lambda x: x[1], reverse=True)[:limit]
        out = []
        for field_id, score in ranked:
            record = dict(records_by_id[field_id])
            record["retrievalScore"] = round(score, 4)
            out.append(record)
        return out
