from __future__ import annotations

from .operator_catalog import OperatorCatalog


CORE_OPERATORS = {
    "add",
    "subtract",
    "multiply",
    "divide",
    "abs",
    "log",
    "signed_power",
    "ts_backfill",
    "ts_mean",
    "ts_delta",
    "ts_rank",
    "ts_zscore",
    "ts_std_dev",
    "ts_corr",
    "ts_decay_linear",
    "winsorize",
    "rank",
    "zscore",
    "normalize",
    "vec_avg",
    "vec_sum",
    "group_neutralize",
    "group_rank",
    "group_zscore",
    "trade_when",
}


class OperatorRetriever:
    def __init__(self, catalog: OperatorCatalog | None = None) -> None:
        self.catalog = catalog or OperatorCatalog()

    def search_for_analysis(self, analysis: dict, limit: int = 50) -> list[dict]:
        context = " ".join(
            [
                str(analysis.get("summary", "")),
                " ".join(analysis.get("global_concepts", []) or []),
                " ".join(
                    str(c.get("implementation_notes", ""))
                    for c in analysis.get("tradable_claims", []) or []
                ),
            ]
        ).lower()
        scored = []
        for record in self.catalog.records:
            name = str(record.get("name", ""))
            haystack = " ".join(
                str(record.get(k, ""))
                for k in ("name", "category", "definition", "description")
            ).lower()
            score = 3.0 if name in CORE_OPERATORS else 0.0
            for token in set(context.replace("/", " ").replace("-", " ").split()):
                if len(token) >= 4 and token in haystack:
                    score += 0.15
            if str(record.get("category", "")) in {
                "Time Series",
                "Cross Sectional",
                "Group",
                "Arithmetic",
                "Vector",
            }:
                score += 0.4
            scored.append((score, record))
        scored.sort(key=lambda x: (x[0], str(x[1].get("name", ""))), reverse=True)
        return [dict(record) for _, record in scored[:limit]]
