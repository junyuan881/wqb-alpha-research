from __future__ import annotations

import json
from pathlib import Path

from .config import OPERATORS_JSON


class OperatorCatalog:
    def __init__(self, path: str | Path = OPERATORS_JSON) -> None:
        self.path = Path(path).resolve()
        with self.path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("Operator JSON must be a list")
        self.records: list[dict] = data
        self.by_name = {record.get("name"): record for record in self.records}

    def get(self, name: str) -> dict | None:
        return self.by_name.get(name)

    def names(self) -> set[str]:
        return {name for name in self.by_name if isinstance(name, str)}

    def search(self, query: str = "", category: str | None = None, limit: int = 50) -> list[dict]:
        q = query.lower().strip()
        out = []
        for record in self.records:
            if category and str(record.get("category", "")).lower() != category.lower():
                continue
            haystack = " ".join(
                str(record.get(key, ""))
                for key in ("name", "category", "definition", "description")
            ).lower()
            if q and q not in haystack:
                continue
            out.append(record)
            if len(out) >= limit:
                break
        return out
